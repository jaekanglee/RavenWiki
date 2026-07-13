"""raven docs list/show가 CURATION.md(agent-curation topic)을 노출하는지 검증.

배경: raven/core/templates/agent/CURATION.md는 작성됐지만 docs_show의
topic_map에도, vault bootstrap의 LITE_BOOTSTRAP_FILE_MAP에도 연결되지
않아 어떤 경로로도 도달 불가능한 고아 파일이었다 (2026-07-13 스펙).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from typer.testing import CliRunner

from raven.cli.__main__ import app
from raven.core.vault import LITE_BOOTSTRAP_FILE_MAP, Vault

runner = CliRunner()


def test_docs_list_includes_agent_curation():
    result = runner.invoke(app, ["docs", "list"])
    assert result.exit_code == 0, result.stdout
    assert "agent-curation" in result.stdout


def test_docs_show_agent_curation_prints_file_content():
    result = runner.invoke(app, ["docs", "show", "agent-curation"])
    assert result.exit_code == 0, result.stdout
    assert "Vault Curation" in result.stdout


def test_docs_show_unknown_topic_lists_agent_curation_as_valid_choice():
    result = runner.invoke(app, ["docs", "show", "no-such-topic"])
    assert result.exit_code == 1
    combined = result.stdout + (result.stderr or "")
    assert "agent-curation" in combined


def test_curation_not_in_lite_bootstrap_file_map():
    """CURATION.md는 docs_show 전용 — vault에 자동 복사되면 안 된다."""
    assert "_meta/agents/CURATION.md" not in LITE_BOOTSTRAP_FILE_MAP


def test_vault_create_does_not_copy_curation_md(monkeypatch):
    vaults_root = Path(tempfile.mkdtemp(prefix="raven-curation-vaults-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-curation-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(vaults_root))
    try:
        v = Vault.create("curation-test", target_root / "curation-test", bootstrap=True)
        assert not (v.root / "_meta" / "agents" / "CURATION.md").exists()
    finally:
        shutil.rmtree(vaults_root, ignore_errors=True)
        shutil.rmtree(target_root, ignore_errors=True)
