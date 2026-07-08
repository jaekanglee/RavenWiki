"""v0.7.114+ (ADR-2026-07-08): lint #19 guide freshness 검사."""
import json
from pathlib import Path

import pytest


def _write_agents(tmp_vault: Path, schema_content: str = "# SCHEMA\n", pww_content: str = "# PWW\n") -> None:
    agents = tmp_vault / "_meta" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "SCHEMA.md").write_text(schema_content, encoding="utf-8")
    (agents / "PROJECT-WORKFLOW.md").write_text(pww_content, encoding="utf-8")


def _write_stamp(tmp_vault: Path, stamp: dict) -> None:
    p = tmp_vault / "_meta" / "agents" / ".guide-version"
    p.write_text("\n".join(f"{k}: {v}" for k, v in stamp.items()) + "\n", encoding="utf-8")


def _setup_vault(tmp_path: Path):
    from raven.core.registry import VaultMeta
    from raven.core.vault import Vault
    root = tmp_path / "v"
    (root / "content").mkdir(parents=True)
    (root / "log.md").write_text("# log\n", encoding="utf-8")
    meta = VaultMeta(name="test", path=root, mode="personal", owner="test")
    return Vault(meta=meta, root=root)


def test_lint_19_no_agents_dir(tmp_path):
    """`_meta/agents/` 부재 — info 2건 (SCHEMA + PWW 부재)."""
    from raven.core.lint import check_guide_freshness

    vault = _setup_vault(tmp_path)
    issues = check_guide_freshness(vault)
    assert len(issues) == 2
    assert all(i["severity"] == "info" for i in issues)
    assert all(i["id"] == "#19" for i in issues)


def test_lint_19_no_stamp(tmp_path):
    """부속은 있지만 stamp 없음 — info 2건 (회귀 가드)."""
    from raven.core.lint import check_guide_freshness

    vault = _setup_vault(tmp_path)
    _write_agents(vault.root)
    issues = check_guide_freshness(vault)
    assert len(issues) == 2
    assert all("stamp 없음" in i["message"] for i in issues)


def test_lint_19_stamp_fresh(tmp_path):
    """stamp == vault_hash — 0건 (정상)."""
    from raven.core.lint import check_guide_freshness
    from raven.mcp.tools.guide import _sha256

    vault = _setup_vault(tmp_path)
    _write_agents(vault.root)
    schema_hash = _sha256(vault.root / "_meta" / "agents" / "SCHEMA.md")
    pww_hash = _sha256(vault.root / "_meta" / "agents" / "PROJECT-WORKFLOW.md")
    _write_stamp(vault.root, {"SCHEMA": schema_hash, "PROJECT-WORKFLOW": pww_hash})
    issues = check_guide_freshness(vault)
    assert issues == []


def test_lint_19_stamp_stale(tmp_path):
    """stamp != vault_hash — info 2건 (stamp stale 경고)."""
    from raven.core.lint import check_guide_freshness

    vault = _setup_vault(tmp_path)
    _write_agents(vault.root)
    # stamp은 옛 hash로 박음
    _write_stamp(vault.root, {"SCHEMA": "stale_sha", "PROJECT-WORKFLOW": "stale_pww"})
    issues = check_guide_freshness(vault)
    assert len(issues) == 2
    assert all("stamp stale" in i["message"] for i in issues)
    assert all(i["severity"] == "info" for i in issues)
