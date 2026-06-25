"""write.py — 2 mutating MCP tools (require --write).

Tools:
    wiki_update — overwrite a markdown file (frontmatter-aware)
    wiki_ingest — turn a raw source into a vault page (lightweight)

NOTE: this module does NOT touch git. The orchestrator (Hermes) commits
the diff after a batch of writes. Tools only mutate files.
"""
from __future__ import annotations

import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import frontmatter

from mcp import db
from mcp.tools import VaultContext, check_permission


# ─────────────── shared helpers ───────────────


def _resolve_md_path(vault: Path, slug: str) -> Path:
    """Resolve a slug to an absolute markdown path.

    The slug may be a vault-relative path with or without the .md suffix
    (e.g. ``"concepts/wiki"`` or ``"_meta/SCHEMA.md"``).
    """
    p = Path(slug)
    if p.suffix != ".md":
        p = p.with_suffix(".md")
    return vault / p


def _rebuild_db(vault: Path) -> None:
    """Re-run scripts/build_db.py so wiki.db reflects on-disk changes.

    Best-effort: prints to stderr on failure but does not raise (admin
    operations should succeed even if DB rebuild fails — the caller can
    manually rerun build_db later).
    """
    build_script = vault / "scripts" / "build_db.py"
    if not build_script.exists():
        return
    try:
        subprocess.run(
            [sys.executable, str(build_script), str(vault)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"⚠️  build_db.py failed: {e.stderr or e.stdout}\n")


# ─────────────── 6. wiki_update ───────────────


def wiki_update(
    slug: str,
    content: str,
    frontmatter_data: Optional[dict] = None,
    ctx: Optional[VaultContext] = None,
) -> dict:
    """Update (or create) a markdown page by slug.

    Args:
        slug: vault slug (e.g. ``"concepts/wiki"``, ``"SCHEMA"``,
              ``"_meta/SCHEMA.md"``). Top-level slugs (no ``/``) are
              allowed — the file simply lives at the vault root.
        content: raw markdown body (without frontmatter)
        frontmatter_data: optional dict to serialize as YAML frontmatter
        ctx: VaultContext; defaults to read/write/admin per the CLI

    Returns:
        ``{"ok": bool, "message": str, "path": str}``
    """
    ctx = ctx or VaultContext(vault=db._default_vault())
    ctx.require("wiki_update")  # raises if read mode

    # M3 fix (was: rejected any slug without "/"). We now only require
    # *some* non-empty slug — top-level pages (e.g. SCHEMA.md) are valid.
    if not slug:
        return {"ok": False, "message": "slug required", "path": ""}

    abs_path = _resolve_md_path(ctx.vault, slug)
    if not abs_path.exists():
        return {
            "ok": False,
            "message": (
                f"file does not exist: {abs_path.relative_to(ctx.vault)}. "
                "Use wiki_ingest for new pages."
            ),
            "path": str(abs_path.relative_to(ctx.vault)),
        }

    # Read existing frontmatter if caller didn't supply one
    existing = frontmatter.load(abs_path)
    meta = dict(frontmatter_data) if frontmatter_data else dict(existing.metadata)
    meta["updated"] = dt.date.today().isoformat()

    post = frontmatter.Post(content, **meta)
    abs_path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    rel = abs_path.relative_to(ctx.vault)
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

    # M3 fix: callers sometimes pass VaultContext(vault="~/wiki") as a str.
    # Normalize to Path before any / operator, otherwise `str / "raw"`
    # raises TypeError on Py 3.11+.
    vault_path = Path(ctx.vault).expanduser()
    raw_root = vault_path / "raw"
    if not raw_root.exists():
        return {"ok": False, "message": f"raw/ does not exist at {raw_root}",
                "pages_created": 0, "pages_updated": 0}

    src_path = Path(source).expanduser()
    if not src_path.is_absolute():
        src_path = vault_path / source

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
            "message": f"already ingested at {dest.relative_to(vault_path)} (use mode=force to overwrite)",
            "pages_created": 0,
            "pages_updated": 0,
        }

    shutil.copy2(src_path, dest)
    return {
        "ok": True,
        "message": f"ingested to {dest.relative_to(vault_path)}",
        "pages_created": 1,
        "pages_updated": 0,
    }


# ─────────────── 8. wiki_delete (admin) ───────────────


