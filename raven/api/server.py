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
from fastapi import FastAPI, HTTPException, Query, Header
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


# v0.7.114+ (ADR-2026-07-08): Lite bootstrap freshness 가드 미들웨어.
# vault 부속(SCHEMA.md / PROJECT-WORKFLOW.md)의 SHA256을 매 응답에 X-Guide-Hash로 echo.
# X-Guide-Hash 요청 헤더가 있으면 cache_hash로 파싱, mismatch 시 응답 body에
# `freshness_warning` 첨부 + log.md audit append. silent warn — 강제 read ❌.
# HTTP 전용 (stdio 미지원). MCP HTTP transport 와 REST API 동일 동작.
_FRESHNESS_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_FRESHNESS_USER_AGENT_LIKE_PREFIXES = ("agent", "mcp", "ai-")


def _resolve_request_vault(vault_name: Optional[str]) -> Optional[Vault]:
    """URL path의 vault 이름으로 Vault 객체 resolve. 실패 시 None."""
    if not vault_name:
        return None
    meta = registry().get(vault_name)
    if not meta:
        return None
    try:
        return Vault.load(meta)
    except Exception:
        return None


def _extract_vault_name_from_path(path: str) -> Optional[str]:
    """/api/vaults/{name}/... 형태에서 name 추출."""
    parts = path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "vaults":
        return parts[2]
    return None


@app.middleware("http")
async def freshness_middleware(request, call_next):
    """Lite bootstrap freshness 가드 — ADR-2026-07-08.

    Request 헤더 X-Guide-Hash: SCHEMA=abc,PROJECT-WORKFLOW=def
    → vault 부속 hash 재계산 후 mismatch 시 freshness_warning 첨부.

    Response 헤더 X-Guide-Hash: SCHEMA=...,PROJECT-WORKFLOW=...
    → agent가 다음 호출 시 cache_hash로 사용.
    """
    from raven.mcp.tools.guide import check_freshness

    cache_hash = request.headers.get("X-Guide-Hash")
    vault_name = _extract_vault_name_from_path(request.url.path)
    vault = _resolve_request_vault(vault_name) if vault_name else None

    response = await call_next(request)

    if vault is None:
        return response

    try:
        info = check_freshness(vault_root=vault.root, cache_hash=cache_hash)
    except Exception:
        # hash 계산 실패 시 silent skip (성능/안정성 우선)
        return response

    # 응답 헤더 echo (모든 응답에 — agent가 다음 호출 시 사용)
    from raven.mcp.tools.guide import _format_hash_for_header
    guides_for_header = {
        k: {"vault_hash": v.get("vault_hash") if isinstance(v, dict) else None}
        for k, v in info.get("guides", {}).items()
        if isinstance(v, dict)
    }
    formatted = _format_hash_for_header(guides_for_header)
    if formatted:
        response.headers["X-Guide-Hash"] = formatted

    # mismatch — write 도구일 때만 freshness_warning 첨부
    if info.get("stale") and request.method in _FRESHNESS_WRITE_METHODS:
        response.headers["X-Guide-Freshness-Warning"] = (
            "stale_guide: cache_hash != vault_hash. "
            + "Kinds=" + ",".join(info.get("stale_kinds", []))
        )

    return response


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
    is_docker = (str(runtime_root.resolve()) == "/vaults" or os.path.exists("/.dockerenv"))
    for v in registry().list():
        raw_meta = reg_data.get(v.name, {})
        display_path = raw_meta.get("path") if isinstance(raw_meta, dict) else None
        
        # v0.7.121+: 로컬 실행 시, .registry.json의 display_path가 존재하지 않는 엉뚱한 경로(타인 홈디렉토리 등)이고
        # fallback으로 실제 존재하는 경로 v.path가 구해진 경우, 안전하게 v.path를 display_path로 사용한다.
        if not is_docker and display_path:
            try:
                dp_path = Path(display_path).expanduser().resolve()
                if not dp_path.exists() and v.path.exists():
                    display_path = str(v.path)
            except Exception:
                pass

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


# v0.7.68 (평가 B#3): 순수 subprocess 래퍼를 raven.core.git으로 이동.
from raven.core.git import run_git as _run_git


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


@app.post("/api/vaults")
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


