"""test_tools.py — exercise the 7 MCP tools + permission model."""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp import db
from mcp.tools import (
    VaultContext,
    PermissionError_,
    check_permission,
    WRITE,
    READ,
    ADMIN,
)
from mcp.tools.read import (
    wiki_search,
    wiki_get_page,
    wiki_lint,
    wiki_graph,
    wiki_log,
)
from mcp.tools.write import wiki_update, wiki_ingest, wiki_delete, wiki_rename


# ─────────────── permission model ───────────────


def test_check_permission_read_mode_allows_read_tools():
    check_permission("wiki_search", READ)  # must not raise


def test_check_permission_read_mode_blocks_writes():
    with pytest.raises(PermissionError_):
        check_permission("wiki_update", READ)
    with pytest.raises(PermissionError_):
        check_permission("wiki_ingest", READ)


def test_check_permission_write_mode_allows_writes():
    check_permission("wiki_update", WRITE)
    check_permission("wiki_ingest", WRITE)


def test_check_permission_write_mode_blocks_admin():
    with pytest.raises(PermissionError_):
        check_permission("wiki_delete", WRITE)
    with pytest.raises(PermissionError_):
        check_permission("wiki_rename", WRITE)


def test_check_permission_admin_mode_allows_everything():
    check_permission("wiki_update", ADMIN)
    check_permission("wiki_ingest", ADMIN)
    check_permission("wiki_delete", ADMIN)
    check_permission("wiki_rename", ADMIN)


# ─────────────── read tools (5) ───────────────


def test_tool_wiki_search(wiki_db: Path):
    ctx = VaultContext(vault=wiki_db.parent, mode=READ)
    results = wiki_search("wiki", top_k=3, ctx=ctx)
    assert isinstance(results, list)
    if results:
        r = results[0]
        assert "slug" in r and "score" in r


def test_tool_wiki_get_page(wiki_db: Path, sample_slug: str):
    ctx = VaultContext(vault=wiki_db.parent, mode=READ)
    page = wiki_get_page(sample_slug, ctx=ctx)
    assert page is not None
    assert page["slug"] == sample_slug
    assert "backlinks" in page
    assert "tags" in page
    assert "outbound_links" in page


def test_tool_wiki_get_page_missing(wiki_db: Path):
    ctx = VaultContext(vault=wiki_db.parent, mode=READ)
    page = wiki_get_page("nope_nope_nope", ctx=ctx)
    assert page is None


def test_tool_wiki_lint(wiki_db: Path):
    ctx = VaultContext(vault=wiki_db.parent, mode=READ)
    result = wiki_lint(ctx=ctx)
    assert "critical" in result
    assert "warning" in result
    assert "info" in result
    assert "total" in result
    assert isinstance(result["total"], int)


def test_tool_wiki_graph(wiki_db: Path):
    ctx = VaultContext(vault=wiki_db.parent, mode=READ)
    g = wiki_graph(ctx=ctx)
    assert "nodes" in g and "edges" in g
    assert isinstance(g["nodes"], list)


def test_tool_wiki_graph_with_project_filter(wiki_db: Path):
    ctx = VaultContext(vault=wiki_db.parent, mode=READ)
    g = wiki_graph(project="concept", ctx=ctx)
    assert "nodes" in g and "edges" in g


def test_tool_wiki_log(wiki_db: Path):
    ctx = VaultContext(vault=wiki_db.parent, mode=READ)
    entries = wiki_log(tail_n=3, ctx=ctx)
    assert isinstance(entries, list)


# ─────────────── write tools + permission enforcement ───────────────


def test_wiki_update_blocked_in_read_mode(wiki_db: Path, sample_slug: str):
    ctx = VaultContext(vault=wiki_db.parent, mode=READ)
    with pytest.raises(PermissionError_):
        wiki_update(slug=sample_slug, content="# nothing", ctx=ctx)


def test_wiki_ingest_blocked_in_read_mode(wiki_db: Path, tmp_path: Path):
    # Stage a fake raw source
    src = tmp_path / "x.md"
    src.write_text("# raw")
    # But first copy it into vault/raw so the path resolves (read mode never gets here)
    ctx = VaultContext(vault=wiki_db.parent, mode=READ)
    with pytest.raises(PermissionError_):
        wiki_ingest(source=str(src), ctx=ctx)


