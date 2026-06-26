"""test_db.py — db.py unit tests against the live wiki.db."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mcp import db


def test_db_connect(wiki_db: Path):
    conn = db.get_db(wiki_db.parent)
    assert isinstance(conn, sqlite3.Connection)
    # row_factory set means columns accessible by name
    row = conn.execute("SELECT slug FROM pages LIMIT 1").fetchone()
    assert row is not None
    assert "slug" in row.keys()
    conn.close()


def test_db_not_found(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="wiki.db not found"):
        db.get_db(tmp_path)


def test_db_default_vault_is_wiki_root(wiki_db: Path):
    """Default vault resolution should land on ~/Desktop/Dev/Project/Raven."""
    conn = db.get_db()  # no arg → defaults to mcp/../
    row = conn.execute("SELECT COUNT(*) FROM pages").fetchone()
    assert row[0] > 0
    conn.close()


def test_search_fts(wiki_db: Path):
    results = db.search_fts("wiki", top_k=5, vault=wiki_db.parent)
    assert isinstance(results, list)
    assert len(results) > 0
    r = results[0]
    assert {"slug", "title", "path", "score", "snippet"} <= set(r.keys())
    assert isinstance(r["score"], (int, float))


def test_search_top_k(wiki_db: Path):
    results = db.search_fts("wiki OR page OR concept", top_k=2, vault=wiki_db.parent)
    assert len(results) <= 2


def test_search_no_match(wiki_db: Path):
    results = db.search_fts("zzzzz_nonexistent_query_xyz", top_k=5, vault=wiki_db.parent)
    assert results == []


def test_get_page_existing(wiki_db: Path, sample_slug: str):
    page = db.get_page(sample_slug, vault=wiki_db.parent)
    assert page is not None
    assert page["slug"] == sample_slug
    assert page["title"]
    assert page["type"]
    assert "content" in page and "raw_content" in page


def test_get_page_not_found(wiki_db: Path):
    page = db.get_page("this_slug_does_not_exist", vault=wiki_db.parent)
    assert page is None


def test_get_page_includes_tags(wiki_db: Path, sample_slug: str):
    page = db.get_page(sample_slug, vault=wiki_db.parent)
    assert page is not None
    assert isinstance(page["tags"], list)
    # tags are strings
    for t in page["tags"]:
        assert isinstance(t, str)


def test_get_page_includes_outbound_links(wiki_db: Path, sample_slug: str):
    page = db.get_page(sample_slug, vault=wiki_db.parent)
    assert page is not None
    assert isinstance(page["outbound_links"], list)
    for ln in page["outbound_links"]:
        assert {"target_slug", "intent"} <= set(ln.keys())


def test_get_page_includes_backlinks_field(wiki_db: Path, sample_slug: str):
    page = db.get_page(sample_slug, vault=wiki_db.parent)
    assert page is not None
    # backlinks field always present (may be empty)
    assert "backlinks" in page
    assert isinstance(page["backlinks"], list)


def test_list_pages(wiki_db: Path):
    pages = db.list_pages(vault=wiki_db.parent)
    assert isinstance(pages, list)
    assert len(pages) > 0
    for p in pages:
        assert {"slug", "title", "type", "path", "updated"} <= set(p.keys())


def test_graph(wiki_db: Path):
    g = db.graph(vault=wiki_db.parent)
    assert set(g.keys()) == {"nodes", "edges"}
    assert isinstance(g["nodes"], list)
    assert isinstance(g["edges"], list)
    if g["edges"]:
        e = g["edges"][0]
        assert {"source", "target", "intent"} <= set(e.keys())


def test_tail_log(wiki_db: Path):
    entries = db.tail_log(tail_n=5, vault=wiki_db.parent)
    assert isinstance(entries, list)
    assert len(entries) <= 5
    if entries:
        assert "line" in entries[0]


def test_tail_log_more_than_available(wiki_db: Path):
    """Asking for more than exists should not crash."""
    entries = db.tail_log(tail_n=10_000, vault=wiki_db.parent)
    assert isinstance(entries, list)


def test_schema_text(wiki_db: Path):
    text = db.schema_text(vault=wiki_db.parent)
    assert isinstance(text, str)
    assert "##" in text or "Schema" in text or len(text) > 100