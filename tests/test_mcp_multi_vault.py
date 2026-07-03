"""test_mcp_multi_vault.py — one MCP server process serves every registered vault.

Regression guard for the raven/mcp/cli.py refactor that replaced the
server-wide `--vault` flag with a per-call `vault` (registry name) argument
on every tool/resource, mirroring raven.api.server's `/api/vaults/{name}/...`
pattern instead of pinning the whole server to a single vault at startup.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from raven.mcp.cli import register_tools
from raven.mcp.resources import register_resources


def _make_vault(root: Path, name: str, log_text: str, schema_text: str) -> Path:
    vault_dir = root / name
    vault_dir.mkdir()
    (vault_dir / "log.md").write_text(log_text, encoding="utf-8")
    agents_dir = vault_dir / "_meta" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "SCHEMA.md").write_text(schema_text, encoding="utf-8")
    return vault_dir


@pytest.fixture
def two_vaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Register two distinct vaults ("alpha", "beta") in a temp registry."""
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp_path))
    from raven.core.registry import VaultMeta, VaultRegistry

    alpha = _make_vault(tmp_path, "alpha", "## alpha entry\n", "# alpha schema\n")
    beta = _make_vault(tmp_path, "beta", "## beta entry\n", "# beta schema\n")

    reg = VaultRegistry(root=tmp_path)
    reg.add(VaultMeta(name="alpha", path=alpha))
    reg.add(VaultMeta(name="beta", path=beta))
    return alpha, beta


def _call_tool_result(mcp: FastMCP, name: str, arguments: dict):
    """Normalize `call_tool`'s return shape back to the tool's plain value.

    FastMCP returns a bare content list for scalar/dict returns but a
    `(content, {"result": ...})` tuple when the return type is a richer
    structure (e.g. `list[dict]`) — unwrap either into the original value.
    """
    result = asyncio.run(mcp.call_tool(name, arguments))
    if isinstance(result, tuple):
        _, structured = result
        return structured["result"]
    return json.loads(result[0].text)


def _read_resource_text(mcp: FastMCP, uri: str) -> str:
    contents = list(asyncio.run(mcp.read_resource(uri)))
    return contents[0].content


def test_wiki_log_routes_by_vault_name(two_vaults):
    mcp = FastMCP("wiki")
    register_tools(mcp, "read")

    alpha_lines = _call_tool_result(mcp, "wiki_log", {"vault": "alpha", "tail_n": 5})
    beta_lines = _call_tool_result(mcp, "wiki_log", {"vault": "beta", "tail_n": 5})

    assert any("alpha entry" in d["line"] for d in alpha_lines)
    assert not any("alpha entry" in d["line"] for d in beta_lines)
    assert any("beta entry" in d["line"] for d in beta_lines)


def test_wiki_schema_resource_routes_by_vault_name(two_vaults):
    mcp = FastMCP("wiki")
    register_resources(mcp)

    alpha_text = _read_resource_text(mcp, "wiki://alpha/schema")
    beta_text = _read_resource_text(mcp, "wiki://beta/schema")

    assert "alpha schema" in alpha_text
    assert "beta schema" in beta_text


def test_wiki_update_only_touches_the_named_vault(two_vaults):
    alpha, beta = two_vaults
    # type: concept required — two_vaults' _meta/agents/SCHEMA.md makes both
    # vaults is_llm_wiki=True, so contracts.write_page enforces valid
    # frontmatter type on non-WIP pages (raven/core/contracts.py's
    # validate_gardening_schema).
    (alpha / "page.md").write_text("---\ntitle: p\ntype: concept\n---\n\noriginal\n", encoding="utf-8")
    (beta / "page.md").write_text("---\ntitle: p\ntype: concept\n---\n\noriginal\n", encoding="utf-8")

    mcp = FastMCP("wiki")
    register_tools(mcp, "write")

    asyncio.run(mcp.call_tool(
        "wiki_update", {"vault": "alpha", "slug": "page", "content": "changed"},
    ))

    assert "changed" in (alpha / "page.md").read_text(encoding="utf-8")
    assert "original" in (beta / "page.md").read_text(encoding="utf-8")
    assert "changed" not in (beta / "page.md").read_text(encoding="utf-8")


def test_unknown_vault_name_raises_clear_error(two_vaults):
    mcp = FastMCP("wiki")
    register_tools(mcp, "read")

    with pytest.raises(ToolError) as excinfo:
        asyncio.run(mcp.call_tool("wiki_log", {"vault": "nope"}))

    message = str(excinfo.value)
    assert "nope" in message
    assert "alpha" in message
    assert "beta" in message
