"""server.py — FastAPI surface over raven.core.

Single source of truth for the GUI's HTTP calls. The dashboard used to read
static JSON (page-<slug>.json etc.); it now calls this server, which keeps
everything dynamic and supports multiple vaults.

Design:
    - stateless: every request resolves the vault fresh
    - CORS restricted to the local dashboard's known origins (v0.7.67+); production should add auth
    - errors return {ok: false, error: "..."} (never raw stack traces)
    - all write ops use the engine; no shortcuts
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from raven.core import registry, resolve_active_vault, link_module
from raven.core.registry import VAULTS_ROOT
from raven.core import db_module, lint_module, export_module
from raven.core import slug_module, frontmatter_module, archive_module
from raven.core import log_module, digest_module
from raven.core import contracts
from raven.core.vault import Vault

# v0.7.61+ workspace tree (read-only) — WorkspacePage OS 파일 트리 노출.
from raven.api.workspace_tree import (
    list_workspace_dir,
    read_workspace_file,
    MAX_DEPTH,
    DEFAULT_DEPTH,
)


app = FastAPI(title="raven API", version="0.2.0")
# v0.7.67 (평가 A#5): `allow_origins=["*"]` + 무인증 조합은 127.0.0.1 바인딩을
# 무력화한다 — 원격 접속은 못 막아도, 브라우저에 열린 *임의의 웹페이지*가
# cross-origin으로 이 API를 호출할 수 있었다(예: DELETE /api/vaults/{name}
# ?force=true → shutil.rmtree). 로컬 대시보드가 실제로 쓰는 origin만 허용
# (.env.example의 PORT_API/PORT_DASHBOARD로 커스터마이즈 가능).
_dashboard_port = os.environ.get("PORT_DASHBOARD", "5173")
_api_port = os.environ.get("PORT_API", "8765")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{_dashboard_port}",   # vite dev server
        f"http://127.0.0.1:{_dashboard_port}",
        f"http://localhost:{_api_port}",         # built dashboard served by this API
        f"http://127.0.0.1:{_api_port}",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────────── helpers ──────────────────────────


def _vault_or_404(name: str) -> Vault:
    meta = registry().get(name)
    if not meta:
        raise HTTPException(status_code=404, detail=f"vault {name!r} not found")
    try:
        return Vault.load(meta)
    except FileNotFoundError:
        raise HTTPException(
            status_code=409,
            detail=(
                f"vault {name!r} is registered at {meta.path!s}, but that path "
                f"doesn't resolve in this runtime. Fix the registry pointer with "
                f"`raven vault repair {name} --path <correct-path>` or "
                f"`POST /api/vaults/{name}/repair` — this only rewrites the "
                f"registry entry, it never touches vault files."
            ),
        )


def _err(e: Exception) -> dict:
    return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _safe_slug_or_400(slug: str, v: Vault) -> Path:
    """Validate slug and return absolute Path (without .md suffix).

    Raises HTTPException(400) on bad slug.
    """
    try:
        return slug_module.validate(slug, vault_root=v.root)
    except slug_module.SlugError as e:
        raise HTTPException(status_code=400, detail=f"invalid slug: {e}")


# ────────────────────────── models ──────────────────────────


class PageCreate(BaseModel):
    slug: str = Field(..., description="vault-relative path, e.g. 'content/foo'")
    title: str
    content: str = ""
    type: str = "concept"
    tags: list[str] = []


class PageUpdate(BaseModel):
    content: str
    title: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[list[str]] = None


class LogAppend(BaseModel):
    action: str = Field(..., description="ingest|update|create|archive|delete|lint|build|migrate|chore")
    subject: str
    files: list[str] = []
    note: Optional[str] = None


# ────────────────────────── vault endpoints ──────────────────────────


@app.get("/api/vaults")
def list_vaults():
    """All registered vaults (with metadata).

    v0.6.3+: also returns the resolved `vaults_root` so the dashboard
    can show "Vaults root: ~/Raven" or wherever WIKI_VAULTS_DIR points.
    """
    runtime_root = VAULTS_ROOT()
    host_root_raw = os.environ.get("RAVEN_VAULTS_DIR", "").strip()
    host_root = Path(host_root_raw).expanduser().resolve() if host_root_raw else runtime_root
    reg_data = registry()._data.get("vaults", {})
    out = []
    for v in registry().list():
        raw_meta = reg_data.get(v.name, {})
        display_path = raw_meta.get("path") if isinstance(raw_meta, dict) else None
        if not isinstance(display_path, str) or not display_path.strip():
            try:
                rel = v.path.resolve().relative_to(runtime_root.resolve())
                display_path = str((host_root / rel).resolve())
            except ValueError:
                display_path = str(v.path)
        out.append({
            "name": v.name,
            "path": display_path,
            "mode": v.mode,
            "owner": v.owner,
            "default": v.default,
            "workspace_path": v.workspace_path,
        })
    return {
        "ok": True,
        "vaults": out,
        "vaults_root": str(host_root),
        "runtime_vaults_root": str(runtime_root),
    }


def _resolve_vault_create_paths(requested_path: Path) -> tuple[Path, Path]:
    """Return runtime and display paths for vault creation.

    Docker runs against the container-local mount root (`WIKI_VAULTS_DIR`), but
    the persisted `.vault.json` path and UI should keep the host absolute path
    from `RAVEN_VAULTS_DIR` when available.
    """
    display_path = requested_path.expanduser().resolve()
    runtime_root = VAULTS_ROOT().resolve()
    host_root_raw = os.environ.get("RAVEN_VAULTS_DIR", "").strip()
    if not host_root_raw:
        return display_path, display_path

    host_root = Path(host_root_raw).expanduser().resolve()
    if host_root == runtime_root:
        return display_path, display_path

    try:
        rel = display_path.relative_to(host_root)
        return (runtime_root / rel).resolve(), display_path
    except ValueError:
        pass

    try:
        rel = display_path.relative_to(runtime_root)
        return display_path, (host_root / rel).resolve()
    except ValueError:
        return display_path, display_path


@app.get("/api/index.json")
def get_index_json() -> list:
    """Page index for the Dashboard HomePage.

    v0.6.5+: dev API now serves the same shape as `scripts/export_static.py`
    produces for the static `dashboard/public/api/index.json`. Previously
    the dev server returned 404 (no such route) — HomePage was always
    empty in `make dev` until the user ran `raven export` first.

    Shape (per page):
        {slug, title, type, path, created, updated, tags}

    Vault selection:
        - If a `default` is set in the registry, use it
        - Otherwise fall back to the first registered vault
        - 404 if no vaults are registered

    Filter rules match `export_static.py`:
        - skip hidden paths (start with `.`)
        - skip `node_modules/` and `dashboard/`
    """
    from fastapi import HTTPException

    # Pick default (or first) vault — same pattern as the Dashboard's
    # `GET /api/vaults` consumer.
    reg_data = registry()._data
    default_name = reg_data.get("default")
    vaults = registry().list()
    if not vaults:
        raise HTTPException(status_code=404, detail="no vaults registered")
    target_meta = None
    if default_name:
        target_meta = next((v for v in vaults if v.name == default_name), None)
    if target_meta is None:
        target_meta = vaults[0]
    # registry().list() returns VaultMeta objects; we need a live Vault
    # handle to access .content_root / .root for filesystem reads.
    target = Vault.load(target_meta)

    rows: list = []
    # Path components that must never be exposed via the page index
    # (mirrors `scripts/export_static.py` SQL filter on L120-124).
    hidden_top = {".", "..", "node_modules", "dashboard", ".git"}
    for fp in target.content_root.rglob("*.md"):
        rel = fp.relative_to(target.root)
        rel_str = str(rel).replace("\\", "/")
        # Skip if ANY path component is hidden (matches SQL's
        # `slug NOT LIKE '.%'` for the second-level component + the
        # explicit node_modules / dashboard blocklist).
        parts = rel_str.split("/")
        if any(p in hidden_top or p.startswith(".") for p in parts):
            continue

        text = fp.read_text(errors="replace")
        meta, _ = _split_fm(text)
        slug = rel_str[:-3]  # drop ".md"
        tags_str = meta.get("tags", "") or ""
        rows.append(
            {
                "slug": slug,
                "title": meta.get("title", slug.split("/")[-1]),
                "type": meta.get("type", "?"),
                "path": rel_str,
                "created": meta.get("created", ""),
                "updated": meta.get("updated", ""),
                "tags": tags_str,
            }
        )

    # Sort by (type, slug) — same as export_static L137.
    rows.sort(key=lambda p: (p["type"] or "", p["slug"]))
    return rows


@app.get("/api/vaults/{name}")
def vault_info(name: str):
    v = _vault_or_404(name)
    pages = list(v.content_root.rglob("*.md"))
    return {
        "ok": True,
        "vault": {
            "name": v.meta.name,
            "path": str(v.root),
            "mode": v.meta.mode,
            "owner": v.meta.owner,
            "created": v.meta.created,
            "pages": len(pages),
            "db_present": v.db_path.exists(),
            "workspace_path": v.meta.workspace_path,
        },
    }


@app.post("/api/vaults/{name}/select")
def select_vault(name: str):
    """Set the registry default to `name`."""
    if not registry().set_default(name):
        raise HTTPException(status_code=404, detail=f"vault {name!r} not found")
    return {"ok": True, "active": name}


class WorkspacePayload(BaseModel):
    workspace_path: str = ""
    unlink: bool = False


@app.post("/api/vaults/{name}/workspace")
def associate_workspace(name: str, payload: WorkspacePayload):
    """Associate or unlink a workspace directory with a vault."""
    meta = registry().get(name)
    if not meta:
        raise HTTPException(status_code=404, detail=f"vault {name!r} not found")

    w_path = ""
    if not payload.unlink and payload.workspace_path:
        p = Path(payload.workspace_path).expanduser().resolve()
        if not p.exists() or not p.is_dir():
            raise HTTPException(status_code=400, detail=f"Not a directory: {p}")
        w_path = str(p)

    if registry().update_workspace_path(name, w_path):
        return {"ok": True, "workspace_path": w_path}
    else:
        raise HTTPException(status_code=500, detail="Failed to update workspace path")


# ─── v0.7.61+ Workspace tree (read-only) ────────────────────────────────
# WorkspacePage에 OS 파일 트리 노출. READ-ONLY: raven은 절대 workspace 파일을
# 수정하지 않음. 사용자가 외부에서 편집한 파일을 dashboard에서 바로 보고
# .md 파일은 인라인 미리보기.


@app.get("/api/vaults/{name}/workspace/tree")
def workspace_tree_endpoint(
    name: str,
    path: str = Query("", description="workspace-relative directory path"),
    depth: int = Query(DEFAULT_DEPTH, ge=1, le=MAX_DEPTH, description="recursion depth"),
    hidden: bool = Query(False, description="include dotfiles (.git, .venv, etc)"),
):
    """워크스페이스 디렉토리 1단계 트리 (read-only).

    보안: path는 workspace_root의 서브디렉토리만 허용. ../ 등 외부 traversal 거부.
    """
    v = _vault_or_404(name)
    w_path = v.meta.workspace_path
    if not w_path:
        raise HTTPException(status_code=400, detail="No workspace associated with this vault")

    root = Path(w_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Workspace directory does not exist: {w_path}",
        )

    try:
        result = list_workspace_dir(
            workspace_root=root,
            relative=path,
            depth=depth,
            include_hidden=hidden,
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotADirectoryError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True, **result}


@app.get("/api/vaults/{name}/workspace/file")
def workspace_file_endpoint(
    name: str,
    path: str = Query(..., description="workspace-relative file path"),
):
    """워크스페이스 안 파일 read (인라인 미리보기 용).

    최대 256KB. 큰 파일은 truncated. READ-ONLY.
    """
    v = _vault_or_404(name)
    w_path = v.meta.workspace_path
    if not w_path:
        raise HTTPException(status_code=400, detail="No workspace associated with this vault")

    root = Path(w_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Workspace directory does not exist: {w_path}",
        )

    try:
        result = read_workspace_file(workspace_root=root, relative=path)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IsADirectoryError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True, **result}


def _run_git(cwd: str, args: list[str]) -> tuple[bool, str]:
    import subprocess
    import shutil
    if not shutil.which("git"):
        return False, "git binary not found on the server"
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            errors="replace"
        )
        if res.returncode != 0:
            return False, res.stderr.strip()
        return True, res.stdout
    except Exception as e:
        return False, str(e)


@app.get("/api/vaults/{name}/git/status")
def git_status(name: str):
    v = _vault_or_404(name)
    w_path = v.meta.workspace_path
    if not w_path:
        return {"ok": True, "has_workspace": False, "is_git": False}

    p = Path(w_path).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        return {"ok": True, "has_workspace": True, "workspace_path": w_path, "is_git": False, "error": f"Workspace directory does not exist: {w_path}"}

    success, stdout = _run_git(str(p), ["rev-parse", "--is-inside-work-tree"])
    if not success or stdout.strip() != "true":
        return {"ok": True, "has_workspace": True, "workspace_path": str(p), "is_git": False}

    success, branch = _run_git(str(p), ["branch", "--show-current"])
    branch = branch.strip() if success else ""
    if not branch:
        success, branch_det = _run_git(str(p), ["rev-parse", "--abbrev-ref", "HEAD"])
        branch = branch_det.strip() if success else "detached"

    success, commit_sha = _run_git(str(p), ["rev-parse", "--short", "HEAD"])
    commit_sha = commit_sha.strip() if success else "unknown"

    success, status_out = _run_git(str(p), ["status", "--porcelain"])
    if not success:
        return {"ok": False, "error": f"Failed to get git status: {status_out}"}

    changes = []
    for line in status_out.splitlines():
        if len(line) >= 4:
            status = line[:2]
            filepath = line[3:]
            changes.append({"file": filepath, "status": status})

    return {
        "ok": True,
        "has_workspace": True,
        "workspace_path": str(p),
        "is_git": True,
        "branch": branch,
        "commit": commit_sha,
        "changes": changes,
    }


@app.get("/api/vaults/{name}/git/diff")
def git_diff(name: str, file: Optional[str] = Query(None, description="relative file path to show diff for")):
    v = _vault_or_404(name)
    w_path = v.meta.workspace_path
    if not w_path:
        raise HTTPException(status_code=400, detail="No workspace associated with this vault")

    p = Path(w_path).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=404, detail=f"Workspace directory does not exist: {w_path}")

    args = ["diff", "HEAD"]
    if file:
        f_path = Path(file)
        if not f_path.is_absolute():
            f_path = (p / f_path).resolve()
        else:
            f_path = f_path.resolve()

        try:
            f_path.relative_to(p)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: file must be inside the workspace directory")

        # Handle untracked file diff against empty
        success, status_out = _run_git(str(p), ["status", "--porcelain", str(f_path)])
        if success and status_out.startswith("??"):
            _, diff_content = _run_git(str(p), ["diff", "--no-index", "/dev/null", str(f_path)])
            file_content = ""
            if f_path.exists() and f_path.is_file():
                try:
                    file_content = f_path.read_text(errors="replace")
                except Exception as e:
                    file_content = f"// Error reading file: {e}\n"
            return {
                "ok": True,
                "workspace_path": str(p),
                "file": file,
                "diff": diff_content or f"+++ b/{file}\n" + file_content
            }

        args.append("--")
        args.append(str(f_path))

    success, diff_content = _run_git(str(p), args)
    if not success and not diff_content:
        return {"ok": False, "error": f"Failed to get git diff: {diff_content}"}

    return {
        "ok": True,
        "workspace_path": str(p),
        "file": file,
        "diff": diff_content,
    }


class VaultCreate(BaseModel):
    name: str = Field(..., description="vault name (lowercase kebab-case 권장)")
    path: str = Field(..., description="absolute path to vault directory")
    mode: str = Field("personal", description="personal | shared | agent")
    owner: str = Field("user", description="user or agent name")
    description: str = Field("", description="free text")
    bootstrap: bool = Field(
        True,
        description=(
            "Lite bootstrap policy: if True, copy ONLY agent-facing essentials "
            "(SCHEMA, PROJECT-WORKFLOW, log.md). Tier 1 raven-internal "
            "docs (OPERATIONS, agent/*, raven-policy) are NEVER auto-copied. "
            "Use `raven docs` command to read raven-internal docs."
        ),
    )
    profile: str = Field("llm-wiki", description="basic | llm-wiki")


@app.post("/api/vaults/create")
def create_vault(payload: VaultCreate):
    """Create a new vault on disk + register it.

    Mirrors `raven vault create <name> <path> --mode <mode>`.

    Tier boundary policy: regardless of bootstrap flag, raven-internal
    operational docs (OPERATIONS.md, agent/*, raven-policy.md) are NEVER
    copied into the user vault. This enforces the 2-tier boundary
    (Tier 1 = raven package, Tier 2 = user vault).
    """
    from raven.core.vault import Vault as _Vault

    # Validate: name not already taken
    if registry().get(payload.name):
        raise HTTPException(status_code=409, detail=f"vault {payload.name!r} already exists")

    runtime_path, display_path = _resolve_vault_create_paths(Path(payload.path))

    try:
        v = _Vault.create(
            name=payload.name,
            path=runtime_path,
            mode=payload.mode,
            owner=payload.owner,
            description=payload.description,
            bootstrap=payload.bootstrap,
            profile=payload.profile,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"create failed: {e}")

    if display_path != runtime_path:
        from raven.core.registry import VaultMeta as _VM

        display_meta = _VM(
            name=v.meta.name,
            path=display_path,
            mode=v.meta.mode,
            owner=v.meta.owner,
            created=v.meta.created,
            description=v.meta.description,
            default=v.meta.default,
            allow_tier1_leak=v.meta.allow_tier1_leak,
            features=v.meta.features,
        )
        (runtime_path / ".vault.json").write_text(
            json.dumps(display_meta.to_json(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        reg = registry()
        reg._data.setdefault("vaults", {})[payload.name] = display_meta.to_json()
        reg._save()

    return {
        "ok": True,
        "vault": {
            "name": v.meta.name,
            "path": str(display_path),
            "mode": v.meta.mode,
            "owner": v.meta.owner,
            "default": v.meta.name == registry()._data.get("default", ""),
            "bootstrapped": payload.bootstrap,
        },
    }


@app.post("/api/vaults/{name}/verify")
def verify_vault_bootstrap(name: str):
    """Verify the vault's Lite bootstrap files match source templates (SHA256).

    M4 F3 — Bootstrap Self-Test. Mirrors `raven vault verify <name>`.

    Returns:
        ok=True if all Lite bootstrap files match the source templates.
        ok=False with per-file checks otherwise.
    """
    v = _vault_or_404(name)
    result = v.verify_bootstrap()
    payload = result.to_dict()
    if not result.ok:
        raise HTTPException(status_code=409, detail=payload)
    return payload


class VaultBootstrapPayload(BaseModel):
    profile: str = Field("llm-wiki", description="basic | llm-wiki")


@app.post("/api/vaults/{name}/bootstrap")
def bootstrap_vault(name: str, payload: VaultBootstrapPayload):
    """Apply/Overwrite profile bootstrap into an existing vault."""
    v = _vault_or_404(name)
    if payload.profile not in ("basic", "llm-wiki"):
        raise HTTPException(status_code=400, detail="invalid profile")
    try:
        from raven.core.vault import Vault as _Vault
        if payload.profile == "basic":
            _Vault._bootstrap_basic(v.root)
        else:
            v.sync_meta(lite=True, force=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"bootstrap failed: {e}")
    return {"ok": True, "profile": payload.profile}


# ────────────────────────── page endpoints ──────────────────────────

# v0.6.16+: 폴더는 1차 시민. OS 파일시스템을 SOT로 한다.
# _meta/, _archive/, _deprecated/ 같은 Raven 시스템 폴더는 sidebar에서 제외한다.
RAVEN_SYSTEM_DIRS = {"_meta", "_archive", "_deprecated", "_templates"}
# 보관소(Vault)의 대문/홈페이지 역할을 하는 파일명(stem) 후보군 (최상단 정렬 대상)
INDEX_FILE_STEMS = {"index", "readme", "home"}


def _build_tree_node(path: Path, v_root: Path) -> dict:
    """폴더 노드 1개를 dict로. 자식은 재귀."""
    rel = str(path.relative_to(v_root))
    children: list[dict] = []
    try:
        # 인덱스 예약 파일(index, readme 등)을 최상단에 예외 배치하고, 그 아래로 폴더 -> 일반 파일 순으로 정렬합니다.
        for entry in sorted(
            path.iterdir(),
            key=lambda p: (
                not (p.is_file() and p.stem.lower() in INDEX_FILE_STEMS),
                not p.is_dir(),
                p.name.lower()
            )
        ):
            name = entry.name
            if entry.is_dir():
                if name in RAVEN_SYSTEM_DIRS:
                    continue
                children.append(_build_tree_node(entry, v_root))
            elif entry.is_file() and name.endswith(".md"):
                # page 노드
                text = entry.read_text(errors="replace")
                meta, _ = _split_fm(text)
                slug = str(entry.relative_to(v_root))[:-3]
                children.append({
                    "type": "page",
                    "path": slug,
                    "slug": slug,
                    "title": meta.get("title", slug),
                    "pageType": meta.get("type", "?"),
                })
    except (PermissionError, OSError):
        pass
    return {"type": "dir", "path": rel, "children": children}


@app.get("/api/vaults/{name}/tree")
def vault_tree(name: str):
    """Vault 트리 (v0.6.16+). 폴더 + 페이지. 빈 폴더도 포함.

    폴더는 OS 디렉토리 그대로. 메타데이터 저장 안 함. `os.walk` 기반.
    응답:
        {
          "ok": true,
          "vault": name,
          "tree": {
            "type": "dir",
            "path": "content",
            "children": [
              {"type": "dir", "path": "content/concept", "children": [...]},
              {"type": "page", "path": "content/concept/users",
               "slug": "content/concept/users", "title": "...", "pageType": "concept"}
            ]
          }
        }
    """
    v = _vault_or_404(name)
    return {
        "ok": True,
        "vault": name,
        "tree": _build_tree_node(v.content_root, v.root),
    }


class FolderCreate(BaseModel):
    path: str = Field(..., description="vault-relative folder path, e.g. 'content/users/admin'")


@app.post("/api/vaults/{name}/folders")
def create_folder(name: str, payload: FolderCreate):
    """폴더 생성 (v0.6.16+). mkdir. 부수 파일 생성 안 함.

    - payload.path는 vault-relative. 슬래시로 끝나도 OK.
    - depth 제한 없음. 단, '..' / 절대경로 / NUL은 400.
    - 이미 존재하면 409.
    """
    v = _vault_or_404(name)
    raw = payload.path.strip().strip("/").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="folder path is empty")
    if raw in {"", "."}:
        raise HTTPException(status_code=400, detail="folder path is empty")
    # 안전 검증: slug_module 재활용 (페이지 slug와 동일 가드).
    try:
        validated = slug_module.validate(raw, vault_root=v.root)
    except slug_module.SlugError as e:
        raise HTTPException(status_code=400, detail=f"invalid folder path: {e}")
    if validated.suffix == ".md":
        raise HTTPException(status_code=400, detail="folder path ends with .md")
    if validated.exists():
        if validated.is_file():
            raise HTTPException(status_code=409, detail=f"path {raw!r} is a file")
        # 디렉토리면 멱등 — 이미 존재해도 OK
        return {"ok": True, "vault": name, "path": raw, "existed": True}
    # 충돌: 같은 path에 .md 파일이 있으면 실패
    md_path = validated.with_suffix(".md")
    if md_path.exists():
        raise HTTPException(
            status_code=409,
            detail=f"a page already exists at {raw!r} ({md_path.name})",
        )
    validated.mkdir(parents=True, exist_ok=False)
    return {"ok": True, "vault": name, "path": raw, "existed": False}


@app.get("/api/vaults/{name}/pages")
def list_pages(
    name: str,
    type: Optional[str] = Query(None, description="filter by frontmatter type"),
    tag: Optional[str] = Query(None, description="filter by tag substring"),
):
    v = _vault_or_404(name)
    rows = []
    for fp in v.content_root.rglob("*.md"):
        text = fp.read_text(errors="replace")
        meta, _ = _split_fm(text)
        slug = str(fp.relative_to(v.root))[:-3]
        if type and meta.get("type") != type:
            continue
        if tag and tag not in meta.get("tags", ""):
            continue
        rows.append({
            "slug": slug,
            "title": meta.get("title", slug),
            "type": meta.get("type", "?"),
            "updated": meta.get("updated", ""),
        })
    return {"ok": True, "vault": name, "pages": rows}


class GraphLayoutParams(BaseModel):
    iterations: int = Field(500, ge=1, le=2000, description="spring iterations (FR-style)")


def _normalize_layout(
    ids: list[str],
    pos_x: list[float],
    pos_y: list[float],
    target: float = 500.0,
) -> dict[str, tuple[float, float]]:
    """그래프 좌표를 center=0, scale=±target 으로 정규화한다."""
    n = len(ids)
    if n == 0:
        return {}
    if n == 1:
        return {ids[0]: (0.0, 0.0)}
    min_x, max_x = min(pos_x), max(pos_x)
    min_y, max_y = min(pos_y), max(pos_y)
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    span_x = max(abs(min_x - cx), abs(max_x - cx))
    span_y = max(abs(min_y - cy), abs(max_y - cy))
    span = max(span_x, span_y) or 1.0
    return {
        ids[i]: (
            round((pos_x[i] - cx) / span * target, 1),
            round((pos_y[i] - cy) / span * target, 1),
        )
        for i in range(n)
    }


def _stable_unit(slug: str, salt: str = "") -> float:
    """slug 기반 deterministic jitter: [0, 1)."""
    import hashlib

    h = hashlib.sha256(f"{salt}:{slug}".encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big") / float(1 << 64)


def _louvain_communities(
    ids: list[str],
    edges: list[tuple[str, str]],
    weights: list[float] | None = None,
    seed: int = 0,
) -> dict[str, int]:
    """Louvain-style community detection (v0.6.15+).

    표준 Louvain (Blondel 2008)의 multi-level ΔQ 최적화는 dense subgraph에서
    ΔQ=0 tie가 많아 결정적인 merge가 안 되는 경향이 있다. v1은 다음 두 단계로
    robust + deterministic + 의존성 없음 결과를 보장한다:

      1) Connected components 분리: 각 연결 컴포넌트는 다른 community로 시작.
      2) Within-component label propagation: 각 노드가 인접 community의
         최다 라벨로 adopt. 8번 반복. ΔQ > 0 같은 미세 비교 대신 "인접 다수결"
         만으로 merge.

    이 방식은 dense subgraph에서도 명확한 merge가 일어나며, 결정론적이며,
    의존성이 없다. 표준 Louvain의 quality에 비하면 약간 떨어질 수 있지만
    PKM use case (수십~수백 노드)에서 시각적 가독성은 더 낫다.

    결정론: 입력과 seed가 같으면 같은 community id. 발견 순서로 renumber.
    """
    from collections import Counter, defaultdict

    n = len(ids)
    if n == 0:
        return {}
    if n == 1:
        return {ids[0]: 0}
    idx = {s: i for i, s in enumerate(ids)}

    # Build undirected adjacency.
    adj: dict[int, list[int]] = defaultdict(list)
    for e in edges:
        s, t = e[0], e[1]
        if s in idx and t in idx and s != t:
            adj[idx[s]].append(idx[t])
            adj[idx[t]].append(idx[s])

    # Step 1: connected components as initial community.
    community = list(range(n))
    seen = [False] * n
    for start in range(n):
        if seen[start]:
            continue
        seen[start] = True
        stack = [start]
        while stack:
            u = stack.pop()
            for nb in adj[u]:
                if not seen[nb]:
                    seen[nb] = True
                    stack.append(nb)
            # Mark all reachable as same community: but only the first node
            # in a component dictates the label. We'll renumber later, so this
            # is just an initial seed — label propagation below overrides.

    # Step 2: label propagation. Each node adopts the most frequent label
    # among its neighbors (ties: lowest label wins). Repeat up to 8 times or
    # until convergence.
    for _iteration in range(8):
        moved = 0
        for i in range(n):
            if not adj[i]:
                continue
            labels = [community[nb] for nb in adj[i]]
            if not labels:
                continue
            counts = Counter(labels)
            best_label, _ = counts.most_common(1)[0]
            if best_label != community[i]:
                # Tie-break: if two labels tie, prefer the lower one. Counter
                # preserves insertion order; for stability we explicitly sort
                # by (-count, label) and pick first.
                sorted_labels = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
                best_label = sorted_labels[0][0]
                if best_label != community[i]:
                    community[i] = best_label
                    moved += 1
        if moved == 0:
            break

    # Renumber communities to 0..K-1 in first-appearance order.
    remap: dict[int, int] = {}
    next_id = 0
    for c in community:
        if c not in remap:
            remap[c] = next_id
            next_id += 1
    return {ids[i]: remap[community[i]] for i in range(n)}


def _constellation_layout(
    ids: list[str],
    edges: list[tuple[str, str]],
    weights: dict[str, int] | None = None,
) -> dict[str, tuple[float, float]]:
    """Obsidian식 별자리/신경망 감각의 deterministic graph layout.

    v1 기준:
    - degree/weight 높은 hub는 component 중심부에 배치
    - hub의 1-hop 이웃은 hub 주변 궤도, leaf/low-degree는 바깥 ring에 배치
    - connected components는 큰 원 둘레에 분리
    - slug hash 기반 각도 jitter로 입력이 같으면 항상 같은 좌표
    - 최종 좌표는 기존 graph contract처럼 center=0, scale=±500
    """
    import math

    n = len(ids)
    if n == 0:
        return {}
    if n == 1:
        return {ids[0]: (0.0, 0.0)}

    weights = weights or {}
    idx = {s: i for i, s in enumerate(ids)}
    adj: dict[str, set[str]] = {s: set() for s in ids}
    for s, t in edges:
        if s in idx and t in idx and s != t:
            adj[s].add(t)
            adj[t].add(s)

    # connected components — 큰 component를 먼저 배치해 전체 별자리의 주 구조를 잡는다.
    remaining = set(ids)
    components: list[list[str]] = []
    while remaining:
        start = min(remaining)
        stack = [start]
        remaining.remove(start)
        comp: list[str] = []
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nb in sorted(adj[cur]):
                if nb in remaining:
                    remaining.remove(nb)
                    stack.append(nb)
        components.append(comp)

    def node_score(slug: str) -> tuple[int, int, float, str]:
        degree = len(adj[slug])
        weight = int(weights.get(slug, 0) or 0)
        # degree가 가장 중요하고, in-degree/weight가 hub tie-breaker 역할.
        return (degree * 10 + weight * 3, degree, _stable_unit(slug, "hub"), slug)

    components.sort(key=lambda c: (-len(c), -max(node_score(s)[0] for s in c), min(c)))
    comp_count = len(components)
    global_pos: dict[str, tuple[float, float]] = {}

    for comp_i, comp in enumerate(components):
        comp_size = len(comp)
        hub = max(comp, key=node_score)

        # Component 중심: 단일/최대 component는 원점, 나머지는 큰 원 둘레에 deterministic 분리.
        if comp_count == 1:
            comp_cx = comp_cy = 0.0
        else:
            outer_r = 520.0 + 170.0 * math.sqrt(comp_count)
            if comp_i == 0 and comp_size > 1:
                comp_cx = comp_cy = 0.0
            else:
                angle = (2.0 * math.pi * (comp_i - 1) / max(comp_count - 1, 1))
                angle += (_stable_unit(hub, "component") - 0.5) * 0.28
                comp_cx = math.cos(angle) * outer_r
                comp_cy = math.sin(angle) * outer_r

        if comp_size == 1:
            angle = 2.0 * math.pi * _stable_unit(hub, "isolated")
            # 완전 고립 노드가 너무 멀리 이탈해 전체 레이아웃 정규화 스케일을 쪼그려트리지 않도록 반지름 조정
            r = 160.0 + 25.0 * math.sqrt(comp_i)
            global_pos[hub] = (comp_cx + math.cos(angle) * r, comp_cy + math.sin(angle) * r)
            continue

        # Hub 중심. weight가 높은 hub가 시각 중심을 잡고, 주변 node는 level ring에 배치.
        global_pos[hub] = (comp_cx, comp_cy)

        # BFS level: hub 주변 1-hop ring, 그 밖은 더 외곽 ring.
        levels: dict[str, int] = {hub: 0}
        queue = [hub]
        for cur in queue:
            for nb in sorted(adj[cur]):
                if nb in comp and nb not in levels:
                    levels[nb] = levels[cur] + 1
                    queue.append(nb)

        rings: dict[int, list[str]] = {}
        for slug in comp:
            if slug == hub:
                continue
            level = levels.get(slug, 2)
            degree = len(adj[slug])
            # leaf/low-degree는 같은 level에서도 한 단계 바깥으로 밀어 별자리 꼬리를 만든다.
            ring = level
            if degree <= 1:
                ring += 1
            rings.setdefault(ring, []).append(slug)

        base_angle = 2.0 * math.pi * _stable_unit(hub, "base-angle")
        for ring, slugs in sorted(rings.items()):
            slugs.sort(key=lambda s: (_stable_unit(s, f"ring-{ring}"), s))
            count = len(slugs)
            # 1-hop orbit은 촘촘히, leaf/outer ring은 넓게.
            radius = 85.0 + 80.0 * ring + 12.0 * math.sqrt(comp_size)
            for j, slug in enumerate(slugs):
                angle = base_angle + 2.0 * math.pi * j / max(count, 1)
                angle += (_stable_unit(slug, "angle-jitter") - 0.5) * (0.45 / max(ring, 1))
                radial_jitter = (_stable_unit(slug, "radius-jitter") - 0.5) * 36.0
                degree = len(adj[slug])
                if degree >= 3:
                    radial_jitter -= 45.0  # secondary hub는 안쪽으로
                elif degree <= 1:
                    radial_jitter += 55.0  # leaf는 바깥으로
                r = radius + radial_jitter
                global_pos[slug] = (comp_cx + math.cos(angle) * r, comp_cy + math.sin(angle) * r)

    pos_x = [global_pos.get(s, (0.0, 0.0))[0] for s in ids]
    pos_y = [global_pos.get(s, (0.0, 0.0))[1] for s in ids]
    return _normalize_layout(ids, pos_x, pos_y)


def _forceatlas_layout(
    ids: list[str],
    edges: list[tuple[str, str]],
    weights: dict[str, int] | None = None,
    # v0.7.49+: iterations 기본값 320→400. community_hub 강화(repulsion↓)로
    # 수렴 시간이 더 필요해짐. deterministic & iterations 상한(500) 내.
    iterations: int = 400,
    communities: dict[str, int] | None = None,
) -> dict[str, tuple[float, float]]:
    """ForceAtlas2 / LinLog hybrid v2 — PKM 문서 그래프 가독성 우선.

    v1 (0b71e5e) 대비 개선점 (v2):
      - attraction: log1p(d)·d → d (선형) — 같은 군집이 더 강하게 뭉친다.
      - per-node mass = 1 + degree + 0.6·sqrt(weight) — hub가 너무 커지지 않게 cap.
      - repulsion: mass-스케일 + 1/r (degenerate 막기 위해 +1 jitter) — 큰 hub 주변이 비좁지 않게.
      - per-component seed offset: connected component별로 ±R 떨어뜨려서 seed에서도
        군집 간 분리가 시작되게 한다. 그 후 force로 다듬는다.
      - iterations 220 → 320 (deterministic, 출력 안정).
      - output은 기존 graph contract: center=0, scale=±500.

    v0.7.6x+ (다른 layout 전부 제거하고 atlas 단일화하며 밀도 튠업):
      - mass의 degree cap 6→12: 촘촘한 실사용 vault(평균 degree 6.8)에서
        degree 8~17인 진짜 허브가 cap 6짜리와 동급 취급되어 이웃을 충분히
        못 밀어내던 문제 수정.
      - repulsion이 그래프 평균 degree에 비례해서 커짐 (1100 * (1+avg/20)) —
        성긴 그래프는 기존과 거의 동일, 촘촘한 그래프는 그만큼 더 벌어짐.
    결정론: random 없음. 입력과 시드가 같으면 같은 좌표.
    """
    import math

    n = len(ids)
    if n == 0:
        return {}
    if n == 1:
        return {ids[0]: (0.0, 0.0)}

    weights = weights or {}
    idx = {s: i for i, s in enumerate(ids)}
    valid_edges = [(s, t) for s, t in edges if s in idx and t in idx and s != t]

    # Seed: 기존 constellation 결과를 사용하되, 연결 컴포넌트별 중심을 멀리 떨어뜨려
    # force가 시작부터 군집을 분리할 수 있게 한다. → LinLog의 핵심.
    seed = _constellation_layout(ids, valid_edges, weights=weights)
    pos_x = [seed.get(s, (0.0, 0.0))[0] for s in ids]
    pos_y = [seed.get(s, (0.0, 0.0))[1] for s in ids]

    # Connected components — 각 컴포넌트의 centroid를 0 주변에서 ring으로 배치.
    from collections import deque
    seen = [False] * n
    components: list[list[int]] = []
    for start in range(n):
        if seen[start]:
            continue
        seen[start] = True
        comp: list[int] = [start]
        dq = deque([start])
        while dq:
            u = dq.popleft()
            for s, t in valid_edges:
                su, tu = idx[s], idx[t]
                for v in (su, tu):
                    if v == u or seen[v]:
                        continue
                    seen[v] = True
                    comp.append(v)
                    dq.append(v)
        components.append(comp)
    if len(components) > 1:
        ring_r = 180.0 + 30.0 * (len(components) - 1)
        for k, comp in enumerate(components):
            ang = (2 * math.pi * k) / max(len(components), 1)
            cx = ring_r * math.cos(ang)
            cy = ring_r * math.sin(ang)
            for v in comp:
                pos_x[v] += cx
                pos_y[v] += cy

    degree = [0] * n
    for s, t in valid_edges:
        degree[idx[s]] += 1
        degree[idx[t]] += 1
    # 고립 노드(degree=0)는 척력을 극히 덜 받게 하여 중심부 중력으로 묶이게 mass를 0.3으로 억제
    # v0.7.6x+: degree cap 6→12. PKM 위키는 평균 degree가 6~7대까지 촘촘한 경우가
    # 흔한데(hub-control-room 실측 6.8), cap이 6이면 degree 8~17짜리 진짜 허브가
    # degree 6짜리와 똑같은 mass를 받아 이웃을 충분히 못 밀어냄 — 허브 주변만
    # 유독 빽빽해지는 원인이었다. cap을 올려서 진짜 허브가 이웃을 더 세게 밀어내게.
    mass = [
        0.3 if degree[i] == 0 else
        1.0 + min(degree[i], 12) * 0.55 + math.sqrt(max(int(weights.get(ids[i], 0) or 0), 0)) * 0.6
        for i in range(n)
    ]

    steps = max(40, min(iterations, 500))
    # v0.7.49+: 성운 군집화 강화. community_hub 0.10→0.25 (은하 핵 인력 2.5배),
    # repulsion 1400→1100 (척력 약화 → 더 조밀). iterations 320→400 (수렴 안정).
    # 결정론/normalize_layout contract 유지. frontend 무변경.
    # v0.7.6x+: repulsion을 그래프 밀도(평균 degree)에 비례해서 올림. 성긴
    # 그래프(평균 degree ≲2)는 기존 1100 근처를 유지하고, 촘촘한 그래프일수록
    # (attraction이 그만큼 많은 edge로 강하게 당기므로) 더 벌어지게 보정한다.
    avg_degree = (sum(degree) / n) if n else 0.0
    repulsion = 1100.0 * (1.0 + avg_degree / 20.0)
    attraction = 0.15
    gravity = 0.045
    # v0.7.6x+: 28→50. repulsion을 올린 것만으론 부족했다 — 실측(hub-control-room,
    # 36 nodes) 결과 max_step0=28 그대로면 iterations=500 예산 안에서 더 강해진
    # 힘이 충분히 수렴 못 해 오히려 튜닝 전보다 더 뭉쳐 보였다(회귀). max_step0을
    # 같이 올려야 같은 iterations 예산으로도 새 힘의 크기에 맞게 수렴한다.
    # (iterations 자체를 올리는 방향은 O(n²)이라 n=300에서 20s, n=600에서 82s로
    # 폭증해 기각 — 성능 예산은 그대로 두고 수렴 속도만 개선.)
    max_step0 = 50.0

    edge_indices = [(idx[s], idx[t]) for s, t in valid_edges]

    for it in range(steps):
        temp = max_step0 * (1.0 - (it / max(steps - 1, 1))) + 1.0
        dx = [0.0] * n
        dy = [0.0] * n

        # 각 커뮤니티의 Centroid 계산 (매 iteration 마다)
        comm_centroids: dict[int, list[float]] = {}
        if communities:
            for i in range(n):
                c = communities.get(ids[i], -1)
                if c >= 0:
                    data = comm_centroids.setdefault(c, [0.0, 0.0, 0.0])
                    data[0] += pos_x[i]
                    data[1] += pos_y[i]
                    data[2] += 1.0
            for c, data in comm_centroids.items():
                if data[2] > 0:
                    data[0] /= data[2]
                    data[1] /= data[2]

        # Repulsion (mass-scaled) & Collision (겹침 방지). 모든 노드쌍
        for i in range(n):
            for j in range(i + 1, n):
                vx = pos_x[i] - pos_x[j]
                vy = pos_y[i] - pos_y[j]
                d2 = vx * vx + vy * vy + 0.01
                d = math.sqrt(d2)
                
                # 기본 ForceAtlas 척력
                f = repulsion * mass[i] * mass[j] / d2
                fx = (vx / d) * f
                fy = (vy / d) * f
                
                # Collision Guard: 옵시디언 감성을 위한 겹침 방지 탄성 (노드 최소 반경 약 20px 보장)
                min_dist = 20.0
                if d < min_dist:
                    overlap = min_dist - d
                    col_f = (overlap * overlap) * 12.0  # 탄성 강도
                    fx += (vx / d) * col_f
                    fy += (vy / d) * col_f
                
                dx[i] += fx
                dy[i] += fy
                dx[j] -= fx
                dy[j] -= fy

        # Linear attraction: 거리 비례 — 짧은 edge는 강하게, 긴 edge는 약하게.
        # LinLog와 다른 선택이지만 PKM 위키처럼 군집이 응집되어 있을 때 더 예쁘게 모임.
        for i, j in edge_indices:
            vx = pos_x[i] - pos_x[j]
            vy = pos_y[i] - pos_y[j]
            d = math.sqrt(vx * vx + vy * vy) + 0.001
            f = attraction * d
            fx = (vx / d) * f
            fy = (vy / d) * f
            dx[i] -= fx
            dy[i] -= fy
            dx[j] += fx
            dy[j] += fy

        # Gravity: center 방향으로 약한 인력 & 커뮤니티 중심 중력 (은하 핵 인력)
        for i in range(n):
            dx[i] -= pos_x[i] * gravity
            dy[i] -= pos_y[i] * gravity
            if communities:
                c = communities.get(ids[i], -1)
                if c >= 0 and c in comm_centroids:
                    cx, cy, _ = comm_centroids[c]
                    # v0.7.49+: 자신 소속 커뮤니티 중심(은하 핵)으로 인력 0.10→0.25.
                    # 같은 community 노드들이 더 강하게 centroid로 빨려들어
                    # "성운 군집" 효과가 뚜렷해진다.
                    dx[i] -= (pos_x[i] - cx) * 0.25
                    dy[i] -= (pos_y[i] - cy) * 0.25

        for i in range(n):
            disp = math.sqrt(dx[i] * dx[i] + dy[i] * dy[i])
            if disp <= 0.0001:
                continue
            scale = min(disp, temp) / disp
            pos_x[i] += dx[i] * scale
            pos_y[i] += dy[i] * scale

    return _normalize_layout(ids, pos_x, pos_y)


@app.get("/api/vaults/{name}/graph")
def vault_graph(
    name: str,
    iterations: int = Query(500, ge=1, le=2000, description="spring iterations"),
    community: Literal["none", "modularity"] = Query(
        "none",
        description="community detection (v0.6.15+): 'modularity' attaches a "
        "Louvain-style community id per node so the dashboard can color by "
        "structure instead of metadata. 'none' skips the computation.",
    ),
):
    """vault 페이지 + wikilink edges + graph layout 좌표를 반환.

    v0.6.10+: nodes[i].x, nodes[i].y = 서버 계산 graph layout 좌표.
    v0.7.6x+: layout은 atlas(ForceAtlas2/LinLog hybrid) 고정 — 다른 레이아웃은
        노드 위치가 실제 위키링크 구조와 무관해 허브 뭉침/레이어 크로우딩
        문제가 있어 제거함 (docs/architecture.md D10/D11 참고).
    v0.6.15+: ?community=modularity attaches nodes[i].community = Louvain-style
        community id (0..K-1). 'none' (default) skips the call.

    nodes: [{id: slug, title, type, weight, x, y, community?}]
    edges: [{source: src_slug, target: tgt_slug}]

    wiki.db의 links 테이블에서 source/target 직접 매칭 (정확성 우선).
    wiki.db가 없으면 (구 vault) rglob fallback.
    """
    v = _vault_or_404(name)

    # 1) wiki.db가 있으면 DB 사용 (정확)
    wiki_db = v.root / "wiki.db"
    if wiki_db.exists():
        try:
            import sqlite3
            db = sqlite3.connect(str(wiki_db))
            db.row_factory = sqlite3.Row
            pages = db.execute("SELECT slug, title, type FROM pages").fetchall()
            # in-degree: target_slug별 들어오는 edge 수 (auto+broken 한정, missing 제외)
            in_deg_raw = db.execute(
                "SELECT target_slug, COUNT(*) AS cnt FROM links "
                "WHERE intent IN ('auto', 'broken') GROUP BY target_slug"
            ).fetchall()
            in_degree = {r["target_slug"]: r["cnt"] for r in in_deg_raw}
            nodes = [
                {
                    "id": p["slug"],
                    "slug": p["slug"],
                    "title": p["title"],
                    "type": p["type"],
                    "weight": in_degree.get(p["slug"], 0),
                }
                for p in pages
            ]
            # 각 노드의 markdown frontmatter에서 importance 수치를 파싱하여 하이브리드 가중치로 보정
            for node in nodes:
                slug = node["slug"]
                node_fp = v.root / f"{slug}.md"
                importance = 1
                if node_fp.exists():
                    try:
                        text = node_fp.read_text(errors="replace")
                        if text.startswith("---"):
                            fm_part = text.split("---", 2)[1]
                            for line in fm_part.splitlines():
                                if ":" in line:
                                    k, val = line.split(":", 1)
                                    if k.strip() == "importance":
                                        try:
                                            importance = int(val.strip())
                                        except Exception:
                                            pass
                                        break
                    except Exception:
                        pass
                node["importance"] = importance
                # 하이브리드 가중치 = in-degree 링크 수 + (importance - 1) * 3.5
                node["weight"] = int(in_degree.get(slug, 0) + (importance - 1) * 3.5)
            # intent='auto' or 'broken' 만 edge로 (missing은 의도적 placeholder)
            edges_raw = db.execute(
                "SELECT source_slug, target_slug FROM links WHERE intent IN ('auto', 'broken')"
            ).fetchall()
            # 양방향 상호 링킹(A->B, B->A) 및 중복 엣지 제거 -> 단일 무방향 엣지로 정돈
            seen_pairs = set()
            unique_edges = []
            for r in edges_raw:
                s, t = r["source_slug"], r["target_slug"]
                if s == t:
                    continue  # self-loop 방지
                pair = (min(s, t), max(s, t))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    unique_edges.append({"source": s, "target": t})
            edges = unique_edges
            db.close()
            # Patch A1 (v0.6.10+): force-directed 좌표 부착 (서버 1회 계산, 결정론).
            ids = [n["id"] for n in nodes]
            edge_pairs = [(e["source"], e["target"]) for e in edges]
            weights = {n["id"]: int(n.get("weight", 0) or 0) for n in nodes}

            # 은하 중심 중력 및 시각 군집화를 위해 커뮤니티를 레이아웃 전에 항상 계산
            comm_map = _louvain_communities(ids, edge_pairs)
            for node in nodes:
                node["community"] = comm_map.get(node["id"], -1)

            layout_coords = _forceatlas_layout(
                ids, edge_pairs, weights=weights, iterations=iterations, communities=comm_map
            )
            for node in nodes:
                xy = layout_coords.get(node["id"], (0.0, 0.0))
                node["x"] = xy[0]
                node["y"] = xy[1]
            return {
                "ok": True,
                "vault": name,
                "nodes": nodes,
                "edges": edges,
                "stats": {"nodes": len(nodes), "edges": len(edges)},
            }
        except Exception as e:
            # Silent failure 방지 및 디버깅을 위한 에러 로깅
            import sys
            import traceback
            sys.stderr.write(f"⚠️  [vault_graph] wiki.db load failed for vault {name}: {e}\n")
            traceback.print_exc(file=sys.stderr)
            pass  # fallback to rglob

    # 2) wiki.db 없거나 실패 시 — rglob fallback (구 vault)
    nodes = []
    seen = set()
    for fp in v.content_root.rglob("*.md"):
        text = fp.read_text(errors="replace")
        meta, _ = _split_fm(text)
        slug = str(fp.relative_to(v.root))[:-3]
        if slug in seen:
            continue
        seen.add(slug)
        nodes.append({
            "id": slug,
            "slug": slug,
            "title": meta.get("title", slug),
            "type": meta.get("type", "?"),
        })

    import re
    wikilink_re = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
    edges = []
    edge_set = set()
    # in-degree 카운트 — rglob fallback에서도 weight 필드 보존 (대시보드 UI 일관성)
    in_degree: dict[str, int] = {}
    for fp in v.content_root.rglob("*.md"):
        text = fp.read_text(errors="replace")
        meta, body = _split_fm(text)
        src = str(fp.relative_to(v.root))[:-3]
        for m in wikilink_re.finditer(body):
            tgt = m.group(1).strip()
            if not tgt:
                continue
            if tgt.endswith(".md"):
                tgt = tgt[:-3]
            if tgt == src:
                continue
            # rglob fallback 짧은 slug 보정 (예: "purpose" -> "content/concept/purpose")
            resolved_tgt = tgt
            if tgt:
                candidates = [n["id"] for n in nodes if n["id"] == tgt or n["id"].endswith("/" + tgt)]
                if candidates:
                    resolved_tgt = min(candidates, key=len)  # 가장 짧은 경로 우선
            # 양방향 상호 링킹 및 중복 엣지 제거 -> 단일 무방향 엣지로 정돈
            key = (min(src, resolved_tgt), max(src, resolved_tgt))
            if key in edge_set:
                continue
            edge_set.add(key)
            edges.append({"source": src, "target": resolved_tgt})
            in_degree[resolved_tgt] = in_degree.get(resolved_tgt, 0) + 1

    # nodes에 weight 부착 및 importance 파싱
    for node in nodes:
        slug = node["slug"]
        node_fp = v.root / f"{slug}.md"
        importance = 1
        if node_fp.exists():
            try:
                text = node_fp.read_text(errors="replace")
                if text.startswith("---"):
                    fm_part = text.split("---", 2)[1]
                    for line in fm_part.splitlines():
                        if ":" in line:
                            k, val = line.split(":", 1)
                            if k.strip() == "importance":
                                try:
                                    importance = int(val.strip())
                                except Exception:
                                    pass
                                break
            except Exception:
                pass
        node["importance"] = importance
        node["weight"] = int(in_degree.get(node["id"], 0) + (importance - 1) * 3.5)

    # Patch A1 (v0.6.10+): force-directed 좌표 부착 (fallback 분기).
    ids = [n["id"] for n in nodes]
    edge_pairs = [(e["source"], e["target"]) for e in edges]
    weights = {n["id"]: int(n.get("weight", 0) or 0) for n in nodes}

    # fallback 분기에서도 커뮤니티 항상 계산
    comm_map = _louvain_communities(ids, edge_pairs)
    for node in nodes:
        node["community"] = comm_map.get(node["id"], -1)

    layout_coords = _forceatlas_layout(
        ids, edge_pairs, weights=weights, iterations=iterations, communities=comm_map
    )
    for node in nodes:
        xy = layout_coords.get(node["id"], (0.0, 0.0))
        node["x"] = xy[0]
        node["y"] = xy[1]

    return {
        "ok": True,
        "vault": name,
        "nodes": nodes,
        "edges": edges,
        "stats": {"nodes": len(nodes), "edges": len(edges)},
    }


@app.get("/api/vaults/{name}/pages/{slug:path}")
def get_page(name: str, slug: str):
    v = _vault_or_404(name)
    fp = _safe_slug_or_400(slug, v).with_suffix(".md")
    if not fp.exists():
        # fuzzy fallback (옛 빌드 slug 호환): 짧은 slug로 호출 시 모든 pages 중
        # slug의 마지막 segment로 끝나는 것 찾기. 예: 'vault-structure' → 'concept/vault-structure'
        base = slug.rsplit("/", 1)[-1]  # 마지막 segment만
        candidates = []
        for fp_md in v.content_root.rglob("*.md"):
            cand_slug = str(fp_md.relative_to(v.root))[:-3]
            if cand_slug == base or cand_slug.endswith("/" + base):
                candidates.append(fp_md)
        if len(candidates) == 1:
            fp = candidates[0]
        elif len(candidates) > 1:
            # ambiguous — 가장 짧은 slug 우선 (root에 가까운 게 더 canonical)
            fp = min(candidates, key=lambda p: len(p.relative_to(v.root).parts))
        else:
            raise HTTPException(status_code=404, detail=f"page {slug!r} not found in vault {name!r}")
    text = fp.read_text()
    meta, body = _split_fm(text)

    # Fetch backlinks
    backlinks = []
    wiki_db = v.root / "wiki.db"
    if wiki_db.exists():
        try:
            import sqlite3
            db = sqlite3.connect(str(wiki_db))
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT l.source_slug, p.title "
                "FROM links l "
                "JOIN pages p ON l.source_slug = p.slug "
                "WHERE l.target_slug = ? AND l.intent IN ('auto', 'broken')",
                (slug,)
            ).fetchall()
            backlinks = [{"source_slug": r["source_slug"], "source_title": r["title"]} for r in rows]
            db.close()
        except Exception:
            pass

    if not backlinks:
        import re
        link_pat = re.compile(rf"\[\[{re.escape(slug)}(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]", re.IGNORECASE)
        for other_fp in v.content_root.rglob("*.md"):
            other_slug = str(other_fp.relative_to(v.root))[:-3]
            if other_slug == slug:
                continue
            try:
                content = other_fp.read_text(errors="replace")
                m, b = _split_fm(content)
                if link_pat.search(b):
                    backlinks.append({
                        "source_slug": other_slug,
                        "source_title": m.get("title", other_slug)
                    })
            except Exception:
                pass

    import os
    path_str = str(fp.resolve())
    host_dir = os.environ.get("RAVEN_VAULTS_DIR", "").strip()
    if host_dir:
        try:
            rel_from_vaults_root = fp.resolve().relative_to(registry().root.resolve())
            path_str = str(Path(host_dir).expanduser().resolve() / rel_from_vaults_root)
        except Exception:
            pass

    return {
        "ok": True,
        "vault": name,
        "slug": slug,
        "file_path": path_str,
        "frontmatter": meta,
        "content": body,
        "backlinks": backlinks,
    }


# ─── vault management (v0.6.10+) ─────────────────────────────────
# stats / rename / delete — 운영자가 vault 단위로 관리할 수 있는 API.

@app.get("/api/vaults/{name}/stats")
def vault_stats(name: str):
    """Return content + index stats for a vault.

    Used by the Dashboard vault manager to show "12 pages / 5 broken
    links / 84 KB" before destructive ops (rename/delete).
    """
    v = _vault_or_404(name)
    pages = list(v.content_root.rglob("*.md")) if v.content_root.exists() else []
    size_bytes = sum(p.stat().st_size for p in pages)
    log_path = v.root / "log.md"
    log_entries = 0
    if log_path.exists():
        log_entries = sum(
            1 for line in log_path.read_text().splitlines() if line.startswith("## [")
        )
    # broken wikilink count via existing CLI recipe (single source of truth)
    broken = 0
    try:
        from raven.core import link as _link
        broken = len(_link.find_broken(v))
    except Exception:
        pass  # don't fail stats on link audit errors
    return {
        "ok": True,
        "vault": name,
        "pages": len(pages),
        "size_bytes": size_bytes,
        "log_entries": log_entries,
        "broken_links": broken,
    }


class VaultRename(BaseModel):
    name: str = Field(..., description="new vault name (lowercase kebab-case 권장)")


@app.put("/api/vaults/{name}")
def rename_vault(name: str, payload: VaultRename):
    """Rename a vault. The directory on disk is renamed too (matches CLI).

    Registry default stays valid: if the renamed vault was default, the new
    name becomes default automatically.
    """
    reg = registry()
    v = _vault_or_404(name)
    new_name = payload.name.strip()
    if not new_name or new_name == name:
        raise HTTPException(status_code=400, detail=f"invalid new name: {new_name!r}")
    if reg.get(new_name):
        raise HTTPException(status_code=409, detail=f"vault {new_name!r} already exists")

    old_root = v.root
    new_root = old_root.parent / new_name

    # 1. rename directory on disk
    try:
        old_root.rename(new_root)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"rename failed: {e}")

    # 2. update registry
    was_default = reg._data.get("default") == name
    reg.remove(name)
    from raven.core.registry import VaultMeta as _VM
    reg.add(_VM(name=new_name, path=new_root, mode=v.meta.mode, owner=v.meta.owner,
                created=v.meta.created, description=v.meta.description))
    if was_default:
        reg.set_default(new_name)

    return {"ok": True, "vault": {"old": name, "new": new_name, "path": str(new_root)}}


class VaultRepairPath(BaseModel):
    path: str = Field(
        ...,
        description=(
            "corrected path where the vault's files actually live, as resolvable "
            "by THIS API process — e.g. under WIKI_VAULTS_DIR (/vaults/<name>) "
            "when running via the Docker image, not the host-facing display path "
            "shown in `.vault.json` or the dashboard."
        ),
    )


@app.post("/api/vaults/{name}/repair")
def repair_vault_path(name: str, payload: VaultRepairPath):
    """Fix a vault's registered path without touching any files.

    Use when `.registry.json` points at a path that doesn't resolve in the
    current runtime (e.g. after a host/container path mismatch). This is
    registry-only — it never moves, copies, or deletes vault data, so it's
    safe to run even when the currently-registered path is unreachable
    (unlike rename, which requires the vault to already load).

    `payload.path` must be resolvable by this process (same convention as
    `vault register`/`vault clone`) — when running via Docker, that means
    the container-internal path under WIKI_VAULTS_DIR, not the host path.
    """
    reg = registry()
    if reg.get(name) is None:
        raise HTTPException(status_code=404, detail=f"vault {name!r} not found")

    new_path = Path(payload.path).expanduser().resolve()
    if not new_path.is_dir():
        raise HTTPException(status_code=400, detail=f"not a directory: {new_path}")
    if not (new_path / ".vault.json").exists():
        raise HTTPException(status_code=400, detail=f"not a vault (missing .vault.json): {new_path}")

    reg.update_path(name, new_path)
    return {"ok": True, "vault": name, "path": str(new_path)}


class CrosslinkRequest(BaseModel):
    slug: str = Field(
        ...,
        description=(
            "slug to resolve. Looks up across ALL registered vaults when not "
            "present in the originating vault. Read-only — never mutates any "
            "vault data. v0.7.37+."
        ),
    )


@app.post("/api/crosslink/{name}")
def crosslink_resolve(name: str, payload: CrosslinkRequest):
    """v0.7.37+: federated wikilink resolution across vaults (read-only).

    Returns:
        `{ok: True, found_in: "<other-vault-name>", title: "...", slug: "..."}`
        when the slug exists in another vault. When the originating vault
        `name` is omitted or the slug exists in that vault, this returns
        `{ok: True, found_in: "self", vault: name, slug: payload.slug}` so
        the dashboard can short-circuit.

        `{ok: False, not_found: True}` when no vault has the slug.

    Policy:
        * Origin vault is tried FIRST (exact + rglob fallback for legacy
          slugs).
        * Then every other registered vault in deterministic order
          (registry.json key order).
        * If EXACTLY ONE other vault holds the slug → return it.
        * If MULTIPLE other vaults hold the same slug → return a
          disambiguation list (`{candidates: [...]}`) so the dashboard
          can prompt the user (no silent pick).
        * Read-only by design — writes are scoped to the originating
          vault by `write_allowed_for()` (see `contracts.write_page`).

    This is the read-side counterpart to v0.7.37+'s `agents` write
    allowlist policy — together they let each vault keep its domain
    while remaining discoverable from any other.
    """
    reg = registry()
    # Normalize slug (e.g. "shared" → "content/shared") so short names
    # resolve under the content/ tree the way raven convention dictates.
    norm_slug = slug_module.normalize_prefix(payload.slug)

    # 1) Try the originating vault first.
    origin = reg.get(name)
    if origin is not None:
        try:
            vp = _vault_or_404(name)
        except HTTPException:
            vp = None
        if vp is not None:
            try:
                fp = _safe_slug_or_400(norm_slug, vp).with_suffix(".md")
                if fp.exists():
                    text = fp.read_text()
                    meta, _body = _split_fm(text)
                    return {
                        "ok": True,
                        "found_in": "self",
                        "vault": name,
                        "slug": norm_slug,
                        "title": meta.get("title", norm_slug),
                    }
            except HTTPException:
                # invalid slug in origin → still try others
                pass

    # 2) Federation — walk other registered vaults in deterministic order.
    candidates: list[dict] = []
    for other_meta in reg.list():
        if other_meta.name == name:
            continue
        if not other_meta.path.exists():
            continue
        try:
            other_vp = Vault.load(other_meta)
            fp = _safe_slug_or_400(norm_slug, other_vp).with_suffix(".md")
            if fp.exists():
                text = fp.read_text()
                meta, _body = _split_fm(text)
                candidates.append({
                    "vault": other_meta.name,
                    "slug": norm_slug,
                    "title": meta.get("title", norm_slug),
                })
        except (HTTPException, Exception):
            # Failed to load other vault (corrupt, missing, bad slug) →
            # skip silently. Federated lookup is best-effort.
            continue

    if len(candidates) == 1:
        c = candidates[0]
        return {
            "ok": True,
            "found_in": c["vault"],
            "slug": c["slug"],
            "title": c["title"],
        }
    if len(candidates) > 1:
        return {
            "ok": True,
            "found_in": "ambiguous",
            "candidates": candidates,
        }
    return {"ok": False, "not_found": True, "slug": norm_slug}


@app.delete("/api/vaults/{name}")
def delete_vault(name: str, force: bool = False):
    """Delete (unregister) a vault.

    Default behavior (force=False):
        - refuses if the vault contains any .md files (protects user data)
        - unregisters only — directory on disk is left intact

    force=True:
        - removes the entire directory recursively (DESTRUCTIVE)
        - use with care
    """
    import shutil
    meta = registry().get(name)
    if not meta:
        raise HTTPException(status_code=404, detail=f"vault {name!r} not found")

    # 만약 디스크에서 디렉토리가 이미 유실되었다면, 바로 등록 해제 처리
    if not meta.path.exists():
        was_default = registry()._data.get("default") == name
        registry().remove(name)
        if was_default:
            remaining = list(registry()._data.get("vaults", {}).keys())
            if remaining:
                registry().set_default(remaining[0])
        return {"ok": True, "vault": name, "destructive": force, "note": "directory already missing"}

    v = Vault.load(meta)
    pages = list(v.content_root.rglob("*.md")) if v.content_root.exists() else []
    log_path = v.root / "log.md"
    has_log = log_path.exists() and log_path.stat().st_size > 0

    if (pages or has_log) and not force:
        return {
            "ok": False,
            "vault": name,
            "reason": "vault contains content",
            "stats": {
                "pages": len(pages),
                "log_present": has_log,
            },
            "hint": "retry with ?force=true to delete the directory",
        }

    # destructive path
    if force:
        try:
            shutil.rmtree(v.root)
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"rmtree failed: {e}")

    # always unregister (even non-destructive unregister)
    was_default = registry()._data.get("default") == name
    registry().remove(name)
    if was_default:
        # pick another vault as default if any
        remaining = list(registry()._data.get("vaults", {}).keys())
        if remaining:
            registry().set_default(remaining[0])

    return {"ok": True, "vault": name, "destructive": force}


@app.post("/api/vaults/{name}/pages")
def create_page(name: str, payload: PageCreate):
    """Create a new page.

    Slug handling (v0.3+):
        - Invalid slugs (.., ~, absolute, NUL, ':') rejected with HTTP 400.
        - 'foo' (no '/') is auto-prefixed to 'content/foo' (matches CLI).

    v0.6.2+:
        - Delegates to `raven.core.contracts.write_page` (shared recipe).
        - HTTPException types preserved for the FastAPI boundary.
    """
    v = _vault_or_404(name)
    result = contracts.write_page(
        v,
        payload.slug,
        f"# {payload.title}\n{payload.content}".rstrip() + "\n",
        title=payload.title,
        type=payload.type,
        tags=payload.tags,
        overwrite=False,  # create-only: 409 on exists (matches pre-v0.6.2)
        enforce_protected_paths=True,
    )
    if not result.ok:
        if result.error == "exists":
            raise HTTPException(status_code=409, detail=f"page {result.slug!r} already exists")
        if result.error == "permission_denied":
            raise HTTPException(status_code=403, detail=result.message or result.error)
        # Slug validation error → 400
        raise HTTPException(status_code=400, detail=result.error)
    return {"ok": True, "vault": name, "slug": result.slug}


@app.put("/api/vaults/{name}/pages/{slug:path}")
def update_page(name: str, slug: str, payload: PageUpdate):
    """Update an existing page.

    Slug is validated (v0.3+). 'created' is preserved from existing frontmatter
    (v0.3+ — matches Agent and CLI behavior).

    v0.6.2+:
        - Delegates to `raven.core.contracts.write_page` (shared recipe).
    """
    v = _vault_or_404(name)
    # First validate slug via the original safe_slug helper — preserves
    # the pre-v0.6.2 400-on-bad-slug semantics at the API boundary.
    _safe_slug_or_400(slug, v)
    # Existence check for update-only 404 semantics.
    try:
        normalized = slug_module.normalize_prefix(slug)
        safe_path = slug_module.validate(normalized, vault_root=v.root)
        if not safe_path.with_suffix(".md").exists():
            raise HTTPException(status_code=404, detail=f"page {slug!r} not found")
    except slug_module.SlugError:
        # Already validated above; this means normalize/validate drift
        # — let contracts.report it.
        pass
    result = contracts.write_page(
        v,
        slug,
        payload.content.rstrip() + "\n",
        title=payload.title,
        type=payload.type,
        tags=payload.tags,
        overwrite=True,
        enforce_protected_paths=True,
    )
    if not result.ok:
        if result.error == "permission_denied":
            raise HTTPException(status_code=403, detail=result.message or result.error)
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "ok": True,
        "vault": name,
        "slug": result.slug,
        "created": result.created_date,
    }


@app.delete("/api/vaults/{name}/pages/{slug:path}")
def delete_page(name: str, slug: str):
    """Archive page (moves to _archive/<original-path>-<timestamp>.md).

    Slug validated (v0.3+). Archive path mirrors original (preserves nesting).

    v0.7.67 (평가 B#2): routes through core.archive.archive_page — the same
    recipe CLI and MCP now use, instead of a third inline copy.
    """
    v = _vault_or_404(name)
    safe_path = _safe_slug_or_400(slug, v)
    if not safe_path.with_suffix(".md").exists():
        raise HTTPException(status_code=404, detail=f"page {slug!r} not found")
    result = archive_module.archive_page(v, slug)
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.error)
    return {"ok": True, "vault": name, "slug": slug, "archived_to": result.archived_to}


class VaultClone(BaseModel):
    src: str = Field(..., description="source vault name")
    name: str = Field(..., description="new vault name")
    path: str = Field(..., description="absolute path for new vault directory")
    mode: Optional[str] = Field(None, description="override mode (default: copy from src)")
    owner: Optional[str] = Field(None, description="override owner (default: copy from src)")
    copy_meta: bool = Field(True, description="copy _meta/ from src")


@app.post("/api/vaults/clone")
def clone_vault(payload: VaultClone):
    """Clone an existing vault (content + _meta) to a new vault.

    Skips _archive/ and wiki.db. The new vault is registered automatically.
    """
    src_meta = registry().get(payload.src)
    if src_meta is None:
        raise HTTPException(status_code=404, detail=f"source vault {payload.src!r} not found")
    if registry().get(payload.name) is not None:
        raise HTTPException(status_code=409, detail=f"name {payload.name!r} already registered")
    src_v = Vault.load(src_meta)
    try:
        new_v = Vault.clone(
            src=src_v,
            name=payload.name,
            path=Path(payload.path).expanduser(),
            mode=payload.mode,
            owner=payload.owner,
            copy_meta=payload.copy_meta,
        )
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "ok": True,
        "vault": {
            "name": new_v.meta.name,
            "path": str(new_v.root),
            "mode": new_v.meta.mode,
            "owner": new_v.meta.owner,
            "src": payload.src,
            "copy_meta": payload.copy_meta,
        },
    }


# ────────────────────────── archive endpoints ──────────────────────────


@app.get("/api/vaults/{name}/archive")
def list_archive(name: str, older_than: int = Query(0, description="only show entries older than N days (0=all)")):
    """List all archived files in the vault."""
    v = _vault_or_404(name)
    entries = archive_module.list_archived(v)
    if older_than > 0:
        entries = [e for e in entries if e.age_days is not None and e.age_days > older_than]
    return {
        "ok": True,
        "vault": name,
        "count": len(entries),
        "entries": [e.to_dict() for e in entries],
    }


@app.post("/api/vaults/{name}/archive/clean")
def clean_archive(
    name: str,
    older_than: int = Query(30, description="delete entries older than N days (0=all)"),
    apply: bool = Query(False, description="actually delete (default: dry-run)"),
):
    """Delete old archived files. Dry-run by default."""
    v = _vault_or_404(name)
    result = archive_module.clean_archived(v, older_than_days=older_than, apply=apply)
    return result.to_dict() | {"vault": name}


@app.post("/api/vaults/{name}/archive/restore")
def restore_archive(name: str, archive_path: str = Query(..., description="vault-relative path, e.g. _archive/content/foo-20260625-123456.md")):
    """Restore an archived file to its original slug location."""
    v = _vault_or_404(name)
    result = archive_module.restore_archived(v, archive_path)
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "ok": True,
        "vault": name,
        "original_slug": result.original_slug,
        "restored_to": result.restored_to,
    }


# ────────────────────────── query endpoints ──────────────────────────


@app.get("/api/vaults/{name}/search")
def search(name: str, q: str = Query(..., min_length=1), top_k: int = 10):
    v = _vault_or_404(name)
    # reuse agent's lightweight search via direct walk
    import re as _re
    import html as _html
    terms = [t.lower() for t in _re.findall(r"\w+", q) if t]
    if not terms:
        return {"ok": True, "vault": name, "results": []}

    def _make_snippet(body_text: str, terms: list[str], width: int = 200) -> str:
        """First matching window of width chars centered on the first term hit,
        with <mark> wrapping literal matches (XSS-safe: html-escaped first)."""
        lower = body_text.lower()
        for term in terms:
            idx = lower.find(term)
            if idx < 0:
                continue
            start = max(0, idx - width // 2)
            end = min(len(body_text), idx + width // 2)
            snippet = body_text[start:end].replace("\n", " ").strip()
            # XSS escape first, then apply <mark> to literal term occurrences
            snippet = _html.escape(snippet)
            # Re-apply <mark> around case-insensitive matches (longest first
            # so e.g. "machine" matches before "mach").
            for t in sorted(set(terms), key=len, reverse=True):
                pat = _re.compile(_re.escape(t), _re.IGNORECASE)
                snippet = pat.sub(lambda m: f"<mark>{m.group(0)}</mark>", snippet)
            if start > 0:
                snippet = "…" + snippet
            if end < len(body_text):
                snippet = snippet + "…"
            return snippet
        # No match in body (only frontmatter maybe) → first 200 chars
        snippet = _html.escape(body_text[:width].replace("\n", " ").strip())
        return (snippet + "…") if len(body_text) > width else snippet

    scores = []
    for fp in v.content_root.rglob("*.md"):
        slug = str(fp.relative_to(v.root))[:-3]
        # v0.7.66 (평가 P1#8): 자동 생성 카탈로그(index.md, _index/*)는 모든
        # 페이지의 제목·요약을 복제해 어떤 검색어든 실제 노트를 밀어냈음 —
        # 탐색(tree/graph)용이지 검색 대상이 아님.
        if slug == "content/index" or slug.startswith("content/_index/"):
            continue
        full_text = fp.read_text(errors="replace")
        text = full_text.lower()
        meta, body = _split_fm(full_text)
        score = sum(text.count(t) for t in terms)
        if score > 0:
            snippet = _make_snippet(body, terms)
            scores.append((score, {
                "slug": slug,
                "title": meta.get("title", slug),
                "type": meta.get("type", "?"),
                "score": score,
                "snippet": snippet,
            }))
    scores.sort(key=lambda x: x[0], reverse=True)
    return {"ok": True, "vault": name, "query": q, "results": [s for _, s in scores[:top_k]]}


@app.get("/api/vaults/{name}/link-check")
def link_check(name: str, slug: Optional[str] = None):
    v = _vault_or_404(name)
    return {
        "ok": True,
        "vault": name,
        "broken": link_module.find_broken(v, slug=slug),
        "missing": link_module.find_missing(v, slug=slug),
    }


@app.post("/api/vaults/{name}/build")
def build(name: str):
    """v0.7.67 (평가 B#8): build_db()가 이미 내부에서 lint를 실행해 결과를
    `result["lint"]`에 담아 반환한다 — 이 엔드포인트가 그 결과를 버리고
    legacy `run_lint()`(subprocess lint + run_all 재실행)를 또 호출해,
    빌드 1회에 lint가 2~3회 도는 낭비가 있었다. build_db의 결과를 그대로 쓴다.
    """
    v = _vault_or_404(name)
    result = db_module.build_db(v)
    lr = result.get("lint") or {}
    return {
        "ok": result.get("ok", False) and lr.get("ok", False),
        "build": result,
        "lint": lr,
    }


@app.post("/api/vaults/{name}/export")
def export(name: str, out_dir: Optional[str] = None):
    v = _vault_or_404(name)
    target = Path(out_dir) if out_dir else None
    result = export_module.export_static(v, out_dir=target)
    return {"ok": result.get("ok", False), "export": result}


# ────────────────────────── log endpoints (v0.5.0+) ──────────────────────────


@app.get("/api/vaults/{name}/log")
def get_log(
    name: str,
    tail: Optional[int] = Query(None, description="최근 N개만"),
    action: Optional[str] = Query(None, description="액션 필터"),
    raw: bool = Query(False, description="raw log.md 전체 텍스트 반환"),
):
    """log.md 작업 이력 조회."""
    v = _vault_or_404(name)
    if raw:
        path = log_module.log_path(v)
        content = ""
        if path.exists():
            content = path.read_text(errors="replace")
        return {
            "ok": True,
            "vault": name,
            "raw": content,
        }
    entries = log_module.list_entries(v, tail=tail, action=action)
    total = log_module.count(v)
    return {
        "ok": True,
        "vault": name,
        "total": total,
        "shown": len(entries),
        "entries": entries,
    }


@app.get("/api/vaults/{name}/log/status")
def get_log_status(name: str):
    """log.md 상태 (entries 수, last entry, rotation 필요)."""
    v = _vault_or_404(name)
    path = log_module.log_path(v)
    total = log_module.count(v)
    entries = log_module.list_entries(v, tail=1)
    last = entries[0] if entries else None
    return {
        "ok": True,
        "vault": name,
        "log_path": str(path),
        "exists": path.exists(),
        "total_entries": total,
        "last_entry": last,
        "needs_rotate": total >= 500,
        "rotate_threshold": 500,
    }


@app.post("/api/vaults/{name}/log")
def post_log(name: str, payload: LogAppend):
    """log.md에 새 entry 추가 (수동)."""
    v = _vault_or_404(name)
    try:
        entry = log_module.append(
            v,
            action=payload.action,
            subject=payload.subject,
            files=payload.files or None,
            note=payload.note,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "ok": True,
        "vault": name,
        "entry": {
            "date": entry.date,
            "action": entry.action,
            "subject": entry.subject,
            "details": entry.details,
        },
    }


@app.post("/api/vaults/{name}/log/rotate")
def post_log_rotate(name: str, year: Optional[int] = None, force: bool = False):
    """log.md rotate (500 entries 초과 시).

    v0.7.67 (평가 A#7): 이 함수 본문이 docstring뿐이라 항상 null을 반환하고
    아무것도 하지 않았다 — 실제 구현은 아래 `post_debug_log`의 `return` 문
    뒤에 죽은 코드로 잘못 붙어 있었다 (2650줄 server.py를 편집하다 블록이
    엉뚱한 함수 밑에 삽입된 사고). 원래 구현을 여기로 되돌린다.
    """
    v = _vault_or_404(name)
    total = log_module.count(v)
    if total < 500 and not force:
        return {
            "ok": False,
            "error": f"{total} entries (500 미만) — 강제 rotate는 ?force=true",
            "current": total,
        }
    target = log_module.rotate(v, year=year)
    return {
        "ok": True,
        "vault": name,
        "rotated_to": str(target),
        "preserved_entries": total,
    }


# ─── /api/debug-log (v0.6.10+, 개발 단계 throw/error catch) ───────
# Dashboard 브라우저에서 fetch throw / window.onerror / unhandledrejection
# 등을 POST하면 서버가 tmp/dashboard.log에 append. mobile DevTools 못 볼 때
# 사용자가 `cat tmp/dashboard.log`로 직접 진단 가능.
class DebugLogEntry(BaseModel):
    level: str = Field("info", description="info | warn | error")
    source: str = Field("", description="dashboard | unhandledrejection | fetch | component")
    message: str = Field(..., description="에러 메시지 또는 진단 라인")
    stack: str = Field("", description="스택 트레이스 (선택)")
    url: str = Field("", description="window.location.href (선택)")
    vault: str = Field("", description="active vault (선택)")


_DEBUG_LOG_PATH = Path(__file__).resolve().parent.parent.parent / "tmp" / "dashboard.log"


@app.post("/api/debug-log")
def post_debug_log(entry: DebugLogEntry):
    """Dashboard throw / error를 tmp/dashboard.log에 append. dev only."""
    try:
        _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {entry.level.upper():5s} {entry.source:20s} vault={entry.vault or '-':12s} url={entry.url or '-'}\n"
        line += f"  msg: {entry.message}\n"
        if entry.stack:
            for sl in entry.stack.splitlines()[:10]:
                line += f"  at:  {sl}\n"
        line += "\n"
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "path": str(_DEBUG_LOG_PATH)}


# ────────────────────────── garden endpoint (v0.7.27) ──────────────────────────


@app.get("/api/vaults/{name}/garden")
def get_garden(name: str):
    """지식 정원(Gardening) 데이터 (Stale & Orphan 문서) 조회."""
    v = _vault_or_404(name)
    from raven.core import garden as garden_module

    # 1. Stale Pages (90일+ 미갱신)
    stale_raw = garden_module.get_stale_pages(v)
    stale_list = []
    for item in stale_raw:
        stale_list.append({
            "slug": item["slug"],
            "updated": item["updated"],
            "age_days": item["age_days"],
        })

    # 2. Orphan Pages & Link Candidates
    orphan_raw = garden_module.get_orphan_pages(v)
    orphan_list = []
    for item in orphan_raw:
        # FTS 기반 링크 추천 후보 추출
        candidates = garden_module.find_link_candidates(v, item["slug"])
        orphan_list.append({
            "slug": item["slug"],
            "title": item["title"],
            "type": item["type"],
            "link_candidates": candidates,  # list of slugs
        })

    return {
        "ok": True,
        "vault": name,
        "stale": stale_list,
        "orphan": orphan_list,
    }


# ────────────────────────── lint endpoints (v0.5.1+) ──────────────────────────


@app.get("/api/vaults/{name}/lint")
def get_lint(
    name: str,
    check: Optional[str] = Query(None, description="특정 check id (#1-#12)"),
    severity: Optional[str] = Query(None, description="critical|warning|info"),
    write_log: bool = Query(False, description="log.md에 lint entry 자동 append"),
):
    """lint 12개 (카파시 가이드) 실행."""
    v = _vault_or_404(name)
    result = lint_module.run_all(v)
    issues = result["issues"]
    if check:
        issues = [i for i in issues if i.get("id") == check]
    if severity:
        issues = [i for i in issues if i.get("severity") == severity]
    if write_log:
        try:
            c = result["counts"]
            log_module.append(
                v,
                action="lint",
                subject=f"lint 12개 ({c['critical']}C/{c['warning']}W/{c['info']}I)",
                extra={"by_check": json.dumps(result["by_check"], ensure_ascii=False)},
            )
        except Exception:
            pass
    return {
        "ok": result["ok"],
        "vault": name,
        "counts": result["counts"],
        "by_check": result["by_check"],
        "issues": issues,
    }


@app.get("/api/vaults/{name}/lint/summary")
def get_lint_summary(name: str):
    """12개 check별 통계 (빠른 헬스체크)."""
    v = _vault_or_404(name)
    result = lint_module.run_all(v)
    return {
        "ok": result["ok"],
        "vault": name,
        "counts": result["counts"],
        "by_check": result["by_check"],
    }


# ────────────────────────── digest (v0.5.6, M5 F5) ──────────────────────────


@app.get("/api/vaults/{name}/digest")
def get_digest(name: str, days: int = Query(7, ge=1, le=30, description="this_week 윈도우 (1–30)")):
    """Dashboard digest — 사람 운영자 진입 시 '오늘 vault 상태' 한 화면 요약.

    Returns: compute_digest() payload — today / this_week / lint / log_recent / stats.
    """
    v = _vault_or_404(name)
    payload = digest_module.compute_digest(v, days=days)
    return {"ok": True, **payload}


# ────────────────────────── advisory locks (M5 F4) ──────────────────────────
#
# Read-only advisory lock view for the Dashboard. Mirrors mcp.tools.check_lock
# exactly so the Dashboard and the MCP write tools see the same state. We do
# NOT add POST endpoints here — F4 is "advisory" and claim/release flow is
# the caller's job (typically via the MCP transport). Exposing GET only keeps
# this endpoint truly read-only and safe for the Dashboard to poll.


@app.get("/api/vaults/{name}/locks")
def list_locks(name: str, slug: Optional[str] = Query(None, description="specific slug to inspect")):
    """Advisory lock state for a vault (M5 F4).

    With ``slug``: returns the lock record (or ``{"holder": None}``) for
    that slug, same shape ``mcp.tools.check_lock`` returns.

    Without ``slug``: returns all currently active lock entries. Expired
    entries are filtered out (the underlying store does its own GC on
    read).
    """
    v = _vault_or_404(name)
    # Import lazily so server.py doesn't take a hard dependency on mcp.tools
    # at import time (the API server runs in processes that may not have
    # mcp installable, e.g. slim prod containers).
    from raven.mcp.tools import check_lock, _load_locks_store, _is_expired

    if slug:
        holder = check_lock(v.root, slug)
        return {
            "ok": True,
            "vault": name,
            "slug": slug,
            "holder": holder,
        }

    store = _load_locks_store(v.root)
    active = {
        s: entry for s, entry in store.items()
        if not _is_expired(entry)
    }
    return {
        "ok": True,
        "vault": name,
        "count": len(active),
        "locks": active,
    }


@app.delete("/api/vaults/{name}/locks")
def release_lock(name: str, slug: str = Query(..., description="specific slug to release lock for")):
    """Force release (unlock) an advisory lock for a specific slug (v0.7.28)."""
    v = _vault_or_404(name)
    from raven.mcp.tools import _load_locks_store, _save_locks_store

    store = _load_locks_store(v.root)
    if slug in store:
        store.pop(slug)
        persisted = _save_locks_store(v.root, store)
        return {"ok": persisted, "released": slug}
    return {"ok": True, "released": slug, "note": "lock not found"}


# ────────────────────────── raw/ folder endpoints (v0.7.50+, ADR-2026-07-02) ──────────────────────────
#
# 사람 1차 운영 영역. 에이전트는 MCP wiki_read로만 read. wiki_ingest는
# 사람 명시 호출 시에만. 5번째 진입점이 아닌 기존 HTTP API의 확장.
# 패턴: list_pages / create_folder 와 동일 (slug_module.validate + HTTPException 4xx).


class RawItem(BaseModel):
    path: str = Field(..., description="vault-relative path under raw/, e.g. 'raw/articles/foo.md'")


class RawContent(BaseModel):
    content: str = Field(..., description="raw/ 파일 전체 본문 (utf-8)")


def _raw_root_or_400(v: Vault) -> Path:
    """Return <vault>/raw. 없으면 404."""
    raw_root = v.root / "raw"
    if not raw_root.exists():
        raise HTTPException(status_code=404, detail=f"raw/ folder not found in vault {v.meta.name!r}")
    return raw_root


def _safe_raw_path_or_400(rel: str, raw_root: Path) -> Path:
    """`rel` (raw/ 하위 경로, 예: 'articles/foo.md')가 raw_root 내부인지 검증 후 절대 경로 반환.

    FastAPI 라우트 `/raw/{path:path}`는 path 파라미터에 raw_root relative 경로만 받음.
    → client는 'raw/articles/foo.md' 가 아니라 'articles/foo.md' 만 보냄.
    또한 FastAPI는 `..`을 자동 normalize하므로 'articles/../escape.md' → 'escape.md'로
    매핑될 수 있음. defense-in-depth로 명시적 거부 + raw_root 내부 확인 둘 다 적용.

    가드:
      1) 명시적 `..` segment 거부 (FastAPI normalize 우회 방지)
      2) slug_module.validate (절대/.. / NUL 차단)
      3) defense-in-depth: resolved path가 raw_root 내부인지 확인
    """
    s = rel.strip().replace("\\", "/").lstrip("/")
    if not s:
        raise HTTPException(status_code=400, detail="raw path is empty")
    # 1) 명시적 .. segment 차단 (FastAPI path normalization이 ..을 흡수하기 전에 거부)
    parts = s.split("/")
    if ".." in parts or any(p == "" for p in parts if p == ""):
        # 빈 segment만 차단 (예: 'foo//bar' → 'foo/bar' 정규화는 slug_module이 처리)
        # '..' 만 명시 거부
        if ".." in parts:
            raise HTTPException(status_code=400, detail=f"raw path contains '..': {rel!r}")
    # 2) slug_module로 안전 검증 (페이지 slug와 동일 가드). raw_root.parent는 vault root.
    try:
        validated = slug_module.validate(f"raw/{s}", vault_root=raw_root.parent)
    except slug_module.SlugError as e:
        raise HTTPException(status_code=400, detail=f"invalid raw path: {e}")
    # 3) defense-in-depth: resolved가 raw_root 내부
    try:
        validated_resolved = validated.resolve()
        raw_resolved = raw_root.resolve()
        validated_resolved.relative_to(raw_resolved)
    except (ValueError, OSError):
        raise HTTPException(status_code=400, detail=f"raw path escapes raw/ root: {rel!r}")
    return validated


@app.get("/api/vaults/{name}/raw")
def list_raw(name: str):
    """raw/ 트리 + 메타 (Dashboard `/raw` panel + Sidebar raw/ 노드용).

    - 빈 폴더도 포함 (P32: OS directory = first-class).
    - 응답: {
        ok, vault, root: 'raw',
        items: [{path, name, type: 'file'|'dir', size, modified, kind: 'raw'}]
      }
    """
    v = _vault_or_404(name)
    raw_root = _raw_root_or_400(v)
    items: list[dict] = []
    for fp in raw_root.rglob("*"):
        rel = fp.relative_to(v.root)
        rel_str = str(rel).replace("\\", "/")
        if fp.is_dir():
            items.append({
                "path": rel_str,
                "name": fp.name,
                "type": "dir",
                "kind": "raw",
            })
        else:
            try:
                stat = fp.stat()
                size = stat.st_size
                modified = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
            except OSError:
                size = None
                modified = None
            items.append({
                "path": rel_str,
                "name": fp.name,
                "type": "file",
                "kind": "raw",
                "size": size,
                "modified": modified,
            })
    # 정렬: dir 먼저, 그 다음 파일, 알파벳
    items.sort(key=lambda it: (it["type"] != "dir", it["path"]))
    return {"ok": True, "vault": name, "root": "raw", "items": items}


@app.get("/api/vaults/{name}/raw/{path:path}")
def read_raw(name: str, path: str):
    """raw/<rel> 파일 내용 조회. 사람은 read-only viewer, 에이전트는 wiki_read."""
    v = _vault_or_404(name)
    raw_root = _raw_root_or_400(v)
    fp = _safe_raw_path_or_400(path, raw_root)
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"raw file not found: {path!r}")
    if fp.is_dir():
        raise HTTPException(status_code=400, detail=f"raw path is a directory, not a file: {path!r}")
    try:
        content = fp.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"failed to read raw file: {e}")
    try:
        stat = fp.stat()
        size = stat.st_size
        modified = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
    except OSError:
        size = None
        modified = None
    return {
        "ok": True,
        "vault": name,
        "path": str(fp.relative_to(v.root)).replace("\\", "/"),
        "content": content,
        "size": size,
        "modified": modified,
    }


@app.put("/api/vaults/{name}/raw/{path:path}")
def write_raw(name: str, path: str, payload: RawContent):
    """raw/<rel> 파일 작성/갱신. 사람 운영자 only. 에이전트 호출 ❌ (MCP는 wiki_ingest만).

    - payload.content = 전체 본문 (overwrite).
    - parent dir 없으면 자동 mkdir (P32: OS directory = first-class).
    - 기존 파일 있으면 overwrite (raw는 사람 1차, 의도적 갱신 OK).
    """
    v = _vault_or_404(name)
    raw_root = _raw_root_or_400(v)
    fp = _safe_raw_path_or_400(path, raw_root)
    if fp.is_dir():
        raise HTTPException(status_code=400, detail=f"raw path is a directory: {path!r}")
    # parent mkdir
    fp.parent.mkdir(parents=True, exist_ok=True)
    existed = fp.exists()
    try:
        fp.write_text(payload.content, encoding="utf-8")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"failed to write raw file: {e}")
    try:
        stat = fp.stat()
        size = stat.st_size
    except OSError:
        size = None
    return {
        "ok": True,
        "vault": name,
        "path": str(fp.relative_to(v.root)).replace("\\", "/"),
        "size": size,
        "existed": existed,
    }


@app.delete("/api/vaults/{name}/raw/{path:path}")
def delete_raw(name: str, path: str):
    """raw/<rel> 파일/빈 디렉토리 삭제. hard delete (raw는 immutable-to-LLM, 사람 의도적 삭제 OK).

    - 파일: hard delete (undo 없음, OS 파일관리자 복구 가능).
    - 빈 디렉토리만 삭제. 파일 있는 디렉토리는 409.
    """
    v = _vault_or_404(name)
    raw_root = _raw_root_or_400(v)
    fp = _safe_raw_path_or_400(path, raw_root)
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"raw path not found: {path!r}")
    if fp.is_dir():
        # 비어있는지 확인
        try:
            next(fp.iterdir())
            has_children = True
        except StopIteration:
            has_children = False
        if has_children:
            raise HTTPException(
                status_code=409,
                detail=f"raw/ dir not empty (recurse manually or delete children first): {path!r}",
            )
        try:
            fp.rmdir()
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"failed to rmdir: {e}")
    else:
        try:
            fp.unlink()
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"failed to unlink: {e}")
    return {
        "ok": True,
        "vault": name,
        "path": str(fp.relative_to(v.root)).replace("\\", "/"),
        "deleted": True,
    }


# ────────────────────────── local helpers ──────────────────────────


def _split_fm(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    try:
        _, fm, body = text.split("---", 2)
    except ValueError:
        return {}, text
    meta = {}
    for line in fm.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    return meta, body.strip("\n")
