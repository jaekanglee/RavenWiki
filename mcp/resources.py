"""resources.py — MCP Resources for the wiki vault.

Resources are auto-injected context that MCP clients can fetch without an
explicit tool call. We register 5:

    wiki://index              — full page catalog (sqlite SELECT)
    wiki://page/{slug}        — one page (content + frontmatter + links)
    wiki://graph              — full link graph (nodes + edges)
    wiki://log/recent         — last ~5KB of log.md
    wiki://schema             — SCHEMA.md text

Resources are always read-only — no permission gating needed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _to_json(payload: Any) -> str:
    """Serialize payload to pretty JSON (UTF-8, safe for unknown types)."""
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def register_resources(mcp: Any, vault: Path) -> None:
    """Bind the 5 wiki resources onto a FastMCP instance."""

    # Local imports kept inside the function so resources.py is importable
    # on its own (e.g. from tests) without forcing db.py to open a connection.
    from mcp import db as db_module

    # ─── wiki://index ───
    @mcp.resource("wiki://index")
    def wiki_index() -> str:
        """Catalog of every page in the vault."""
        pages = db_module.list_pages(vault=vault)
        return _to_json({
            "count": len(pages),
            "pages": pages,
        })

    # ─── wiki://page/{slug} ───
    @mcp.resource("wiki://page/{slug}")
    def wiki_page(slug: str) -> str:
        """Single page (frontmatter + content + backlinks + tags).

        Returns a JSON envelope with `{found, page}` so consumers can tell
        a real miss from a payload.
        """
        page = db_module.get_page(slug=slug, vault=vault)
        if page is None:
            return _to_json({"found": False, "slug": slug, "page": None})
        return _to_json({"found": True, "slug": slug, "page": page})

    # ─── wiki://graph ───
    @mcp.resource("wiki://graph")
    def wiki_graph() -> str:
        """Full link graph (nodes = pages, edges = links)."""
        graph = db_module.graph(vault=vault)
        return _to_json({
            "nodes_count": len(graph.get("nodes", [])),
            "edges_count": len(graph.get("edges", [])),
            **graph,
        })

    # ─── wiki://log/recent ───
    @mcp.resource("wiki://log/recent")
    def wiki_log_recent() -> str:
        """Tail of log.md (last 5000 chars)."""
        log_path = vault / "log.md"
        if not log_path.exists():
            return "(no log.md at vault root)"
        text = log_path.read_text(encoding="utf-8")
        return text[-5000:] if len(text) > 5000 else text

    # ─── wiki://schema ───
    @mcp.resource("wiki://schema")
    def wiki_schema() -> str:
        """Raw text of SCHEMA.md."""
        schema_path = vault / "SCHEMA.md"
        if not schema_path.exists():
            return "(no SCHEMA.md at vault root)"
        return schema_path.read_text(encoding="utf-8")