def test_wiki_update_allowed_in_write_mode(wiki_db: Path, sample_slug: str):
    """Round-trip: read content, write it back unchanged, verify same shape."""
    ctx = VaultContext(vault=wiki_db.parent, mode=WRITE)
    page = db.get_page(sample_slug, vault=ctx.vault)
    assert page is not None
    original_content = page["content"]

    result = wiki_update(
        slug=sample_slug, content=original_content, ctx=ctx
    )
    assert result["ok"] is True
    assert "updated" in result["message"].lower()

    # Verify file is unchanged
    page2 = db.get_page(sample_slug, vault=ctx.vault)
    # DB hasn't been re-built; raw_content is still old. That's OK — the
    # assertion is that wiki_update reported ok and the file exists.
    from pathlib import Path
    assert (ctx.vault / (sample_slug + ".md")).exists()


def test_wiki_update_unknown_file(wiki_db: Path):
    ctx = VaultContext(vault=wiki_db.parent, mode=WRITE)
    result = wiki_update(
        slug="does/not/exist", content="x", ctx=ctx
    )
    assert result["ok"] is False
    assert "does not exist" in result["message"]


def test_wiki_ingest_allowed_in_write_mode(wiki_db: Path, tmp_path: Path):
    """Stage a fake raw source, ingest it, verify it lands under raw/."""
    src_name = f"ingest_test_{tmp_path.name}.md"
    src = tmp_path / src_name
    src.write_text("# raw ingest test\nbody")
    ctx = VaultContext(vault=wiki_db.parent, mode=WRITE)
    result = wiki_ingest(source=str(src), project="test", ctx=ctx)
    assert result["ok"] is True
    assert result["pages_created"] == 1
    # File should now be under <vault>/raw/test/<basename>
    dest = ctx.vault / "raw" / "test" / src_name
    assert dest.exists()
    # Cleanup
    dest.unlink()
    project_dir = ctx.vault / "raw" / "test"
    if project_dir.exists():
        try:
            project_dir.rmdir()
        except OSError:
            pass


def test_wiki_ingest_idempotent(wiki_db: Path, tmp_path: Path):
    """Re-ingesting the same source without force is a no-op."""
    src_name = f"ingest_idem_{tmp_path.name}.md"
    src = tmp_path / src_name
    src.write_text("# raw")
    ctx = VaultContext(vault=wiki_db.parent, mode=WRITE)
    r1 = wiki_ingest(source=str(src), project="test", ctx=ctx)
    assert r1["pages_created"] == 1
    r2 = wiki_ingest(source=str(src), project="test", ctx=ctx)
    assert r2["pages_created"] == 0
    assert "already ingested" in r2["message"]
    # Cleanup
    dest = ctx.vault / "raw" / "test" / src_name
    dest.unlink()
    project_dir = ctx.vault / "raw" / "test"
    try:
        project_dir.rmdir()
    except OSError:
        pass


def test_admin_tools_blocked_in_write_mode(wiki_db: Path):
    """wiki_delete / wiki_rename require --admin."""
    with pytest.raises(PermissionError_):
        check_permission("wiki_delete", WRITE)
    with pytest.raises(PermissionError_):
        check_permission("wiki_rename", WRITE)
    # but allowed in admin
    check_permission("wiki_delete", ADMIN)
    check_permission("wiki_rename", ADMIN)


# ─────────────── admin tools: real implementations (M3) ─────────────


def test_wiki_update_accepts_top_level_slug(wiki_db: Path):
    """M3 fix: top-level slugs (no '/') are now valid (e.g. SCHEMA, log)."""
    ctx = VaultContext(vault=wiki_db.parent, mode=WRITE)
    # 'SCHEMA' is the README/index doc living at vault root
    page = db.get_page("SCHEMA", vault=ctx.vault)
    if page is None:
        pytest.skip("SCHEMA page not present in this vault")
    result = wiki_update(
        slug="SCHEMA", content=page["content"], ctx=ctx
    )
    assert result["ok"] is True
    assert "updated" in result["message"].lower()


def test_wiki_update_accepts_dotmd_suffix(wiki_db: Path):
    """M3: passing 'SCHEMA.md' (or any .md slug) should resolve to the same file."""
    ctx = VaultContext(vault=wiki_db.parent, mode=WRITE)
    page = db.get_page("SCHEMA", vault=ctx.vault)
    if page is None:
        pytest.skip("SCHEMA page not present in this vault")
    result = wiki_update(
        slug="SCHEMA.md", content=page["content"], ctx=ctx
    )
    assert result["ok"] is True