def wiki_delete(
    slug: str,
    ctx: Optional[VaultContext] = None,
) -> dict:
    """Delete a vault page by archiving it to ``_archive/``.

    The page is moved to ``<vault>/_archive/<slug>-YYYYMMDD.md`` (never
    permanently destroyed — git + archive both retain history). ``wiki.db``
    is then rebuilt so backlinks and search reflect the new state.

    Args:
        slug: vault slug (e.g. ``"concepts/wiki"``)
        ctx: VaultContext (must be ``admin`` mode)

    Returns:
        ``{"ok": bool, "message": str, "archived": str|None,
            "rewritten_files": int}``
    """
    ctx = ctx or VaultContext(vault=db._default_vault(), mode="admin")
    ctx.require("wiki_delete")

    if not slug:
        return {"ok": False, "message": "slug required",
                "archived": None, "rewritten_files": 0}

    vault_path = Path(ctx.vault).expanduser()
    abs_path = _resolve_md_path(vault_path, slug)
    if not abs_path.exists():
        return {"ok": False, "message": f"{slug} not found",
                "archived": None, "rewritten_files": 0}

    archive_dir = vault_path / "_archive"
    archive_dir.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = archive_dir / f"{abs_path.stem}-{stamp}.md"
    # If a same-second collision exists, suffix with a counter.
    counter = 1
    while archive_path.exists():
        archive_path = archive_dir / f"{abs_path.stem}-{stamp}-{counter}.md"
        counter += 1

    abs_path.rename(archive_path)
    _rebuild_db(vault_path)

    return {
        "ok": True,
        "message": f"archived {slug} → {archive_path.relative_to(vault_path)}",
        "archived": str(archive_path.relative_to(vault_path)),
        "rewritten_files": 0,
    }


# ─────────────── 9. wiki_rename (admin) ───────────────


def wiki_rename(
    old_slug: str,
    new_slug: str,
    ctx: Optional[VaultContext] = None,
) -> dict:
    """Rename a slug and rewrite every inbound ``[[old_slug]]`` wikilink.

    Steps:
        1. Locate ``<old>.md`` under the vault.
        2. Update its frontmatter ``slug:`` field (if present) to ``new_slug``
           and add ``aliases: [<old_slug>]`` so old links continue to resolve.
        3. Move the file to ``<new>.md``.
        4. Walk every other markdown file in the vault and rewrite
           ``[[old_slug]]`` → ``[[new_slug]]`` (preserving intent
           suffixes ``!`` / ``?``).
        5. Rebuild ``wiki.db`` so backlinks/search reflect the rename.

    Args:
        old_slug: current vault slug (file must exist)
        new_slug: target vault slug (file must NOT exist)
        ctx: VaultContext (must be ``admin`` mode)

    Returns:
        ``{"ok": bool, "message": str, "rewritten_files": int,
            "old_slug": str, "new_slug": str}``
    """
    ctx = ctx or VaultContext(vault=db._default_vault(), mode="admin")
    ctx.require("wiki_rename")

    if not old_slug or not new_slug:
        return {"ok": False, "message": "old_slug and new_slug are required",
                "rewritten_files": 0, "old_slug": old_slug, "new_slug": new_slug}

    vault_path = Path(ctx.vault).expanduser()
    old_path = _resolve_md_path(vault_path, old_slug)
    if not old_path.exists():
        return {"ok": False, "message": f"{old_slug} not found",
                "rewritten_files": 0, "old_slug": old_slug, "new_slug": new_slug}

    new_path = _resolve_md_path(vault_path, new_slug)
    if new_path.exists() and new_path != old_path:
        return {"ok": False, "message": f"{new_slug} already exists",
                "rewritten_files": 0, "old_slug": old_slug, "new_slug": new_slug}

    # 1+2+3: rewrite frontmatter and move file.
    text = old_path.read_text(encoding="utf-8")
    post = frontmatter.Post("")
    body = text
    try:
        post = frontmatter.loads(text)
        meta = dict(post.metadata)
        body = post.content
    except Exception:
        meta = {}

    meta["slug"] = new_slug
    aliases = list(meta.get("aliases") or [])
    if old_slug not in aliases:
        aliases.insert(0, old_slug)
    meta["aliases"] = aliases
    meta["updated"] = dt.date.today().isoformat()

    if body.startswith("---\n"):
        # safety: re-strip frontmatter if loader missed it
        body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)

    new_post = frontmatter.Post(body, **meta)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.write_text(frontmatter.dumps(new_post) + "\n", encoding="utf-8")

    # Remove the old file (unless rename is a no-op overwrite-in-place).
    if old_path != new_path:
        old_path.unlink()

    # 4: rewrite every inbound [[old_slug]] → [[new_slug]] across the vault.
    # Capture the optional intent char (!/?) and re-emit it intact, so
    # [[old]]! / [[old]]? stay syntactically equivalent after rename.
    pattern = re.compile(r"\[\[" + re.escape(old_slug) + r"(!|\?)?\]\]")
    rewritten = 0
    excluded = {"raw", "_archive", "scripts", "node_modules", ".venv", ".git", "dashboard"}
    for md in vault_path.rglob("*.md"):
        if any(part in excluded for part in md.relative_to(vault_path).parts):
            continue
        try:
            content = md.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new_content, n = pattern.subn(
            lambda m: "[[" + new_slug + (m.group(1) or "") + "]]",
            content,
        )
        if n > 0:
            md.write_text(new_content, encoding="utf-8")
            rewritten += n

    # 5: rebuild DB
    _rebuild_db(vault_path)

    return {
        "ok": True,
        "message": f"renamed {old_slug} → {new_slug} ({rewritten} wikilinks rewritten)",
        "rewritten_files": rewritten,
        "old_slug": old_slug,
        "new_slug": new_slug,
    }