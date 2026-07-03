"""cli.py — Wiki MCP Server command-line entry point.

Default mode is read-only; pass --write for mutating tools, --admin for
destructive tools (delete / rename). Supports both stdio transport (local
in-process) and streamable-http transport (remote, e.g. Tailscale).

Why this file can import `mcp.server.fastmcp` directly
-----------------------------------------------------
The wiki package used to live at `mcp/`, which collided with the SDK's
`mcp[cli]>=1.x` package. After v0.6.0 the wiki package is at
`raven/mcp/`, so there is no name collision — `import mcp` resolves to
the SDK exactly as expected.

Tools registered
----------------
Read (always):  wiki_search, wiki_get_page, wiki_lint, wiki_graph, wiki_log
Write (--write): + wiki_update, wiki_ingest
Admin (--admin): + wiki_delete, wiki_rename
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, Literal, Optional

# Direct SDK import — no name collision (see module docstring).
from mcp.server.fastmcp import FastMCP

# Local package imports (our own `raven.mcp` module).
from raven.mcp import db as db_module
from raven.mcp.tools import VaultContext, resolve_vault_path
from raven.mcp.tools import read as read_tools
from raven.mcp.tools import write as write_tools
from raven.mcp.resources import register_resources


# ────────────────────────── tool registration ──────────────────────


def register_tools(mcp: Any, mode: str) -> None:
    """Bind the 9 wiki tools onto a FastMCP instance, gated by `mode`.

    One MCP server process serves every vault the registry knows about —
    each tool takes a `vault` (registered vault name) argument and resolves
    a fresh VaultContext per call, mirroring `raven.api.server`'s
    `/api/vaults/{name}/...` pattern instead of pinning to a single vault
    at startup. `mode` (read/write/admin) stays a server-wide setting
    decided at launch, since it's an access level for this process, not a
    per-vault property.

    Read tools are always registered; write/admin tools are conditional.
    Each closure delegates to `mcp.tools.{read,write}` so the actual
    logic lives in one place (testable without the MCP transport).
    """

    EXPERIMENTAL_PREFIX = (
        "[mcp/experimental] multi-agent write is advisory-only: "
        "advisory locks + idempotency are best-effort, NOT a hard concurrency guard. "
        "Concurrent writers face last-writer-wins. locks/queue/review are not implemented. "
        "Caller is responsible for sequencing. "
    )
    VAULT_ARG_NOTE = "`vault` is a registered vault name (see `raven vault list`). "

    # Alias so the permission `mode` survives into closures whose own
    # parameter is also named `mode` (wiki_ingest's auto/force mode) without
    # being shadowed.
    permission_mode = mode

    # ─── 1. wiki_search ───
    @mcp.tool(
        name="wiki_search",
        description=EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE + "FTS5 BM25 search across slug/title/tags/content.",
    )
    def wiki_search(vault: str, query: str, top_k: int = 10) -> list[dict]:
        return db_module.search_fts(query=query, top_k=top_k, vault=resolve_vault_path(vault))

    # ─── 2. wiki_get_page ───
    @mcp.tool(
        name="wiki_get_page",
        description=(
            EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
            + "Single page with content, frontmatter, backlinks, outbound links, and tags."
        ),
    )
    def wiki_get_page(vault: str, slug: str) -> dict | None:
        return db_module.get_page(slug=slug, vault=resolve_vault_path(vault))

    # ─── 3. wiki_lint ───
    @mcp.tool(
        name="wiki_lint",
        description=(
            EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
            + "Run the 14 vault lint checks and return counts + structured issues."
        ),
    )
    def wiki_lint(vault: str) -> dict:
        ctx = VaultContext(vault=resolve_vault_path(vault), mode=permission_mode)
        return read_tools.wiki_lint(ctx=ctx)

    # ─── 4. wiki_graph ───
    @mcp.tool(
        name="wiki_graph",
        description=(
            EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
            + "Vault link graph as {nodes, edges}. Optional project filter substring-matches slugs."
        ),
    )
    def wiki_graph(
        vault: str,
        project: Optional[str] = None,
        fmt: Literal["json"] = "json",
    ) -> dict:
        ctx = VaultContext(vault=resolve_vault_path(vault), mode=permission_mode)
        return read_tools.wiki_graph(project=project, fmt=fmt, ctx=ctx)

    # ─── 5. wiki_log ───
    @mcp.tool(
        name="wiki_log",
        description=EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE + "Last N non-empty log.md lines as structured entries.",
    )
    def wiki_log(vault: str, tail_n: int = 20) -> list[dict]:
        ctx = VaultContext(vault=resolve_vault_path(vault), mode=permission_mode)
        return read_tools.wiki_log(tail_n=tail_n, ctx=ctx)

    # ─── 6. wiki_update (write / admin) ───
    if mode in ("write", "admin"):
        @mcp.tool(
            name="wiki_update",
            description=(
                EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
                + "Create or overwrite a vault markdown page (upsert; new pages "
                "must pass the vault schema guard). Requires --write or --admin. "
                "Optional M4/F1 kwargs: actor (caller identity), "
                "idempotency_key (retry-suppression token)."
            ),
        )
        def wiki_update(
            vault: str,
            slug: str,
            content: str,
            frontmatter: dict | None = None,
            actor: str | None = None,
            idempotency_key: str | None = None,
        ) -> dict:
            ctx = VaultContext(vault=resolve_vault_path(vault), mode=permission_mode)
            return write_tools.wiki_update(
                slug=slug,
                content=content,
                frontmatter_data=frontmatter,
                actor=actor,
                idempotency_key=idempotency_key,
                ctx=ctx,
            )

        @mcp.tool(
            name="wiki_ingest",
            description=(
                EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
                + "Copy a raw source file into <vault>/raw/<project>/. "
                "Requires --write or --admin. Optional M4/F1 kwargs: actor, "
                "idempotency_key."
            ),
        )
        def wiki_ingest(
            vault: str,
            source: str,
            project: str | None = None,
            mode: str = "auto",
            actor: str | None = None,
            idempotency_key: str | None = None,
        ) -> dict:
            ctx = VaultContext(vault=resolve_vault_path(vault), mode=permission_mode)
            return write_tools.wiki_ingest(
                source=source, project=project, mode=mode,
                actor=actor, idempotency_key=idempotency_key,
                ctx=ctx,
            )

    # ─── 7. wiki_delete / wiki_rename (admin only) ───
    if mode == "admin":
        @mcp.tool(
            name="wiki_delete",
            description=(
                EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
                + "Archive a vault page to _archive/ and rebuild wiki.db. "
                "Requires --admin. Optional M4/F1 kwargs: actor, "
                "idempotency_key."
            ),
        )
        def wiki_delete(
            vault: str,
            slug: str,
            actor: str | None = None,
            idempotency_key: str | None = None,
        ) -> dict:
            ctx = VaultContext(vault=resolve_vault_path(vault), mode=permission_mode)
            return write_tools.wiki_delete(
                slug=slug,
                actor=actor,
                idempotency_key=idempotency_key,
                ctx=ctx,
            )

        @mcp.tool(
            name="wiki_rename",
            description=(
                EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
                + "Rename a slug, rewrite every inbound wikilink, and rebuild "
                "wiki.db. Requires --admin. Optional M4/F1 kwargs: actor, "
                "idempotency_key."
            ),
        )
        def wiki_rename(
            vault: str,
            old_slug: str,
            new_slug: str,
            actor: str | None = None,
            idempotency_key: str | None = None,
        ) -> dict:
            ctx = VaultContext(vault=resolve_vault_path(vault), mode=permission_mode)
            return write_tools.wiki_rename(
                old_slug=old_slug, new_slug=new_slug,
                actor=actor, idempotency_key=idempotency_key,
                ctx=ctx,
            )


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
        help="stdio (local in-process) or http (remote, e.g. Tailscale)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host")
    parser.add_argument("--port", type=int, default=8765, help="HTTP bind port")
    parser.add_argument(
        "--mode",
        choices=["read", "write", "admin"],
        default="read",
        help="permission mode: read (default) / write / admin",
    )
    args = parser.parse_args(argv)

    from raven.core.registry import registry

    reg = registry()
    vault_names = sorted(v.name for v in reg.list())

    # Banner goes to stderr so it doesn't pollute the stdio JSON stream.
    print(f"📁 vaults root: {reg.root}", file=sys.stderr)
    print(f"📚 vaults:      {', '.join(vault_names) or '(none registered)'}", file=sys.stderr)
    print(f"🔐 mode:     {args.mode}", file=sys.stderr)
    print(f"📡 transport: {args.transport}", file=sys.stderr)
    if args.transport == "http":
        print(f"🌐 bind:     {args.host}:{args.port}", file=sys.stderr)

    mcp = FastMCP("wiki")
    register_tools(mcp, args.mode)
    register_resources(mcp)

    if args.transport == "stdio":
        # Default: local in-process transport for desktop / local clients.
        mcp.run()
    else:
        # streamable-http for Tailscale-bound remote access.
        # v0.7.23+: FastMCP HTTP는 Starlette app을 만듦.
        # → 직접 uvicorn 실행 (host 검증 우회 + proxy_headers).
        # → 421 Misdirected Request 회피:
        #    uvicorn 0.30+ HTTP/1.1 strict Host check가 default on
        #    → Tailscale IP로 접속 시 Host 헤더 mismatch → 421
        #    → 해결: starlette app에 TrustedHostMiddleware(allowed_hosts=["*"]) 추가
        import uvicorn
        from starlette.middleware import Middleware
        from starlette.middleware.trustedhost import TrustedHostMiddleware

        app = mcp.streamable_http_app()  # FastMCP starlette app
        # v0.7.23+: TrustedHostMiddleware 우회 (모든 host 허용)
        # FastMCP streamable_http_app()이 middleware 파라미터 받음
        # → 직접 app 만들고 middleware 추가가 더 안전
        from starlette.applications import Starlette

        # FastMCP의 mount 경로를 그대로 두고 middleware 추가
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"],  # 모든 host 허용 (Tailscale IP 포함)
        )

        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            forwarded_allow_ips="*",
            proxy_headers=True,
            log_level="info",
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