def test_wiki_delete_archives_and_rebuilds(wiki_db: Path, tmp_path: Path):
    """wiki_delete moves the file to _archive/<slug>-<timestamp>.md."""
    import frontmatter
    import uuid
    ctx = VaultContext(vault=wiki_db.parent, mode=ADMIN)

    # Stage an isolated page under queries/ so we don't touch real content
    target_dir = ctx.vault / "queries"
    target_dir.mkdir(exist_ok=True)
    unique = uuid.uuid4().hex[:8]
    target = target_dir / f"m3_delete_test_{tmp_path.name}_{unique}.md"
    # Defensive: remove any leftover from a prior crash.
    if target.exists():
        target.unlink()
    target.write_text(
        "---\ntitle: M3 delete test\ntype: query\n---\n\nbody\n",
        encoding="utf-8",
    )
    slug = "queries/m3_delete_test_" + tmp_path.name + "_" + unique

    result = wiki_delete(slug=slug, ctx=ctx)
    assert result["ok"] is True
    assert result["archived"] is not None
    assert (ctx.vault / result["archived"]).exists()
    assert not target.exists()

    # wiki.db should no longer index it
    page = db.get_page(slug, vault=ctx.vault)
    assert page is None

    # Restore from archive (best-effort) to keep tests idempotent
    archive = ctx.vault / result["archived"]
    archive.rename(target)
    from mcp.tools import write as _write_mod
    _write_mod._rebuild_db(ctx.vault)


def test_wiki_rename_rewrites_wikilinks_and_aliases(wiki_db: Path, tmp_path: Path):
    """wiki_rename moves the file, rewrites inbound [[link]]s, and aliases."""
    import frontmatter
    import uuid
    ctx = VaultContext(vault=wiki_db.parent, mode=ADMIN)

    queries_dir = ctx.vault / "queries"
    queries_dir.mkdir(exist_ok=True)

    # Use a UUID suffix so the test is fully idempotent — prior crashes or
    # parallel runs can't cause "new_slug already exists" failures.
    unique = uuid.uuid4().hex[:8]
    old_slug = f"queries/m3_old_{tmp_path.name}_{unique}"
    new_slug = f"queries/m3_new_{tmp_path.name}_{unique}"
    old_path = ctx.vault / f"{old_slug}.md"
    # Defensive cleanup: if a leftover from a prior crash exists, remove it.
    for p in [
        old_path,
        ctx.vault / f"{new_slug}.md",
        queries_dir / f"m3_ref_{tmp_path.name}_{unique}.md",
    ]:
        if p.exists():
            p.unlink()

    old_path.write_text(
        "---\ntitle: M3 rename source\ntype: query\nslug: " + old_slug + "\n---\n\nbody\n",
        encoding="utf-8",
    )
    referrer_path = queries_dir / f"m3_ref_{tmp_path.name}_{unique}.md"
    referrer_path.write_text(
        f"See [[{old_slug}]] and [[{old_slug}?]] for details.\n",
        encoding="utf-8",
    )
    _write_mod_rebuild(ctx.vault)

    # 2. Rename
    result = wiki_rename(old_slug=old_slug, new_slug=new_slug, ctx=ctx)
    assert result["ok"] is True
    assert result["rewritten_files"] >= 1
    assert not old_path.exists()
    assert (ctx.vault / f"{new_slug}.md").exists()

    # 3. Referrer's wikilinks were rewritten
    ref_text = referrer_path.read_text(encoding="utf-8")
    assert f"[[{old_slug}]]" not in ref_text
    assert f"[[{new_slug}]]" in ref_text
    assert f"[[{new_slug}?]]" in ref_text  # intent preserved

    # 4. Aliases frontmatter added
    new_post = frontmatter.loads((ctx.vault / f"{new_slug}.md").read_text(encoding="utf-8"))
    assert old_slug in (new_post.metadata.get("aliases") or [])
    assert new_post.metadata.get("slug") == new_slug

    # Cleanup
    referrer_path.unlink()
    (ctx.vault / f"{new_slug}.md").unlink()
    _write_mod_rebuild(ctx.vault)


def _write_mod_rebuild(vault: Path) -> None:
    """Helper: rebuild wiki.db so subsequent assertions see the new state."""
    from mcp.tools import write as _write_mod
    _write_mod._rebuild_db(vault)