"""server.py — FastAPI surface over raven.core + raven.agents.

Single source of truth for the GUI's HTTP calls. The dashboard used to read
static JSON (page-<slug>.json etc.); it now calls this server, which keeps
everything dynamic and supports multiple vaults.

Design:
    - stateless: every request resolves the vault fresh
    - CORS open (local dashboard only); production should add auth
    - errors return {ok: false, error: "..."} (never raw stack traces)
    - all write ops use the engine; no shortcuts
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

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


app = FastAPI(title="raven API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────────── helpers ──────────────────────────


def _vault_or_404(name: str) -> Vault:
    meta = registry().get(name)
    if not meta:
        raise HTTPException(status_code=404, detail=f"vault {name!r} not found")
    return Vault.load(meta)


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
    out = []
    for v in registry().list():
        out.append({
            "name": v.name,
            "path": str(v.path),
            "mode": v.mode,
            "owner": v.owner,
            "default": v.default,
        })
    return {
        "ok": True,
        "vaults": out,
        "vaults_root": str(VAULTS_ROOT()),
    }


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
        },
    }


@app.post("/api/vaults/{name}/select")
def select_vault(name: str):
    """Set the registry default to `name`."""
    if not registry().set_default(name):
        raise HTTPException(status_code=404, detail=f"vault {name!r} not found")
    return {"ok": True, "active": name}


class VaultCreate(BaseModel):
    name: str = Field(..., description="vault name (lowercase kebab-case 권장)")
    path: str = Field(..., description="absolute path to vault directory")
    mode: str = Field("personal", description="personal | shared | agent")
    owner: str = Field("user", description="user or agent name")
    description: str = Field("", description="free text")
    bootstrap: bool = Field(
        True,
        description=(
            "Lite bootstrap policy (v2026-06-26, 2-tier model): if True, copy ONLY "
            "user-facing essentials (SCHEMA, RULES, log.md). Tier 1 raven-internal "
            "docs (OPERATIONS, agent/*, raven-policy) are NEVER auto-copied. "
            "Use `raven docs` command to read raven-internal docs."
        ),
    )


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

    try:
        v = _Vault.create(
            name=payload.name,
            path=Path(payload.path).expanduser(),
            mode=payload.mode,
            owner=payload.owner,
            description=payload.description,
            bootstrap=payload.bootstrap,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"create failed: {e}")

    return {
        "ok": True,
        "vault": {
            "name": v.meta.name,
            "path": str(v.root),
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
        ok=True if all 4 Lite bootstrap files match the source templates.
        ok=False with per-file checks otherwise.
    """
    v = _vault_or_404(name)
    result = v.verify_bootstrap()
    payload = result.to_dict()
    if not result.ok:
        raise HTTPException(status_code=409, detail=payload)
    return payload


# ────────────────────────── page endpoints ──────────────────────────


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


@app.get("/api/vaults/{name}/pages/{slug:path}")
def get_page(name: str, slug: str):
    v = _vault_or_404(name)
    fp = _safe_slug_or_400(slug, v).with_suffix(".md")
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"page {slug!r} not found in vault {name!r}")
    text = fp.read_text()
    meta, body = _split_fm(text)
    return {
        "ok": True,
        "vault": name,
        "slug": slug,
        "frontmatter": meta,
        "content": body,
    }


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
    )
    if not result.ok:
        if result.error == "exists":
            raise HTTPException(status_code=409, detail=f"page {result.slug!r} already exists")
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
    )
    if not result.ok:
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
    """
    v = _vault_or_404(name)
    safe_path = _safe_slug_or_400(slug, v)
    fp = safe_path.with_suffix(".md")
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"page {slug!r} not found")
    import datetime as _dt
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_dir = v.root / "_archive"
    archive_dir.mkdir(exist_ok=True)
    rel = fp.relative_to(v.root)
    dest = archive_dir / rel.parent / f"{rel.stem}-{ts}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    fp.rename(dest)
    # v0.5.1+: log.md에 archive entry 자동 append
    try:
        log_module.append(
            v, action="archive", subject=slug,
            files=[str(dest.relative_to(v.root))], note=f"원본: {slug}",
        )
    except Exception:
        pass
    return {"ok": True, "vault": name, "slug": slug, "archived_to": str(dest)}


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
        full_text = fp.read_text(errors="replace")
        text = full_text.lower()
        meta, body = _split_fm(full_text)
        slug = str(fp.relative_to(v.root))[:-3]
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
    v = _vault_or_404(name)
    result = db_module.build_db(v)
    lr = lint_module.run_lint(v)
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
):
    """log.md 작업 이력 조회."""
    v = _vault_or_404(name)
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
    """log.md rotate (500 entries 초과 시)."""
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
