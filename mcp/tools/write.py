"""write.py — 2 mutating MCP tools (require --write).

Tools:
    wiki_update — overwrite a markdown file (frontmatter-aware)
    wiki_ingest — turn a raw source into a vault page (lightweight)

NOTE: this module does NOT touch git. The orchestrator (Hermes) commits
the diff after a batch of writes. Tools only mutate files.
"""
from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path
from typing import Optional

import frontmatter

from mcp import db
from mcp.tools import VaultContext, check_permission


# ─────────────── 6. wiki_update ───────────────


def wiki_update(
    slug: str,
    content: str,
    frontmatter_data: Optional[dict] = None,
    ctx: Optional[VaultContext] = None,
) -> dict:
    """Update (or create) a markdown page by slug.

    Args:
        slug: vault slug (e.g. "concepts/wiki")
        content: raw markdown body (without frontmatter)
        frontmatter_data: optional dict to serialize as YAML frontmatter
        ctx: VaultContext; defaults to read/write/admin per the CLI

    Returns:
        {"ok": bool, "message": str, "path": str}
    """
    ctx = ctx or VaultContext(vault=db._default_vault())
    ctx.require("wiki_update")  # raises if read mode

    if not slug or "/" not in slug and not frontmatter_data:
        # Slug is "category/name"; reject bare names so callers are explicit
        return {"ok": False, "message": f"slug must include a category, got {slug!r}", "path": ""}

    rel = Path(slug + ".md")
    abs_path = ctx.vault / rel
    if not abs_path.exists():
        return {
            "ok": False,
            "message": f"file does not exist: {rel}. Use wiki_ingest for new pages.",
            "path": str(rel),
        }

    # Read existing frontmatter if caller didn't supply one
    existing = frontmatter.load(abs_path)
    meta = dict(frontmatter_data) if frontmatter_data else dict(existing.metadata)
    meta["updated"] = dt.date.today().isoformat()

    post = frontmatter.Post(content, **meta)
    abs_path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    return {"ok": True, "message": f"updated {rel}", "path": str(rel)}


# ─────────────── 7. wiki_ingest ───────────────


def wiki_ingest(
    source: str,
    project: Optional[str] = None,
    mode: str = "auto",
    ctx: Optional[VaultContext] = None,
) -> dict:
    """Ingest a raw source into the vault.

    Args:
        source: absolute path to a file under <vault>/raw/ (or a string
                of raw text when source ends with ':::').
        project: optional project tag (added to frontmatter)
        mode: "auto" → write to raw/<project>/ if not yet present,
              "force" → always overwrite
        ctx: VaultContext

    Returns:
        {"ok": bool, "message": str, "pages_created": int, "pages_updated": int}
    """
    ctx = ctx or VaultContext(vault=db._default_vault())
    ctx.require("wiki_ingest")

    raw_root = ctx.vault / "raw"
    if not raw_root.exists():
        return {"ok": False, "message": f"raw/ does not exist at {raw_root}",
                "pages_created": 0, "pages_updated": 0}

    src_path = Path(source)
    if not src_path.is_absolute():
        src_path = ctx.vault / source

    if not src_path.exists():
        return {"ok": False, "message": f"source not found: {source}",
                "pages_created": 0, "pages_updated": 0}

    # Decide destination under raw/<project>/<basename>
    project_dir = raw_root / (project or "default")
    project_dir.mkdir(parents=True, exist_ok=True)
    dest = project_dir / src_path.name

    if dest.exists() and mode != "force":
        return {
            "ok": True,
            "message": f"already ingested at {dest.relative_to(ctx.vault)} (use mode=force to overwrite)",
            "pages_created": 0,
            "pages_updated": 0,
        }

    shutil.copy2(src_path, dest)
    return {
        "ok": True,
        "message": f"ingested to {dest.relative_to(ctx.vault)}",
        "pages_created": 1 if not dest.exists() else 0,
        "pages_updated": 0 if not dest.exists() else 1,
    }