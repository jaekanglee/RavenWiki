"""raven.core.db.db_schema_drift — 구버전 스키마 감지 + `contested` 회귀 가드.

v0.7.183 (톡머리 vault operator report): pre-v0.7.67 standalone CLI가 만든
wiki.db는 pages.contested / pages_fts가 없어 MCP read가 깨졌다.
db_schema_drift()가 이를 감지하는지 검증한다.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from raven.core.db import db_schema_drift
from raven.core.registry import VaultMeta
from raven.core.vault import Vault

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


def _vault_at(tmp_path: Path) -> Vault:
    meta = VaultMeta.from_json("drift-test", {"path": str(tmp_path)})
    return Vault.load(meta)


def _write_db(tmp_path: Path, pages_sql: str) -> None:
    conn = sqlite3.connect(str(tmp_path / "wiki.db"))
    conn.executescript(
        pages_sql
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


def test_drift_false_on_canonical_schema(tmp_path: Path) -> None:
    _write_db(tmp_path, _CANONICAL_PAGES_SQL)
    assert db_schema_drift(_vault_at(tmp_path)) is False


def test_drift_true_on_old_standalone_cli_schema(tmp_path: Path) -> None:
    # 2026-07-01 standalone CLI 스키마: contested 없음 + FTS 없음
    _write_db(
        tmp_path,
        """
        CREATE TABLE pages (
          slug TEXT PRIMARY KEY, path TEXT NOT NULL, title TEXT, type TEXT,
          tags TEXT, confidence TEXT, created TEXT, updated TEXT,
          word_count INTEGER, mtime REAL, content TEXT
        );
        """,
    )
    assert db_schema_drift(_vault_at(tmp_path)) is True


def test_drift_true_when_contested_missing_only(tmp_path: Path) -> None:
    # pages_fts/tags/links는 최신이지만 pages.contested만 없는 중간 스키마 —
    # MCP wiki_get_page가 읽는 정확한 컬럼 회귀 가드 (v0.7.183).
    pages_sql = _CANONICAL_PAGES_SQL.replace(
        "  contested INTEGER DEFAULT 0,\n", ""
    )
    _write_db(tmp_path, pages_sql)
    assert db_schema_drift(_vault_at(tmp_path)) is True