@app.post("/api/vaults/verify-all")
def verify_all_vaults_bootstrap():
    """Verify Lite bootstrap for every registered vault at once.

    v0.7.75+: Dashboard VaultManage 진입 시 자동 호출 — 사용자가 누르지 않아도
    모든 vault의 SCHEMA.md / PROJECT-WORKFLOW.md / log.md 일치 여부 검사.

    Returns per-vault result:
        results: [{name, ok, mismatched_files, missing_files, summary}, ...]
    Aggregate counts: ok_count, mismatch_count.

    Never raises on per-vault mismatch (409 forbidden here — caller renders
    a list view, not HTTP error). Errors per vault (corrupt vault, missing
    dir) are caught and returned as `{"name": ..., "ok": False, "error": ...}`.
    """
    results: list[dict] = []
    for meta in registry().list():
        entry: dict = {"name": meta.name, "ok": True}
        try:
            v = _vault_or_404(meta.name)
            r = v.verify_bootstrap()
            entry["ok"] = r.ok
            entry["mismatched_files"] = [
                c.rel_path for c in r.checks if c.status == "mismatch"
            ]
            entry["missing_files"] = [
                c.rel_path for c in r.checks if c.status == "missing"
            ]
            entry["empty_files"] = [
                c.rel_path for c in r.checks if c.status == "empty"
            ]
            entry["summary"] = (
                "ok" if r.ok
                else f"{len(entry['mismatched_files'])} mismatch, "
                     f"{len(entry['missing_files'])} missing"
            )
        except Exception as e:
            entry["ok"] = False
            entry["error"] = str(e)
            entry["summary"] = f"error: {e}"
        results.append(entry)

    ok_count = sum(1 for r in results if r.get("ok"))
    return {
        "ok": ok_count == len(results),
        "total": len(results),
        "ok_count": ok_count,
        "mismatch_count": len(results) - ok_count,
        "results": results,
    }


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


# v0.7.68 (평가 B#3): 그래프 레이아웃 알고리즘(~450줄)을 raven.core.graph로 이동.
# 순수 함수라 HTTP 핸들러 파일에 있을 이유가 없었다. 원래 이름으로 재노출해
# 기존 import(예: tests/test_api.py의 직접 import)를 그대로 유지한다.
from raven.core.graph import (
    normalize_layout as _normalize_layout,
    stable_unit as _stable_unit,
    louvain_communities as _louvain_communities,
    constellation_layout as _constellation_layout,
    forceatlas_layout as _forceatlas_layout,
)


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
    scope: Literal["current", "all"] = Query(
        "current",
        description="Graph scope. 'current' returns one vault; 'all' merges every registered vault.",
    ),
):
    """vault 페이지 + wikilink edges + graph layout 좌표를 반환.

    v0.6.10+: nodes[i].x, nodes[i].y = 서버 계산 graph layout 좌표.
    v0.7.6x+: layout은 atlas(ForceAtlas2/LinLog hybrid) 고정 — 다른 레이아웃은
        노드 위치가 실제 위키링크 구조와 무관해 허브 뭉침/레이어 크로우딩
        문제가 있어 제거함 (docs/architecture.md D10/D11 참고).
    v0.6.15+: ?community=modularity attaches nodes[i].community = Louvain-style
        community id (0..K-1). 'none' (default) skips the call.
    v0.7.122+: ?scope=all merges all registered vault graphs. In all scope,
        node ids and edge endpoints use `{vault}:{slug}` to prevent collisions.

    current nodes: [{id: slug, title, type, weight, x, y, community?}]
    all nodes: [{id: "{vault}:{slug}", vault, slug, title, type, weight, x, y, community?}]
    edges: [{source, target}]

    wiki.db의 links 테이블에서 source/target 직접 매칭 (정확성 우선).
    wiki.db가 없으면 (구 vault) rglob fallback.
    """
    _vault_or_404(name)
    if scope == "all":
        merged_nodes = []
        merged_edges = []
        included_vaults = 0
        for meta in registry().list():
            if not meta.path.exists():
                continue
            graph = vault_graph(meta.name, iterations=iterations, community=community, scope="current")
            included_vaults += 1
            for node in graph.get("nodes", []):
                slug = node.get("slug") or node.get("id")
                prefixed = dict(node)
                prefixed["id"] = f"{meta.name}:{slug}"
                prefixed["slug"] = slug
                prefixed["vault"] = meta.name
                merged_nodes.append(prefixed)
            for edge in graph.get("edges", []):
                merged_edges.append({
                    **edge,
                    "source": f"{meta.name}:{edge.get('source')}",
                    "target": f"{meta.name}:{edge.get('target')}",
                })
        return {
            "ok": True,
            "vault": name,
            "scope": "all",
            "nodes": merged_nodes,
            "edges": merged_edges,
            "stats": {"nodes": len(merged_nodes), "edges": len(merged_edges), "vaults": included_vaults},
        }

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
            reg_root = registry().root.resolve()
            host_path = Path(host_dir).expanduser().resolve()
            
            # v0.7.121+: Docker 환경이거나, 또는 로컬(호스트) 환경인데 host_path가 실제로 로컬에 존재할 때만 치환 적용.
            # 로컬 직접 실행 시 RAVEN_VAULTS_DIR이 타인 경로 등으로 잘못 하드코딩되어 있고 실제 존재하지도 않는다면 치환하지 않음.
            is_docker = (str(reg_root) == "/vaults" or os.path.exists("/.dockerenv"))
            if is_docker or host_path.exists():
                rel_from_vaults_root = fp.resolve().relative_to(reg_root)
                path_str = str(host_path / rel_from_vaults_root)
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
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "vault contains content",
                "stats": {
                    "pages": len(pages),
                    "log_present": has_log,
                },
                "hint": "retry with ?force=true to delete the directory",
            },
        )

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
            "link_candidates": candidates,  # list of {slug,title,reason,score} objects
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
    """lint 12개 (카파시 가이드) 실행.

    v0.7.117 (Fix D): lint_module.run_all() 자체가 예외로 raise되면 (예: 특정
    check가 RuntimeError/ValueError) 응답은 500으로 propagate되지 않고
    ok=False + empty counts로 graceful degrade. log fail = lint fail 분리.
    """
    v = _vault_or_404(name)
    try:
        result = lint_module.run_all(v)
    except Exception as exc:  # AGENTS.md §9: silent 버그 정책 — silent swallow ❌
        import sys
        sys.stderr.write(
            f"⚠️  lint run_all failed for vault {name!r}: "
            f"{type(exc).__name__}: {exc}\n"
        )
        result = {
            "ok": False,
            "counts": {"critical": 0, "warning": 0, "info": 0, "total": 0},
            "by_check": {},
            "issues": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
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
                extra={"by_check": result["by_check"]},
            )
        except Exception as exc:  # AGENTS.md §9: silent 버그 정책 — silent swallow ❌
            import sys
            sys.stderr.write(
                f"⚠️  lint write_log failed for vault {name!r}: "
                f"{type(exc).__name__}: {exc}\n"
            )
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


