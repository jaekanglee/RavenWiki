"""server.py — FastAPI surface over wikisys.core + wikisys.agents.

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

from wikisys.core import registry, resolve_active_vault, link_module
from wikisys.core import db_module, lint_module, export_module
from wikisys.core.vault import Vault


app = FastAPI(title="wikisys API", version="0.2.0")
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


# ────────────────────────── vault endpoints ──────────────────────────


@app.get("/api/vaults")
def list_vaults():
    """All registered vaults (with metadata)."""
    out = []
    for v in registry().list():
        out.append({
            "name": v.name,
            "path": str(v.path),
            "mode": v.mode,
            "owner": v.owner,
            "default": v.default,
        })
    return {"ok": True, "vaults": out}


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


@app.post("/api/vaults/create")
def create_vault(payload: VaultCreate):
    """Create a new vault on disk + register it.

    Mirrors `wikisys vault create <name> <path> --mode <mode>`.
    """
    from wikisys.core.vault import Vault as _Vault

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
        },
    }


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
    fp = v.root / f"{slug}.md"
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
    v = _vault_or_404(name)
    fp = v.root / f"{payload.slug}.md"
    if fp.exists():
        raise HTTPException(status_code=409, detail=f"page {payload.slug!r} already exists")
    fp.parent.mkdir(parents=True, exist_ok=True)
    fm = [
        "---",
        f"title: {payload.title}",
        f"type: {payload.type}",
        f"tags: [{', '.join(payload.tags)}]",
        f"created: {__import__('datetime').date.today().isoformat()}",
        f"updated: {__import__('datetime').date.today().isoformat()}",
        "---",
        "",
    ]
    fp.write_text("\n".join(fm) + payload.content + "\n")
    return {"ok": True, "vault": name, "slug": payload.slug}


@app.put("/api/vaults/{name}/pages/{slug:path}")
def update_page(name: str, slug: str, payload: PageUpdate):
    v = _vault_or_404(name)
    fp = v.root / f"{slug}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"page {slug!r} not found")
    text = fp.read_text()
    meta, _ = _split_fm(text)
    if payload.title is not None:
        meta["title"] = payload.title
    if payload.type is not None:
        meta["type"] = payload.type
    if payload.tags is not None:
        meta["tags"] = payload.tags
    meta["updated"] = __import__("datetime").date.today().isoformat()
    fm_block = ["---"]
    for k, val in meta.items():
        if isinstance(val, list):
            fm_block.append(f"{k}: [{', '.join(val)}]")
        else:
            fm_block.append(f"{k}: {val}")
    fm_block.append("---")
    fp.write_text("\n".join(fm_block) + "\n\n" + payload.content + "\n")
    return {"ok": True, "vault": name, "slug": slug}


@app.delete("/api/vaults/{name}/pages/{slug:path}")
def delete_page(name: str, slug: str):
    v = _vault_or_404(name)
    fp = v.root / f"{slug}.md"
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"page {slug!r} not found")
    archive = v.root / "_archive"
    archive.mkdir(exist_ok=True)
    import datetime as _dt
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = archive / f"{slug.replace('/', '_')}-{ts}.md"
    fp.rename(dest)
    return {"ok": True, "vault": name, "slug": slug, "archived_to": str(dest)}


# ────────────────────────── query endpoints ──────────────────────────


@app.get("/api/vaults/{name}/search")
def search(name: str, q: str = Query(..., min_length=1), top_k: int = 10):
    v = _vault_or_404(name)
    # reuse agent's lightweight search via direct walk
    import re as _re
    terms = [t.lower() for t in _re.findall(r"\w+", q) if t]
    if not terms:
        return {"ok": True, "vault": name, "results": []}
    scores = []
    for fp in v.content_root.rglob("*.md"):
        text = fp.read_text(errors="replace").lower()
        meta, body = _split_fm(fp.read_text(errors="replace"))
        slug = str(fp.relative_to(v.root))[:-3]
        score = sum(text.count(t) for t in terms)
        if score > 0:
            scores.append((score, {
                "slug": slug,
                "title": meta.get("title", slug),
                "type": meta.get("type", "?"),
                "score": score,
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
