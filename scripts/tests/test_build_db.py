"""TDD tests for build_db.py (SQLite v2.4 schema).

These tests describe the contract of build_db.py. They were written FIRST
(RED phase) before build_db.py existed.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE_VAULT = Path(__file__).resolve().parent / "fixtures" / "sample-vault"


# ───────────────────────────── helpers ──────────────────────────────

def _run_build_db(vault: Path, db_path: Path) -> None:
    """Invoke the CLI entry point: scripts/build_db.py <vault> --db <db>."""
    build_db = Path(__file__).resolve().parent.parent / "build_db.py"
    result = subprocess.run(
        [sys.executable, str(build_db), str(vault), "--db", str(db_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"build_db.py failed (rc={result.returncode})\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


@pytest.fixture
def db(tmp_path: Path) -> Path:
    """Run build_db.py against the fixture vault into tmp_path/wiki.db."""
    db_path = tmp_path / "wiki.db"
    _run_build_db(FIXTURE_VAULT, db_path)
    return db_path


@pytest.fixture
def conn(db: Path):
    c = sqlite3.connect(str(db))
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.close()


def _all_table_names(c: sqlite3.Connection) -> set[str]:
    rows = c.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
    ).fetchall()
    return {r["name"] for r in rows}


# ─────────────────────────── schema tests ───────────────────────────

def test_schema_created(db: Path) -> None:
    """Tables pages, tags, links, pages_fts + views v_backlinks, v_pages_with_tags exist."""
    c = sqlite3.connect(str(db))
    c.row_factory = sqlite3.Row
    names = _all_table_names(c)
    c.close()
    for required in {"pages", "tags", "links", "pages_fts",
                     "v_backlinks", "v_pages_with_tags"}:
        assert required in names, f"missing schema object: {required}"


def test_pages_indexed(conn: sqlite3.Connection) -> None:
    """All .md in content/ + _meta/ are scanned and inserted (7 pages)."""
    rows = conn.execute(
        "SELECT slug, type, length(content) AS n FROM pages ORDER BY slug"
    ).fetchall()
    slugs = {r["slug"] for r in rows}
    expected = {
        "a", "b", "c-broken", "d-missing", "e-tags", "f-custom-tag",
        "_meta/rules",
    }
    assert slugs == expected, f"slugs mismatch: {slugs}"
    for r in rows:
        assert r["n"] > 0, f"page {r['slug']} has empty content"


# ─────────────────────────── wikilink tests ─────────────────────────

def test_wikilinks_extracted(conn: sqlite3.Connection) -> None:
    """a.md → b.md and back, plus future-section placeholder."""
    rows = conn.execute(
        "SELECT source_slug, target_slug, intent FROM links ORDER BY source_slug, target_slug"
    ).fetchall()
    pairs = {(r["source_slug"], r["target_slug"]): r["intent"] for r in rows}

    assert ("a", "b") in pairs
    assert ("b", "a") in pairs
    # a → c-broken also exists (we wrote [[c-broken]] in a.md? — no, we wrote [[b]] twice)
    # Let me assert what's actually in the fixture:
    assert ("a", "future-section") in pairs


def test_wikilink_intent_broken(conn: sqlite3.Connection) -> None:
    """`[[does-not-exist]]!` from c-broken → intent='broken' (CRITICAL candidate)."""
    row = conn.execute(
        "SELECT intent FROM links WHERE source_slug='c-broken' AND target_slug='does-not-exist'"
    ).fetchone()
    assert row is not None, "broken link not extracted"
    assert row["intent"] == "broken"


def test_wikilink_intent_missing(conn: sqlite3.Connection) -> None:
    """`[[future-section]]?` → intent='missing' (placeholder)."""
    rows = conn.execute(
        "SELECT intent FROM links WHERE target_slug='future-section'"
    ).fetchall()
    intents = {r["intent"] for r in rows}
    assert "missing" in intents, f"expected missing intent, got {intents}"


# ─────────────────────────── tag tests ──────────────────────────────

def test_tags_separated(conn: sqlite3.Connection) -> None:
    """e.md has [test, alpha, beta] → three rows in tags table."""
    rows = conn.execute(
        "SELECT tag FROM tags WHERE page_slug='e-tags' ORDER BY tag"
    ).fetchall()
    tags = {r["tag"] for r in rows}
    assert tags == {"test", "alpha", "beta"}


def test_tags_view_flat(conn: sqlite3.Connection) -> None:
    """v_pages_with_tags exposes a comma-joined tag list per page."""
    row = conn.execute(
        "SELECT tags_list FROM v_pages_with_tags WHERE slug='e-tags'"
    ).fetchone()
    assert row is not None
    parts = set(row["tags_list"].split(","))
    assert parts == {"test", "alpha", "beta"}


# ─────────────────────────── search & backlinks ─────────────────────

def test_fts5_search(conn: sqlite3.Connection) -> None:
    """BM25 search for 'Karpathy' returns b.md (which mentions Karpathy)."""
    try:
        rows = conn.execute(
            "SELECT slug FROM pages_fts WHERE pages_fts MATCH 'Karpathy' ORDER BY rank"
        ).fetchall()
    except sqlite3.OperationalError as e:
        pytest.fail(f"FTS5 query failed: {e}")
    slugs = {r["slug"] for r in rows}
    assert "b" in slugs, f"Karpathy match missing: {slugs}"


def test_backlinks_view(conn: sqlite3.Connection) -> None:
    """v_backlinks: pages linking TO 'a' should include 'b' (and 'a' itself if self-ref)."""
    rows = conn.execute(
        "SELECT source_slug, source_title FROM v_backlinks WHERE slug='a' ORDER BY source_slug"
    ).fetchall()
    sources = {r["source_slug"] for r in rows}
    assert "b" in sources, f"backlink to 'a' from 'b' missing: {sources}"
    # source_title populated via JOIN to pages
    b_row = next((r for r in rows if r["source_slug"] == "b"), None)
    assert b_row is not None and b_row["source_title"]


# ─────────────────────────── idempotency ────────────────────────────

def test_idempotent(tmp_path: Path) -> None:
    """Running build_db.py twice → identical page/link/tag counts."""
    db1 = tmp_path / "first.db"
    _run_build_db(FIXTURE_VAULT, db1)

    def counts(p: Path) -> tuple[int, int, int]:
        c = sqlite3.connect(str(p))
        npages = c.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        nlinks = c.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        ntags = c.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
        c.close()
        return npages, nlinks, ntags

    db2 = tmp_path / "second.db"
    _run_build_db(FIXTURE_VAULT, db2)
    assert counts(db1) == counts(db2)


# ─────────────────────────── slug strategy ──────────────────────────

def test_slug_from_frontmatter(tmp_path: Path) -> None:
    """frontmatter `slug:` wins over path-based slug."""
    vault = tmp_path / "vault"
    (vault / "content").mkdir(parents=True)
    (vault / "content" / "page.md").write_text(
        "---\ntitle: X\ncreated: 2026-06-24\nupdated: 2026-06-24\n"
        "type: concept\ntags: []\nsources: []\nslug: custom-slug\n---\n\n# X\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "wiki.db"
    _run_build_db(vault, db_path)
    c = sqlite3.connect(str(db_path))
    rows = c.execute("SELECT slug FROM pages").fetchall()
    c.close()
    assert [r[0] for r in rows] == ["custom-slug"]


def test_slug_from_path(tmp_path: Path) -> None:
    """No frontmatter slug → use vault-relative path with .md stripped, content/ prefix removed."""
    vault = tmp_path / "vault"
    (vault / "content").mkdir(parents=True)
    (vault / "content" / "llm-wiki.md").write_text(
        "---\ntitle: X\ncreated: 2026-06-24\nupdated: 2026-06-24\n"
        "type: concept\ntags: []\nsources: []\n---\n\n# X\n",
        encoding="utf-8",
    )
    (vault / "_meta").mkdir(parents=True)
    (vault / "_meta" / "system-design.md").write_text(
        "---\ntitle: X\ncreated: 2026-06-24\nupdated: 2026-06-24\n"
        "type: rule\ntags: []\nsources: []\n---\n\n# X\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "wiki.db"
    _run_build_db(vault, db_path)
    c = sqlite3.connect(str(db_path))
    rows = c.execute("SELECT slug FROM pages ORDER BY slug").fetchall()
    c.close()
    slugs = [r[0] for r in rows]
    # content/ prefix stripped, _meta/ prefix kept
    assert "llm-wiki" in slugs
    assert "_meta/system-design" in slugs


def test_excluded_dirs_skipped(tmp_path: Path) -> None:
    """raw/, _archive/, scripts/, node_modules/ are NOT scanned."""
    vault = tmp_path / "vault"
    for excluded in ("raw", "_archive", "scripts", "node_modules"):
        d = vault / excluded / "content"
        d.mkdir(parents=True)
        (d / "should-be-skipped.md").write_text(
            "---\ntitle: Skip\ncreated: 2026-06-24\nupdated: 2026-06-24\n"
            "type: concept\ntags: []\nsources: []\n---\n\nbody\n",
            encoding="utf-8",
        )
    db_path = tmp_path / "wiki.db"
    _run_build_db(vault, db_path)
    c = sqlite3.connect(str(db_path))
    rows = c.execute("SELECT slug FROM pages").fetchall()
    c.close()
    assert rows == [], f"expected no pages, got {[r[0] for r in rows]}"


def test_all_caps_slug_preserved(tmp_path: Path) -> None:
    """SCHEMA.md → slug 'SCHEMA' (uppercase preserved)."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "SCHEMA.md").write_text(
        "---\ntitle: Schema\ncreated: 2026-06-24\nupdated: 2026-06-24\n"
        "type: rule\ntags: []\nsources: []\n---\n\n# Schema\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "wiki.db"
    _run_build_db(vault, db_path)
    c = sqlite3.connect(str(db_path))
    rows = c.execute("SELECT slug FROM pages").fetchall()
    c.close()
    assert [r[0] for r in rows] == ["SCHEMA"]


def test_missing_frontmatter_defaults(tmp_path: Path) -> None:
    """Page with no frontmatter is still indexed (defaults applied)."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "_meta").mkdir()
    (vault / "_meta" / "rules.md").write_text(
        "# Just a doc\nNo frontmatter here.\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "wiki.db"
    _run_build_db(vault, db_path)
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    row = c.execute(
        "SELECT slug, type, length(content) AS n FROM pages WHERE slug='_meta/rules'"
    ).fetchone()
    c.close()
    assert row is not None, "missing-frontmatter page not indexed"
    assert row["type"] == "rule", f"expected default type=rule, got {row['type']}"
    assert row["n"] > 0


def test_cli_prints_summary(tmp_path: Path) -> None:
    """CLI prints a one-line summary with page/link/tag counts."""
    db_path = tmp_path / "wiki.db"
    build_db = Path(__file__).resolve().parent.parent / "build_db.py"
    result = subprocess.run(
        [sys.executable, str(build_db), str(FIXTURE_VAULT), "--db", str(db_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"build_db.py failed: {result.stderr}"
    assert "wiki.db" in result.stdout, f"summary missing in stdout: {result.stdout!r}"
    assert "pages" in result.stdout and "links" in result.stdout and "tags" in result.stdout