def _raw_write_allowed(actor: Optional[str]) -> bool:
    """raw/ 폴더는 사람 운영자만 (AGENTS.md §7). actor=None 또는 "anonymous" 거부.

    - actor가 명시적으로 식별된 경우 (Dashboard의 user actor, CLI의 user actor) → True
    - 그 외 (None / 빈 문자열 / "anonymous") → False
    - vault .vault.json의 agents allowlist (v0.7.37) 와는 별개 — raw/ 폴더는 vault allowlist
      와 무관하게 사람 운영자만 가능. 에이전트는 MCP wiki_ingest로만 (user_command=True 필수).

    정책 근거: AGENTS.md §7 raw/ 폴더 정책 v0.7.50+.
    """
    if not actor or not actor.strip():
        return False
    if actor.strip().lower() == "anonymous":
        return False
    return True


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


# v0.7.89+: Lite bootstrap 3종 read-only viewer (Dashboard /guides 페이지).
# 화이트리스트 외 경로는 403. SCHEMA/PROJECT-WORKFLOW는 vault create 시 Lite bootstrap으로
# 자동 주입되고 log.md는 빈 헤더로 시작 → 운영자가 "이 vault의 지침이 뭐지?"를 즉시 확인.
# v0.7.65+ AGENTS.md §4: 이 3종이 외부 에이전트에게 노출되는 유일한 Tier 2 표면.
_LITE_GUIDE_WHITELIST: dict[str, str] = {
    # kind (URL path)              → vault-relative filesystem path
    "_meta/agents/SCHEMA.md":          "_meta/agents/SCHEMA.md",
    "_meta/agents/PROJECT-WORKFLOW.md": "_meta/agents/PROJECT-WORKFLOW.md",
    "log.md":                            "log.md",
}


