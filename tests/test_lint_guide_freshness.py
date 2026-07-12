"""v0.7.114+ (ADR-2026-07-08): lint #19 guide freshness 검사."""
import json
from pathlib import Path

import pytest


def _write_agents(tmp_vault: Path, schema_content: str = "# SCHEMA\n", pww_content: str = "# PWW\n", create_stubs: bool = True) -> None:
    from raven.core.vault import AGENT_POINTER_STUB_FILES, AGENT_POINTER_STUB_CONTENT

    agents = tmp_vault / "_meta" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "SCHEMA.md").write_text(schema_content, encoding="utf-8")
    (agents / "PROJECT-WORKFLOW.md").write_text(pww_content, encoding="utf-8")
    # v0.8.1+: Create stub files with correct content (optional)
    if create_stubs:
        for stub_name in AGENT_POINTER_STUB_FILES:
            (tmp_vault / stub_name).write_text(AGENT_POINTER_STUB_CONTENT, encoding="utf-8")


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


def test_lint_19_no_stub_check_when_pww_missing(tmp_path):
    """PROJECT-WORKFLOW.md 자체가 없으면 (basic profile 상황) 스텁 검사 skip."""
    from raven.core.lint import check_guide_freshness
    from raven.core.vault import AGENT_POINTER_STUB_FILES

    vault = _setup_vault(tmp_path)
    # _write_agents() 호출 안 함 — SCHEMA/PWW 둘 다 없는 상태
    issues = check_guide_freshness(vault)
    stub_issues = [i for i in issues if i["slug"] in AGENT_POINTER_STUB_FILES]
    assert stub_issues == []


def test_lint_19_stub_files_missing_when_pww_exists(tmp_path):
    """PWW 있고 stamp 신선하지만 스텁 파일 5개가 없음 — info 5건 추가."""
    from raven.core.lint import check_guide_freshness
    from raven.core.vault import AGENT_POINTER_STUB_FILES
    from raven.mcp.tools.guide import _sha256

    vault = _setup_vault(tmp_path)
    _write_agents(vault.root, create_stubs=False)
    schema_hash = _sha256(vault.root / "_meta" / "agents" / "SCHEMA.md")
    pww_hash = _sha256(vault.root / "_meta" / "agents" / "PROJECT-WORKFLOW.md")
    _write_stamp(vault.root, {"SCHEMA": schema_hash, "PROJECT-WORKFLOW": pww_hash})
    issues = check_guide_freshness(vault)
    stub_issues = [i for i in issues if i["slug"] in AGENT_POINTER_STUB_FILES]
    assert len(stub_issues) == len(AGENT_POINTER_STUB_FILES)
    assert all("부재" in i["message"] for i in stub_issues)


def test_lint_19_stub_files_fresh_when_content_matches(tmp_path):
    """스텁 5개가 정확한 내용으로 존재 — 스텁 관련 issue 0건."""
    from raven.core.lint import check_guide_freshness
    from raven.core.vault import AGENT_POINTER_STUB_FILES, AGENT_POINTER_STUB_CONTENT
    from raven.mcp.tools.guide import _sha256

    vault = _setup_vault(tmp_path)
    _write_agents(vault.root)
    schema_hash = _sha256(vault.root / "_meta" / "agents" / "SCHEMA.md")
    pww_hash = _sha256(vault.root / "_meta" / "agents" / "PROJECT-WORKFLOW.md")
    _write_stamp(vault.root, {"SCHEMA": schema_hash, "PROJECT-WORKFLOW": pww_hash})
    for fname in AGENT_POINTER_STUB_FILES:
        (vault.root / fname).write_text(AGENT_POINTER_STUB_CONTENT, encoding="utf-8")
    issues = check_guide_freshness(vault)
    stub_issues = [i for i in issues if i["slug"] in AGENT_POINTER_STUB_FILES]
    assert stub_issues == []


def test_lint_19_stub_file_tampered_content(tmp_path):
    """스텁 파일 내용이 변조됨 — 해당 스텁만 info 1건."""
    from raven.core.lint import check_guide_freshness
    from raven.core.vault import AGENT_POINTER_STUB_FILES, AGENT_POINTER_STUB_CONTENT
    from raven.mcp.tools.guide import _sha256

    vault = _setup_vault(tmp_path)
    _write_agents(vault.root)
    schema_hash = _sha256(vault.root / "_meta" / "agents" / "SCHEMA.md")
    pww_hash = _sha256(vault.root / "_meta" / "agents" / "PROJECT-WORKFLOW.md")
    _write_stamp(vault.root, {"SCHEMA": schema_hash, "PROJECT-WORKFLOW": pww_hash})
    for fname in AGENT_POINTER_STUB_FILES:
        (vault.root / fname).write_text(AGENT_POINTER_STUB_CONTENT, encoding="utf-8")
    (vault.root / "CLAUDE.md").write_text("변조됨\n", encoding="utf-8")
    issues = check_guide_freshness(vault)
    stub_issues = [i for i in issues if i["slug"] == "CLAUDE.md"]
    assert len(stub_issues) == 1
    assert "불일치" in stub_issues[0]["message"]
