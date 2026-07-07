"""read.py — read-only MCP tools (always permitted).

Tools:
    wiki_search       — FTS5 BM25
    wiki_get_page     — single page + backlinks/tags/outbound
    wiki_lint         — raven.core.lint (14 checks), same runner as the REST API
    wiki_graph        — nodes + edges
    wiki_log          — last N log.md entries
    wiki_get_guide    — Lite bootstrap 3종 read-only viewer (v0.7.91+)
    wiki_get_guide_diff — Lite bootstrap 3종 unified diff (v0.7.95+, vs raven install template)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from raven.mcp import db
from raven.mcp.tools import VaultContext
from raven.mcp.tools import LITE_GUIDE_KINDS, _resolve_guide_path, read_guide, read_guide_diff


# ─────────────── 1. wiki_search ───────────────


def wiki_search(
    query: str, top_k: int = 10, ctx: Optional[VaultContext] = None
) -> list[dict]:
    """FTS5 BM25 search across the vault."""
    ctx = ctx or VaultContext(vault=db._default_vault())
    return db.search_fts(query=query, top_k=top_k, vault=ctx.vault)


# ─────────────── 2. wiki_get_page ───────────────


def wiki_get_page(slug: str, ctx: Optional[VaultContext] = None) -> Optional[dict]:
    """Single page with backlinks, outbound links, and tags."""
    ctx = ctx or VaultContext(vault=db._default_vault())
    return db.get_page(slug=slug, vault=ctx.vault)


# ─────────────── 3. wiki_lint ───────────────


def wiki_lint(ctx: Optional[VaultContext] = None) -> dict:
    """Run raven.core.lint (14 checks) against the vault; return structured summary.

    v0.7.x: previously shelled out to a per-vault `<vault>/scripts/lint.py`,
    which only exists for vaults that opted into the standalone LLM-Wiki
    script bundle — every other vault (including the default Docker-managed
    ones) hit "lint.py not found". Calling `raven.core.lint.run_all()`
    in-process matches what the REST API's `/lint` endpoint already does,
    so behavior is consistent regardless of vault layout.
    """
    ctx = ctx or VaultContext(vault=db._default_vault())
    from raven.core.lint import run_all
    from raven.core.registry import VaultMeta
    from raven.core.vault import Vault

    vault_obj = Vault(meta=VaultMeta(name=ctx.vault.name, path=ctx.vault), root=ctx.vault)
    result = run_all(vault_obj)
    return {
        "critical": result["counts"]["critical"],
        "warning": result["counts"]["warning"],
        "info": result["counts"]["info"],
        "total": result["counts"]["total"],
        "issues": result["issues"],
    }


# ─────────────── 4. wiki_graph ───────────────


def wiki_graph(
    project: Optional[str] = None,
    fmt: str = "json",
    ctx: Optional[VaultContext] = None,
) -> dict:
    """Page + link graph (json). `project` filter is a future option."""
    ctx = ctx or VaultContext(vault=db._default_vault())
    g = db.graph(vault=ctx.vault)
    # Optional filter on edges / nodes by slug prefix (project-style buckets)
    if project:
        g = {
            "nodes": [n for n in g["nodes"] if project in n["slug"]],
            "edges": [
                e for e in g["edges"]
                if project in e["source"] or project in e["target"]
            ],
        }
    g["format"] = fmt
    return g


# ─────────────── 5. wiki_log ───────────────


def wiki_log(tail_n: int = 20, ctx: Optional[VaultContext] = None) -> list[dict]:
    """Last N non-empty log.md lines."""
    ctx = ctx or VaultContext(vault=db._default_vault())
    return db.tail_log(tail_n=tail_n, vault=ctx.vault)


# ─────────────── 6. wiki_get_guide (v0.7.91+) ───────────────


def wiki_get_guide(
    kind: str,
    ctx: Optional[VaultContext] = None,
) -> dict:
    """Read a Lite bootstrap file (whitelist-only).

    Mirrors ``GET /api/vaults/{name}/guide/{kind}`` so MCP and REST expose
    the same surface to agents. The 3-kind whitelist is enforced by
    ``_resolve_guide_path`` — anything else raises ``GuideNotFoundError``
    (MCP transport surfaces it as a tool error, not a vault error).

    Useful for agents that want to read the vault's own PROJECT-WORKFLOW
    via standard MCP instead of reaching into the filesystem (R9:
    vault 외부 시스템/폴더 수정 ❌, so reading the bootstrap file directly
    from disk is technically a vault-external system call).
    """
    ctx = ctx or VaultContext(vault=db._default_vault())
    return read_guide(vault=ctx.vault, kind=kind)


# ─────────────── 7. wiki_get_guide_diff (v0.7.95+) ───────────────


def wiki_get_guide_diff(
    kind: str,
    ctx: Optional[VaultContext] = None,
) -> dict:
    """Unified diff of a Lite bootstrap file vs raven install template.

    Mirrors ``GET /api/vaults/{name}/guide-diff/{kind:path}`` (v0.7.94) so
    MCP and REST expose the same diagnostic surface. The 3-kind whitelist
    is enforced by ``_resolve_guide_template`` — anything else raises
    ``GuideNotFoundError`` (MCP tool error).

    Useful for agents to diagnose "why is my vault's PROJECT-WORKFLOW
    mismatched?" without reaching into the filesystem. The diff is
    line-based (difflib.unified_diff) and truncated at 200 lines for
    large files like PROJECT-WORKFLOW.md.
    """
    ctx = ctx or VaultContext(vault=db._default_vault())
    return read_guide_diff(vault=ctx.vault, kind=kind)
