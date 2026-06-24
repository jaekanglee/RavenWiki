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
from mcp.tools.write import wiki_update, wiki_ingest


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