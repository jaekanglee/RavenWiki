"""MCP read path schema drift guard — old-schema wiki.db → clear error, not
cryptic SQLite error (`no such column: contested`, `no such table: pages_fts`).

v0.7.183 (톡머리 vault operator report): legacy standalone CLI (2026-07-01,
pre-v0.7.67)가 만든 구버전 스키마 wiki.db를 MCP가 읽으면 raw SQLite 에러로
깨졌다. raven/mcp/db.get_db()가 drift를 감지하고 rebuild 힌트를 포함한
명확한 RuntimeError를 던지는지 검증한다.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from raven.mcp import db as mcp_db


def _write_old_schema_db(db_path: Path) -> None:
    """Pre-v0.7.67 standalone-CLI schema: pages에 contested 없음, pages_fts 없음."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE pages (
          slug TEXT PRIMARY KEY, path TEXT NOT NULL, title TEXT, type TEXT,
          tags TEXT, confidence TEXT, created TEXT, updated TEXT,
          word_count INTEGER, mtime REAL, content TEXT
        );
        CREATE TABLE tags (name TEXT PRIMARY KEY, count INTEGER DEFAULT 0);
        CREATE TABLE links (
          src TEXT NOT NULL, dst TEXT NOT NULL, kind TEXT NOT NULL, intent TEXT
        );
        """
    )
    conn.commit()
    conn.close()


_CANONICAL_PAGES_SQL = """
CREATE TABLE pages (
  slug TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  type TEXT NOT NULL,
  created TEXT NOT NULL,
  updated TEXT NOT NULL,
  path TEXT NOT NULL,
  confidence TEXT,
  contested INTEGER DEFAULT 0,
  content TEXT NOT NULL,
  raw_content TEXT NOT NULL,
  collection TEXT NOT NULL DEFAULT 'root',
  status TEXT NOT NULL DEFAULT 'current',
  aliases TEXT NOT NULL DEFAULT '[]',
  importance REAL DEFAULT 0.0,
  centrality REAL DEFAULT 0.0,
  community INTEGER DEFAULT 0,
  layer REAL DEFAULT 0.0,
  freshness REAL DEFAULT 0.0
);
"""


def _write_canonical_db(db_path: Path) -> None:
    """Canonical SCHEMA v2.4 subset (scripts/build_db.py SCHEMA_SQL 축약)."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        _CANONICAL_PAGES_SQL
        + """
        CREATE TABLE tags (page_slug TEXT NOT NULL, tag TEXT NOT NULL);
        CREATE TABLE links (
          source_slug TEXT NOT NULL, target_slug TEXT NOT NULL,
          context TEXT, intent TEXT
        );
        CREATE VIRTUAL TABLE pages_fts USING fts5(slug, title, tags_concat, content, aliases);
        """
    )
    conn.commit()
    conn.close()


def test_get_db_raises_clear_error_on_old_schema(tmp_path: Path) -> None:
    _write_old_schema_db(tmp_path / "wiki.db")
    with pytest.raises(RuntimeError) as exc:
        mcp_db.get_db(tmp_path)
    msg = str(exc.value)
    assert "outdated schema" in msg
    assert "pages.contested / pages_fts" in msg
    assert f"raven build --vault {tmp_path.name}" in msg


def test_get_db_ok_on_canonical_schema(tmp_path: Path) -> None:
    _write_canonical_db(tmp_path / "wiki.db")
    conn = mcp_db.get_db(tmp_path)
    try:
        assert conn is not None
        assert conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0] == 0
    finally:
        conn.close()


def test_get_db_missing_db_still_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        mcp_db.get_db(tmp_path)
