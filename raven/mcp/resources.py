"""resources.py — MCP Resources for the wiki vault.

Resources are auto-injected context that MCP clients can fetch without an
explicit tool call. We register 5, each namespaced by vault name so one
MCP server process can serve every vault the registry knows about
(mirrors raven.mcp.cli.register_tools' `vault` argument):

    wiki://{vault}/index              — full page catalog (sqlite SELECT)
    wiki://{vault}/page/{slug}        — one page (content + frontmatter + links)
    wiki://{vault}/graph              — full link graph (nodes + edges)
    wiki://{vault}/log/recent         — last ~5KB of log.md
    wiki://{vault}/schema             — SCHEMA.md text

Resources are always read-only — no permission gating needed.
"""
from __future__ import annotations

import json
from typing import Any


def _to_json(payload: Any) -> str:
    """Serialize payload to pretty JSON (UTF-8, safe for unknown types)."""
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def register_resources(mcp: Any) -> None:
    """Bind the 5 wiki resources onto a FastMCP instance."""

    # Local imports kept inside the function so resources.py is importable
    # on its own (e.g. from tests) without forcing db.py to open a connection.
    from raven.mcp import db as db_module
    from raven.mcp.tools import resolve_vault_path

    # ─── wiki://{vault}/index ───
    @mcp.resource("wiki://{vault}/index")
    def wiki_index(vault: str) -> str:
        """Catalog of every page in the vault."""
        pages = db_module.list_pages(vault=resolve_vault_path(vault))
        return _to_json({
            "count": len(pages),
            "pages": pages,
        })

    # ─── wiki://{vault}/page/{slug} ───
    @mcp.resource("wiki://{vault}/page/{slug}")
    def wiki_page(vault: str, slug: str) -> str:
        """Single page (frontmatter + content + backlinks + tags).

        Returns a JSON envelope with `{found, page}` so consumers can tell
        a real miss from a payload.
        """
        page = db_module.get_page(slug=slug, vault=resolve_vault_path(vault))
        if page is None:
            return _to_json({"found": False, "slug": slug, "page": None})
        return _to_json({"found": True, "slug": slug, "page": page})

    # ─── wiki://{vault}/graph ───
    @mcp.resource("wiki://{vault}/graph")
    def wiki_graph(vault: str) -> str:
        """Full link graph (nodes = pages, edges = links)."""
        graph = db_module.graph(vault=resolve_vault_path(vault))
        return _to_json({
            "nodes_count": len(graph.get("nodes", [])),
            "edges_count": len(graph.get("edges", [])),
            **graph,
        })

    # ─── wiki://{vault}/log/recent ───
    @mcp.resource("wiki://{vault}/log/recent")
    def wiki_log_recent(vault: str) -> str:
        """Tail of log.md (last 5000 chars)."""
        log_path = resolve_vault_path(vault) / "log.md"
        if not log_path.exists():
            return "(no log.md at vault root)"
        text = log_path.read_text(encoding="utf-8")
        return text[-5000:] if len(text) > 5000 else text

    # ─── wiki://{vault}/schema ───
    @mcp.resource("wiki://{vault}/schema")
    def wiki_schema(vault: str) -> str:
        """Raw text of SCHEMA.md."""
        schema_path = resolve_vault_path(vault) / "SCHEMA.md"
        if not schema_path.exists():
            return "(no SCHEMA.md at vault root)"
        return schema_path.read_text(encoding="utf-8")