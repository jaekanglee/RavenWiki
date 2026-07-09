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
Read (always):  wiki_search, wiki_get_page, wiki_lint, wiki_graph, wiki_log, wiki_get_guide, wiki_get_guide_diff, wiki_stale_detect
Write (--write): + wiki_update, wiki_ingest, wiki_archive
Admin (--admin): + wiki_delete, wiki_rename

ADR-2026-07-06 신규: wiki_stale_detect (read), wiki_archive (write).
v0.7.91+: wiki_get_guide (read) — Lite bootstrap 3종 read-only viewer.
v0.7.95+: wiki_get_guide_diff (read) — Lite bootstrap 3종 diff vs template.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, Literal, Optional

# Direct SDK import — no name collision (see module docstring).
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Local package imports (our own `raven.mcp` module).
from raven.mcp import db as db_module
from raven.mcp.tools import VaultContext, resolve_vault_path
from raven.mcp.tools import read as read_tools
from raven.mcp.tools import stale as stale_tools  # ADR-2026-07-06 §1.3 신규 도구
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

    # ─── 6. wiki_get_guide (v0.7.91+) — Lite bootstrap 3종 read-only viewer
    @mcp.tool(
        name="wiki_get_guide",
        description=(
            EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
            + "Read a Lite bootstrap file (SCHEMA.md / PROJECT-WORKFLOW.md / log.md). "
            + "Mirrors GET /api/vaults/{name}/guide/{kind}. kind must be exactly one of "
            + "the 3 whitelisted paths — anything else returns a tool error so the caller can self-correct. "
            + "Useful for agents that need to read the vault's own workflow rules via MCP "
            + "instead of reaching into the filesystem (R9: vault 외부 시스템 ❌)."
        ),
    )
    def wiki_get_guide(vault: str, kind: str) -> dict:
        from raven.mcp.tools import GuideNotFoundError, read_guide
        try:
            return read_guide(vault=resolve_vault_path(vault), kind=kind)
        except GuideNotFoundError as e:
            # MCP transports exceptions as tool errors; this is the
            # 403-equivalent for non-whitelisted kinds.
            raise ValueError(str(e)) from e

    # ─── 7. wiki_get_guide_diff (v0.7.95+) — Lite bootstrap 3종 diff
    @mcp.tool(
        name="wiki_get_guide_diff",
        description=(
            EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
            + "Unified diff of a Lite bootstrap file vs raven install template. "
            + "Mirrors GET /api/vaults/{name}/guide-diff/{kind} (v0.7.94). "
            + "kind must be one of the 3 whitelisted bootstrap paths — same "
            + "whitelist as wiki_get_guide. Truncated at 200 lines. Useful "
            + "for agents to diagnose 'why is my vault's PROJECT-WORKFLOW "
            + "mismatched?' without filesystem access (R9)."
        ),
    )
    def wiki_get_guide_diff(vault: str, kind: str) -> dict:
        from raven.mcp.tools import GuideNotFoundError, read_guide_diff
        try:
            return read_guide_diff(vault=resolve_vault_path(vault), kind=kind)
        except GuideNotFoundError as e:
            raise ValueError(str(e)) from e

    # ─── 7.5. wiki_check_freshness (v0.7.114+, ADR-2026-07-08) ───
    # Lite bootstrap 3종 hash + cache mismatch. silent warn 기본.
    # HTTP 클라이언트는 동일 동작을 X-Guide-Hash 헤더로도 받을 수 있음 (ADR §2.1).
    @mcp.tool(
        name="wiki_check_freshness",
        description=(
            VAULT_ARG_NOTE
            + "ADR-2026-07-08: lite bootstrap 3종 (SCHEMA.md / PROJECT-WORKFLOW.md / log.md) "
            + "SHA256 + 캐시 mismatch → freshness_warning. cache_hash 형식 = "
            + "'SCHEMA=abc,PROJECT-WORKFLOW=def' (명시) 또는 'abc,def' (순서 고정). "
            + "Silent warn 기본 — 강제 read ❌. Stamp은 _meta/agents/.guide-version 자동."
        ),
    )
    def wiki_check_freshness(vault: str, cache_hash: str | None = None) -> dict:
        from raven.mcp.tools.guide import check_freshness
        from raven.mcp.tools import resolve_vault_path
        return check_freshness(
            vault_root=resolve_vault_path(vault),
            cache_hash=cache_hash,
        )

    # ─── 7.5.5. wiki_get_advice ───
    @mcp.tool(
        name="wiki_get_advice",
        description=(
            EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
            + "List AI network diagnosis advices (e.g. bridge nodes, bloated collections, orphan pages, underlinked nodes) for the vault."
        ),
    )
    def wiki_get_advice(vault: str) -> list[dict]:
        from raven.core.vault import Vault
        from raven.core.registry import VaultMeta
        from raven.core.advice import get_advice
        v = Vault.load(VaultMeta(name=vault, path=resolve_vault_path(vault)))
        return get_advice(v)

    # ─── 7.5.6. wiki_get_ai_advice ───
    @mcp.tool(
        name="wiki_get_ai_advice",
        description=(
            EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
            + "List AI network diagnosis advices with LLM-generated curation guidelines."
        ),
    )
    def wiki_get_ai_advice(vault: str) -> list[dict]:
        from raven.core.vault import Vault
        from raven.core.registry import VaultMeta
        from raven.core.ai_advice import generate_ai_advice
        v = Vault.load(VaultMeta(name=vault, path=resolve_vault_path(vault)))
        return generate_ai_advice(v)

    # ─── 7.5.7. wiki_hybrid_search (v0.7.164+) ───
    @mcp.tool(
        name="wiki_hybrid_search",
        description=(
            EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
            + "Hybrid search combining FTS5 BM25 and vector embeddings (ko-sroberta/bge-m3-ko). "
            + "Falls back to BM25-only if sqlite-vec is not available."
        ),
    )
    def wiki_hybrid_search(vault: str, query: str, limit: int = 10) -> list[dict]:
        from raven.core.vault import Vault
        from raven.core.registry import VaultMeta
        from raven.core.hybrid_search import hybrid_search as core_hybrid_search
        v = Vault.load(VaultMeta(name=vault, path=resolve_vault_path(vault)))
        return core_hybrid_search(v, query, limit=limit)

    # ─── 7.5.8. wiki_rag_query (v0.7.164+) ───
    @mcp.tool(
        name="wiki_rag_query",
        description=(
            EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
            + "Answer user questions using RAG (Retrieval-Augmented Generation) based on hybrid search match results."
        ),
    )
    def wiki_rag_query(vault: str, query: str) -> dict:
        from raven.core.vault import Vault
        from raven.core.registry import VaultMeta
        from raven.core.rag import query_rag
        v = Vault.load(VaultMeta(name=vault, path=resolve_vault_path(vault)))
        return query_rag(v, query)

    # ─── 7.6. wiki_relations_list ───
    @mcp.tool(
        name="wiki_relations_list",
        description=(
            EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
            + "List semantic relations, optionally filtered by source slug or type."
        ),
    )
    def wiki_relations_list(
        vault: str,
        slug: Optional[str] = None,
        relation_type: Optional[str] = None,
    ) -> list[dict]:
        ctx = VaultContext(vault=resolve_vault_path(vault), mode=permission_mode)
        return read_tools.wiki_relations_list(slug=slug, relation_type=relation_type, ctx=ctx)

    # ─── 6. wiki_update (write / admin) ───
    if mode in ("write", "admin"):
        @mcp.tool(
            name="wiki_stale_detect",
            description=(
                EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
                + "ADR-2026-07-06 §1.3: stale 후보 + evidence + suggested_action 반환 (read-only). "
                + "Optional age_threshold_days (default 90), include_self_verified."
            ),
        )
        def wiki_stale_detect(
            vault: str,
            age_threshold_days: int = 90,
            include_self_verified: bool = False,
        ) -> dict:
            return stale_tools.wiki_stale_detect(
                vault=resolve_vault_path(vault),
                age_threshold_days=age_threshold_days,
                include_self_verified=include_self_verified,
            )

        @mcp.tool(
            name="wiki_archive",
            description=(
                EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
                + "ADR-2026-07-06 §1.3: 페이지를 archive/<YYYY-MM-DD>/<slug>.md로 이동 + frontmatter stamp. "
                + "Requires --write or --admin. Optional reason/actor/dry_run."
            ),
        )
        def wiki_archive(
            vault: str,
            slug: str,
            reason: str = "stale_over_threshold",
            actor: str | None = None,
            dry_run: bool = False,
        ) -> dict:
            ctx = VaultContext(vault=resolve_vault_path(vault), mode=permission_mode)
            return stale_tools.wiki_archive(
                slug=slug,
                reason=reason,
                actor=actor,
                dry_run=dry_run,
                ctx=ctx,
            )

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

        @mcp.tool(
            name="wiki_relation_add",
            description=(
                EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
                + "Add or update a semantic relation in a page's frontmatter. Requires --write or --admin."
            ),
        )
        def wiki_relation_add(
            vault: str,
            source_slug: str,
            target_slug: str,
            relation_type: str,
            evidence: list[str] | str,
            reason: str,
            confidence: Optional[dict | float] = None,
            verified_by: Optional[list[str] | str] = None,
            actor: Optional[str] = None,
            idempotency_key: Optional[str] = None,
        ) -> dict:
            ctx = VaultContext(vault=resolve_vault_path(vault), mode=permission_mode)
            return write_tools.wiki_relation_add(
                source_slug=source_slug, target_slug=target_slug, relation_type=relation_type,
                evidence=evidence, reason=reason, confidence=confidence, verified_by=verified_by,
                actor=actor, idempotency_key=idempotency_key, ctx=ctx
            )

        @mcp.tool(
            name="wiki_relation_remove",
            description=(
                EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
                + "Remove a semantic relation from a page's frontmatter. Requires --write or --admin."
            ),
        )
        def wiki_relation_remove(
            vault: str,
            source_slug: str,
            target_slug: str,
            relation_type: str,
            actor: Optional[str] = None,
            idempotency_key: Optional[str] = None,
        ) -> dict:
            ctx = VaultContext(vault=resolve_vault_path(vault), mode=permission_mode)
            return write_tools.wiki_relation_remove(
                source_slug=source_slug, target_slug=target_slug, relation_type=relation_type,
                actor=actor, idempotency_key=idempotency_key, ctx=ctx
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

    mcp = FastMCP(
        "wiki",
        # v0.7.148+ fix: FastMCP's own transport_security auto-locks Host-header
        # validation to 127.0.0.1/localhost/::1 whenever no `host` kwarg is passed
        # (mcp/server/transport_security.py) — independent of, and unaffected by,
        # the TrustedHostMiddleware added below. Remote clients (Tailscale IP, LAN
        # IP) got a hard 421 "Invalid Host header" no matter what --host/--port
        # uvicorn bound to. Disabling DNS-rebinding protection here is acceptable:
        # this server has no browser-facing surface, only direct MCP clients on
        # Tailscale/segregated internal networks.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        instructions=(
            "Raven multi-vault wiki MCP server. Before doing any work in a vault, "
            "call wiki_get_guide(vault=<name>, kind='_meta/agents/PROJECT-WORKFLOW.md') "
            "and then kind='_meta/agents/SCHEMA.md' to learn that vault's conventions — "
            "do not read those files from the filesystem directly. "
            f"Registered vaults: {', '.join(vault_names) or '(none)'}."
        ),
    )
    register_tools(mcp, args.mode)
    register_resources(mcp)

    if args.transport == "stdio":
        # Default: local in-process transport for desktop / local clients.
        mcp.run()
    else:
        # streamable-http for Tailscale/LAN-bound remote access.
        # 421 회피는 FastMCP() 생성 시 transport_security로 처리 (위 참고).
        import uvicorn

        app = mcp.streamable_http_app()  # FastMCP starlette app

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
