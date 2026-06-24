"""read.py — 5 read-only MCP tools (always permitted).

Tools:
    wiki_search  — FTS5 BM25
    wiki_get_page — single page + backlinks/tags/outbound
    wiki_lint    — reuse scripts/lint.py (subprocess to keep isolation)
    wiki_graph   — nodes + edges
    wiki_log     — last N log.md entries
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from mcp import db
from mcp.tools import VaultContext


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
    """Run scripts/lint.py against wiki.db; return structured summary.

    Reuses the existing CLI (subprocess) to avoid importing lint as a
    module (it has its own constants — keeps a clean boundary).
    """
    ctx = ctx or VaultContext(vault=db._default_vault())
    scripts_dir = ctx.vault / "scripts"
    lint_script = scripts_dir / "lint.py"
    if not lint_script.exists():
        return {
            "critical": 0,
            "warning": 0,
            "info": 0,
            "total": 0,
            "issues": [],
            "error": f"lint.py not found at {lint_script}",
        }

    proc = subprocess.run(
        [sys.executable, str(lint_script), "--db", str(ctx.vault / "wiki.db"),
         "--vault", str(ctx.vault), "--quiet"],
        capture_output=True,
        text=True,
        check=False,
    )
    # The --quiet flag prints only the summarize() headline.
    # Parse: "📊 N critical, M warning, K info, T total"
    headline = (proc.stdout or "").strip().splitlines()[-1] if proc.stdout.strip() else ""
    counts = {"critical": 0, "warning": 0, "info": 0, "total": 0}
    if headline.startswith("📊"):
        parts = headline.replace("📊", "").strip().split(",")
        for part in parts:
            k, _, v = part.strip().partition(" ")
            if k in counts:
                try:
                    counts[k] = int(v)
                except ValueError:
                    pass

    # For richer output, run a second time WITHOUT --quiet and parse the issues
    proc2 = subprocess.run(
        [sys.executable, str(lint_script), "--db", str(ctx.vault / "wiki.db"),
         "--vault", str(ctx.vault)],
        capture_output=True,
        text=True,
        check=False,
    )
    issues = []
    for line in (proc2.stdout or "").splitlines():
        if line.startswith(("🔴", "🟡", "🔵")):
            # format: "<emoji> [severity] <path>: <message>"
            try:
                _, rest = line.split(" ", 1)  # strip emoji
                severity = rest.split("]", 1)[0].lstrip("[").strip()
                tail = rest.split("]", 1)[1].strip()
                path, _, message = tail.partition(": ")
                issues.append({
                    "severity": severity,
                    "path": path,
                    "message": message,
                })
            except (ValueError, IndexError):
                continue

    result = {
        "critical": counts["critical"],
        "warning": counts["warning"],
        "info": counts["info"],
        "total": counts["total"],
        "issues": issues,
    }
    if proc.returncode not in (0, 1):
        result["error"] = proc.stderr or "lint exited unexpectedly"
    return result


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