@app.get("/api/vaults/{name}/guide/{kind:path}")
def read_guide(name: str, kind: str) -> dict:
    """Lite bootstrap 3종 read-only viewer (Dashboard /guides).

    kind must be in _LITE_GUIDE_WHITELIST. 그 외 경로는 403.
    """
    v = _vault_or_404(name)
    # 화이트리스트 매칭 (kind 자체 또는 kind의 basename 모두 시도 — '/kind' vs 'kind' 호환).
    candidates = [kind, kind.lstrip("/"), kind.split("/")[-1] if "/" in kind else kind]
    rel_target: str | None = None
    for c in candidates:
        if c in _LITE_GUIDE_WHITELIST:
            rel_target = _LITE_GUIDE_WHITELIST[c]
            break
    if rel_target is None:
        raise HTTPException(
            status_code=403,
            detail=(
                f"guide kind {kind!r} is not in the Lite bootstrap whitelist. "
                f"Allowed: {sorted(_LITE_GUIDE_WHITELIST.keys())}"
            ),
        )
    fp = v.root / rel_target
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"guide file not present: {rel_target!r}")
    if fp.is_dir():
        raise HTTPException(status_code=400, detail=f"guide path is a directory: {rel_target!r}")
    try:
        content = fp.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"failed to read guide: {e}")
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
        "kind": rel_target,
        "content": content,
        "size": size,
        "modified": modified,
    }


# v0.7.94+: Lite bootstrap 3종 diff vs 템플릿.
# v0.7.89 read_guide와 동일한 화이트리스트 (Tier 1 leak 방지). Template은
# raven/core/templates/{agent/,log.md} (raven install source of truth).
# 운영자가 "내 vault의 SCHEMA가 왜 mismatch?" 즉시 진단 가능.
import difflib as _difflib

_LITE_TEMPLATE_MAP: dict[str, str] = {
    # kind (URL path, vault-relative)        → vault-relative filesystem path
    "_meta/agents/SCHEMA.md":          "_meta/agents/SCHEMA.md",
    "_meta/agents/PROJECT-WORKFLOW.md": "_meta/agents/PROJECT-WORKFLOW.md",
    "log.md":                            "log.md",
}

# v0.7.94+: 템플릿은 raven install source of truth (raven/core/templates/).
# 화이트 3종 (Lite bootstrap) 가 vault 에 주입될 때 사용된 원본.
_LITE_TEMPLATE_SRC: dict[str, str] = {
    # kind (URL path)                        → template-relative path
    "_meta/agents/SCHEMA.md":          "agent/SCHEMA.md",
    "_meta/agents/PROJECT-WORKFLOW.md": "agent/PROJECT-WORKFLOW.md",
    "log.md":                            "log.md",
}


