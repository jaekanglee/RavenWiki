"""cli.py — Wiki MCP Server command-line entry point.

Default mode is read-only; pass --write for mutating tools, --admin for
destructive tools (delete / rename). Supports both stdio transport (local
Hermes) and streamable-http transport (Tailscale remote).

Why "cli.py" and not "server.py"?
---------------------------------
Our local package is also named `mcp` (it lives in `mcp/__init__.py`).
The real MCP SDK (`mcp[cli]>=1.x`) ships its own `mcp` package whose
submodules include `mcp.server.fastmcp.FastMCP`. Because our local
`mcp/__init__.py` is first on `sys.path` whenever the vault root is the
cwd, Python's import machinery resolves `import mcp` to our package, not
the SDK. To access the SDK's `FastMCP`, we temporarily remove our local
`mcp.*` entries from `sys.modules` and re-import — see `_load_sdk_fastmcp`.

Tools registered
----------------
Read (always):  wiki_search, wiki_get_page, wiki_lint, wiki_graph, wiki_log
Write (--write): + wiki_update, wiki_ingest
Admin (--admin): + wiki_delete, wiki_rename
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Any, Literal, Optional


def _load_sdk_fastmcp():
    """Import the real MCP SDK's `FastMCP`, dodging the local `mcp` package.

    Three obstacles stand between us and the SDK:

      1. `sys.modules['mcp']` may already point at our local wiki package
         (loaded by tests or earlier code paths).
      2. Our vault root is typically first on `sys.path`, so even after
         clearing `sys.modules`, `find_spec('mcp')` re-resolves to our
         local `mcp/__init__.py`.
      3. The cwd `''` entry behaves the same way (caller is often `cd`'d
         into the vault root).

    We fix all three: snapshot `sys.modules` and `sys.path`, scrub the
    entries that point at our local `mcp/`, do the import, then restore.
    """
    import os

    # Stash every mcp.* module currently loaded.
    stashed_modules = {
        name: mod
        for name, mod in sys.modules.items()
        if name == "mcp" or name.startswith("mcp.")
    }
    for name in list(stashed_modules):
        del sys.modules[name]

    # Identify path entries that point to a directory containing an `mcp/`
    # package *that is not* the SDK's mcp package. The SDK's `mcp/` ships
    # a `server/` subpackage, our local one does not — that distinguishes
    # them reliably.
    stashed_paths = []
    for entry in list(sys.path):
        # Treat both empty string ('' = cwd) and explicit paths the same.
        resolved = entry if entry else os.getcwd()
        candidate = Path(resolved) / "mcp"
        if not (candidate.is_dir() and (candidate / "__init__.py").exists()):
            continue
        if (candidate / "server").is_dir():
            # This is the SDK — leave it on sys.path.
            continue
        stashed_paths.append(entry)
        sys.path.remove(entry)

    try:
        fastmcp_mod = importlib.import_module("mcp.server.fastmcp")
        return fastmcp_mod.FastMCP
    finally:
        # Restore sys.path (preserve relative ordering by prepending).
        for entry in reversed(stashed_paths):
            if entry not in sys.path:
                sys.path.insert(0, entry)
        # Restore our local mcp.* so tool bodies still find our modules.
        for name, mod in stashed_modules.items():
            sys.modules[name] = mod


# Local package imports (our own `mcp` module). These resolve to the
# local wiki package because our `mcp/__init__.py` set sys.modules['mcp']
# during interpreter startup (or this file's earlier import).
from mcp import db as db_module
from mcp.tools import read as read_tools
from mcp.tools import write as write_tools
from mcp.resources import register_resources


# ────────────────────────── vault resolution ───────────────────────


def _resolve_vault(arg: Optional[Path]) -> Path:
    """vault root: CLI flag → default (parent of mcp/)."""
    if arg is not None:
        return Path(arg).resolve()
    return Path(__file__).resolve().parent.parent


# ────────────────────────── tool registration ──────────────────────


def register_tools(mcp: Any, mode: str, vault: Path) -> None:
    """Bind the 7 wiki tools onto a FastMCP instance, gated by `mode`.

    Read tools are always registered; write/admin tools are conditional.
    Each closure delegates to `mcp.tools.{read,write}` so the actual
    logic lives in one place (testable without the MCP transport).
    """

    # ─── 1. wiki_search ───
    @mcp.tool(name="wiki_search", description="FTS5 BM25 search across slug/title/tags/content.")
    def wiki_search(query: str, top_k: int = 10) -> list[dict]:
        return db_module.search_fts(query=query, top_k=top_k, vault=vault)

    # ─── 2. wiki_get_page ───
    @mcp.tool(
        name="wiki_get_page",
        description="Single page with content, frontmatter, backlinks, outbound links, and tags.",
    )
    def wiki_get_page(slug: str) -> dict | None:
        return db_module.get_page(slug=slug, vault=vault)

    # ─── 3. wiki_lint ───
    @mcp.tool(
        name="wiki_lint",
        description="Run scripts/lint.py against wiki.db and return counts + structured issues.",
    )
    def wiki_lint() -> dict:
        return read_tools.wiki_lint(ctx=None)

    # ─── 4. wiki_graph ───
    @mcp.tool(
        name="wiki_graph",
        description="Vault link graph as {nodes, edges}. Optional project filter substring-matches slugs.",
    )
    def wiki_graph(
        project: Optional[str] = None,
        fmt: Literal["json"] = "json",
    ) -> dict:
        return read_tools.wiki_graph(project=project, fmt=fmt, ctx=None)

    # ─── 5. wiki_log ───
    @mcp.tool(name="wiki_log", description="Last N non-empty log.md lines as structured entries.")
    def wiki_log(tail_n: int = 20) -> list[dict]:
        return read_tools.wiki_log(tail_n=tail_n, ctx=None)

    # ─── 6. wiki_update (write / admin) ───
    if mode in ("write", "admin"):
        @mcp.tool(
            name="wiki_update",
            description="Overwrite a vault markdown page. Requires --write or --admin.",
        )
        def wiki_update(
            slug: str,
            content: str,
            frontmatter: dict | None = None,
        ) -> dict:
            return write_tools.wiki_update(
                slug=slug,
                content=content,
                frontmatter_data=frontmatter,
                ctx=None,
            )

        @mcp.tool(
            name="wiki_ingest",
            description="Copy a raw source file into <vault>/raw/<project>/. Requires --write or --admin.",
        )
        def wiki_ingest(
            source: str,
            project: str | None = None,
            mode: str = "auto",
        ) -> dict:
            return write_tools.wiki_ingest(
                source=source, project=project, mode=mode, ctx=None
            )

    # ─── 7. wiki_delete / wiki_rename (admin only) ───
    if mode == "admin":
        @mcp.tool(
            name="wiki_delete",
            description="Archive a vault page to _archive/ and rebuild wiki.db. Requires --admin.",
        )
        def wiki_delete(slug: str) -> dict:
            return write_tools.wiki_delete(slug=slug, ctx=None)

        @mcp.tool(
            name="wiki_rename",
            description="Rename a slug, rewrite every inbound wikilink, and rebuild wiki.db. Requires --admin.",
        )
        def wiki_rename(old_slug: str, new_slug: str) -> dict:
            return write_tools.wiki_rename(old_slug=old_slug, new_slug=new_slug, ctx=None)


# ────────────────────────── main ───────────────────────────────────


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wiki-mcp",
        description="Wiki MCP Server — Model Context Protocol for the wiki vault.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="stdio (local Hermes) or http (Tailscale remote)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host")
    parser.add_argument("--port", type=int, default=8765, help="HTTP bind port")
    parser.add_argument(
        "--vault",
        type=Path,
        default=None,
        help="vault root path (default: parent of mcp/)",
    )
    parser.add_argument(
        "--mode",
        choices=["read", "write", "admin"],
        default="read",
        help="permission mode: read (default) / write / admin",
    )
    args = parser.parse_args(argv)

    vault = _resolve_vault(args.vault)

    # Banner goes to stderr so it doesn't pollute the stdio JSON stream.
    print(f"📁 vault:    {vault}", file=sys.stderr)
    print(f"🔐 mode:     {args.mode}", file=sys.stderr)
    print(f"📡 transport: {args.transport}", file=sys.stderr)
    if args.transport == "http":
        print(f"🌐 bind:     {args.host}:{args.port}", file=sys.stderr)

    mcp_cls = _load_sdk_fastmcp()
    mcp = mcp_cls("wiki")
    register_tools(mcp, args.mode, vault)
    register_resources(mcp, vault)

    if args.transport == "stdio":
        # Default: local in-process transport for Hermes / desktop clients.
        mcp.run()
    else:
        # streamable-http for Tailscale-bound remote access.
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")

    return 0


if __name__ == "__main__":
    sys.exit(main())