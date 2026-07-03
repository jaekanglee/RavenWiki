"""test_mcp_multi_vault.py — one MCP server process serves every registered vault.

Regression guard for the raven/mcp/cli.py refactor that replaced the
server-wide `--vault` flag with a per-call `vault` (registry name) argument
on every tool/resource, mirroring raven.api.server's `/api/vaults/{name}/...`
pattern instead of pinning the whole server to a single vault at startup.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from raven.mcp.tools.read import wiki_log, wiki_get_page
from raven.mcp.tools.write import wiki_update
from raven.mcp.resources import wiki_schema
from raven.core.registry import VaultMeta, VaultRegistry


def _make_vault(root: Path, name: str, log_text: str, schema_text: str) -> Path:
    vault_dir = root / name
    vault_dir.mkdir()
    (vault_dir / "log.md").write_text(log_text, encoding="utf-8")
    (vault_dir / "SCHEMA.md").write_text(schema_text, encoding="utf-8")
    return vault_dir


@pytest.fixture
def two_vaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Register two distinct vaults ("alpha", "beta") in a temp registry."""
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp_path))

    alpha = _make_vault(tmp_path, "alpha", "## alpha entry\n", "# alpha schema\n")
    beta = _make_vault(tmp_path, "beta", "## beta entry\n", "# beta schema\n")

    reg = VaultRegistry(root=tmp_path)
    reg.add(VaultMeta(name="alpha", path=alpha))
    reg.add(VaultMeta(name="beta", path=beta))
    return alpha, beta


def test_wiki_log_routes_by_vault_name(two_vaults):
    alpha_lines = wiki_log(vault="alpha", tail_n=5)
    beta_lines = wiki_log(vault="beta", tail_n=5)

    assert any("alpha entry" in d["line"] for d in alpha_lines)
    assert not any("alpha entry" in d["line"] for d in beta_lines)
    assert any("beta entry" in d["line"] for d in beta_lines)


def test_wiki_schema_resource_routes_by_vault_name(two_vaults):
    alpha_text = wiki_schema(vault="alpha")
    beta_text = wiki_schema(vault="beta")

    assert "alpha schema" in alpha_text
    assert "beta schema" in beta_text


def test_wiki_update_only_touches_the_named_vault(two_vaults):
    alpha, beta = two_vaults
    (alpha / "page.md").write_text("---\ntitle: p\n---\n\noriginal\n", encoding="utf-8")
    (beta / "page.md").write_text("---\ntitle: p\n---\n\noriginal\n", encoding="utf-8")

    wiki_update(vault="alpha", slug="page", content="changed")

    assert "changed" in (alpha / "page.md").read_text(encoding="utf-8")
    assert "original" in (beta / "page.md").read_text(encoding="utf-8")
    assert "changed" not in (beta / "page.md").read_text(encoding="utf-8")


def test_unknown_vault_name_raises_clear_error(two_vaults):
    with pytest.raises(ValueError) as excinfo:
        wiki_log(vault="nope", tail_n=5)

    message = str(excinfo.value)
    assert "nope" in message
    assert "alpha" in message
    assert "beta" in message