@app.get("/api/vaults/{name}/guide-diff/{kind:path}")
def read_guide_diff(name: str, kind: str) -> dict:
    """Lite bootstrap 3종 unified diff (vault vs 템플릿).

    difflib 표준 라이브러리 (외부 의존성 0). 응답 shape:
        {
          ok, vault, kind,
          identical: bool,
          template_path: str,   # 비교 대상 (raven install 경로)
          diff_lines: [         # unified diff 라인 (None이면 동일)
            {tag: '+'/'-'/' '/'', content: str, old_lineno?, new_lineno?},
            ...
          ],
          stats: {added, removed, equal},
          truncated: bool       # 200줄 초과 시 압축
        }

    AGENTS.md §4 Lite bootstrap 정책: 3종은 운영자가 직접 편집 ❌. mismatch는
    Raven 버전 갱신 또는 `raven meta sync --lite`로 해결. 이 endpoint는 진단용.
    """
    v = _vault_or_404(name)
    candidates = [kind, kind.lstrip("/")]
    if "/" in kind:
        candidates.append(kind.split("/")[-1])
    rel_target: str | None = None
    template_src: str | None = None
    for c in candidates:
        if c in _LITE_TEMPLATE_MAP:
            rel_target = _LITE_TEMPLATE_MAP[c]
            template_src = _LITE_TEMPLATE_SRC[c]
            break
    if rel_target is None or template_src is None:
        raise HTTPException(
            status_code=403,
            detail=(
                f"guide kind {kind!r} is not in the Lite bootstrap whitelist. "
                f"Allowed: {sorted(_LITE_TEMPLATE_MAP.keys())}"
            ),
        )
    fp = v.root / rel_target
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"guide file not present: {rel_target!r}")

    # 템플릿 (raven install source of truth) 읽기
    from pathlib import Path as _Path
    template_root = _Path(__file__).resolve().parent.parent / "core" / "templates"
    template_fp = template_root / template_src
    if not template_fp.exists():
        raise HTTPException(
            status_code=500,
            detail=f"template file not found (raven install corruption?): {template_src!r}",
        )

    try:
        vault_text = fp.read_text(encoding="utf-8", errors="replace")
        template_text = template_fp.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"failed to read files: {e}")

    # 라인 단위 split + unified diff
    vault_lines = vault_text.splitlines(keepends=True)
    template_lines = template_text.splitlines(keepends=True)
    diff_iter = _difflib.unified_diff(
        template_lines, vault_lines,
        fromfile=f"template/{rel_target}",
        tofile=f"vault/{rel_target}",
        lineterm="",
    )
    raw_diff = list(diff_iter)
    identical = len(raw_diff) == 0

    # 200줄 압축 (대형 PROJECT-WORKFLOW.md 333줄 — diff 가독성)
    MAX_DIFF_LINES = 200
    truncated = len(raw_diff) > MAX_DIFF_LINES
    display_diff = raw_diff[:MAX_DIFF_LINES] if truncated else raw_diff

    # unified_diff 출력은 "--- file\n+++ file\n@@ ...\n" 헤더 + diff 라인.
    # Frontend 가독성 위해 라인별 구조화.
    diff_lines = []
    added = removed = equal = 0
    for line in display_diff:
        if line.startswith("---") or line.startswith("+++"):
            # 헤더 라인은 무시 (path만)
            continue
        if line.startswith("@@"):
            # hunk 헤더 (구간 정보) — 패스
            continue
        if line.startswith("+"):
            diff_lines.append({"tag": "+", "content": line[1:]})
            added += 1
        elif line.startswith("-"):
            diff_lines.append({"tag": "-", "content": line[1:]})
            removed += 1
        else:
            # ' ' (공백 prefix) — 동일 라인
            diff_lines.append({"tag": " ", "content": line[1:] if line.startswith(" ") else line})
            equal += 1

    return {
        "ok": True,
        "vault": name,
        "kind": rel_target,
        "identical": identical,
        "template_path": str(template_fp),
        "diff_lines": diff_lines if not identical else [],
        "stats": {
            "added": added if not identical else 0,
            "removed": removed if not identical else 0,
            "equal": equal if not identical else (len(vault_lines)),
        },
        "truncated": truncated,
        "truncation_note": (
            f"diff > {MAX_DIFF_LINES} lines — 상위 {MAX_DIFF_LINES}줄만 표시. "
            "전체 비교는 CLI `diff` 사용."
        ) if truncated else None,
    }


@app.put("/api/vaults/{name}/raw/{path:path}")
def write_raw(
    name: str,
    path: str,
    payload: RawContent,
    actor: Optional[str] = Header(None, alias="X-Actor", description="운영자 식별자. 사람 운영자만 허용 (AGENTS.md §7)."),
):
    """raw/<rel> 파일 작성/갱신. 사람 운영자 only. 에이전트 호출 ❌ (MCP는 wiki_ingest만).

    - payload.content = 전체 본문 (overwrite).
    - parent dir 없으면 자동 mkdir (P32: OS directory = first-class).
    - 기존 파일 있으면 overwrite (raw는 사람 1차, 의도적 갱신 OK).

    Actor 가드: raw/ 폴더는 사람 운영자 1차 영역. anonymous / 미식별 호출은 403.
    """
    if not _raw_write_allowed(actor):
        raise HTTPException(
            status_code=403,
            detail=(
                "raw/ 폴더는 사람 운영자 only (AGENTS.md §7). "
                "X-Actor 헤더에 사람 운영자 식별자를 명시하세요. "
                "에이전트는 MCP wiki_ingest(user_command=True) 로만 가능합니다."
            ),
        )
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
def delete_raw(
    name: str,
    path: str,
    actor: Optional[str] = Header(None, alias="X-Actor", description="운영자 식별자. 사람 운영자만 허용 (AGENTS.md §7)."),
):
    """raw/<rel> 파일/빈 디렉토리 삭제. hard delete (raw는 immutable-to-LLM, 사람 의도적 삭제 OK).

    - 파일: hard delete (undo 없음, OS 파일관리자 복구 가능).
    - 빈 디렉토리만 삭제. 파일 있는 디렉토리는 409.

    Actor 가드: raw/ 폴더는 사람 운영자 1차 영역. anonymous / 미식별 호출은 403.
    """
    if not _raw_write_allowed(actor):
        raise HTTPException(
            status_code=403,
            detail=(
                "raw/ 폴더는 사람 운영자 only (AGENTS.md §7). "
                "X-Actor 헤더에 사람 운영자 식별자를 명시하세요. "
                "에이전트는 MCP wiki_ingest(user_command=True) 로만 가능합니다."
            ),
        )
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
