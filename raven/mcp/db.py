"""db.py — read-only query helpers for wiki.db (SCHEMA v2.4).

All public functions return plain dicts / lists so they're trivially
JSON-serializable for the MCP transport. Connections are opened per-call
(read-only workload; no concurrent writers in this process).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional


# ─────────────────────────── helpers ──────────────────────────────


def _default_vault() -> Path:
    """mcp/ is a sibling of wiki.db → vault root is parent of mcp/."""
    return Path(__file__).resolve().parent.parent


def _resolve_vault(vault: Optional[Path | str]) -> Path:
    p = Path(vault) if vault else _default_vault()
    return p


def get_db(vault: Optional[Path | str] = None) -> sqlite3.Connection:
    """Open a connection to <vault>/wiki.db with row_factory=Row.

    Raises FileNotFoundError if wiki.db does not exist (caller should
    run build_db.py first).
    """
    root = _resolve_vault(vault)
    db_path = root / "wiki.db"
    if not db_path.exists():
        raise FileNotFoundError(
            f"wiki.db not found at {db_path}. Run scripts/build_db.py first."
        )
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]


# ─────────────────────────── pages ────────────────────────────────


def list_pages(vault: Optional[Path | str] = None) -> list[dict]:
    """All pages (catalog). Used by wiki://index resource."""
    conn = get_db(vault)
    try:
        rows = conn.execute(
            "SELECT slug, title, type, path, updated FROM pages ORDER BY slug"
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def search_fts(
    query: str,
    top_k: int = 10,
    vault: Optional[Path | str] = None,
) -> list[dict]:
    """FTS5 BM25 search across slug/title/tags/content."""
    conn = get_db(vault)
    try:
        rows = conn.execute(
            "SELECT p.slug, p.title, p.path, "
            "       bm25(pages_fts) AS score, "
            "       snippet(pages_fts, 3, '**', '**', '...', 32) AS snippet "
            "FROM pages_fts "
            "JOIN pages p ON p.rowid = pages_fts.rowid "
            "WHERE pages_fts MATCH ? "
            # v0.7.66 (평가 P1#8): 자동 생성 카탈로그는 검색 제외.
            # LIKE의 `_`는 단일문자 와일드카드라 ESCAPE 필수.
            "  AND p.slug != 'content/index' "
            "  AND p.slug NOT LIKE 'content/\\_index/%' ESCAPE '\\' "
            "ORDER BY bm25(pages_fts) LIMIT ?",
            (query, top_k),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def get_page(
    slug: str, vault: Optional[Path | str] = None
) -> Optional[dict]:
    """Single page + backlinks + outbound links + tags.

    Returns None if slug doesn't exist.
    """
    conn = get_db(vault)
    try:
        row = conn.execute(
            "SELECT slug, title, type, created, updated, path, "
            "       confidence, contested, content, raw_content "
            "FROM pages WHERE slug = ?",
            (slug,),
        ).fetchone()
        if not row:
            return None
        page = dict(row)
        page["tags"] = [
            r["tag"]
            for r in conn.execute(
                "SELECT tag FROM tags WHERE page_slug = ? ORDER BY tag",
                (slug,),
            ).fetchall()
        ]
        page["backlinks"] = _rows_to_dicts(
            conn.execute(
                "SELECT source_slug, source_title, source_path "
                "FROM v_backlinks WHERE slug = ? ORDER BY source_slug",
                (slug,),
            ).fetchall()
        )
        page["outbound_links"] = _rows_to_dicts(
            conn.execute(
                "SELECT target_slug, intent "
                "FROM links WHERE source_slug = ? ORDER BY target_slug",
                (slug,),
            ).fetchall()
        )
        return page
    finally:
        conn.close()


# ─────────────────────────── graph ────────────────────────────────


def graph(vault: Optional[Path | str] = None) -> dict[str, list[dict]]:
    """Full link graph: nodes (pages) + edges (links)."""
    conn = get_db(vault)
    try:
        nodes = _rows_to_dicts(
            conn.execute(
                "SELECT slug, title, type FROM pages ORDER BY slug"
            ).fetchall()
        )
        edges = _rows_to_dicts(
            conn.execute(
                "SELECT source_slug AS source, target_slug AS target, intent "
                "FROM links ORDER BY source_slug, target_slug"
            ).fetchall()
        )
        return {"nodes": nodes, "edges": edges}
    finally:
        conn.close()


# ─────────────────────────── log tail ────────────────────────────


def tail_log(
    tail_n: int = 20, vault: Optional[Path | str] = None
) -> list[dict]:
    """Last N non-empty lines of log.md (heuristic — log is free-text)."""
    root = _resolve_vault(vault)
    log_path = root / "log.md"
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").splitlines()
    # Keep only non-blank lines, then take the tail
    nonblank = [ln for ln in lines if ln.strip()]
    return [{"line": ln} for ln in nonblank[-tail_n:]]


# ─────────────────────────── schema dump ──────────────────────────


def schema_text(vault: Optional[Path | str] = None) -> str:
    """Raw text of SCHEMA.md (resource: wiki://schema)."""
    root = _resolve_vault(vault)
    schema_path = root / "SCHEMA.md"
    if not schema_path.exists():
        return ""
    return schema_path.read_text(encoding="utf-8")