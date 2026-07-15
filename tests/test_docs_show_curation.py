"""`raven docs` exposes CURATION.md without injecting it into vaults."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from typer.testing import CliRunner

from raven.cli.__main__ import app
from raven.core.vault import Vault

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


def test_vault_create_does_not_copy_curation_md(monkeypatch):
    vaults_root = Path(tempfile.mkdtemp(prefix="raven-curation-vaults-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-curation-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(vaults_root))
    try:
        v = Vault.create("curation-test", target_root / "curation-test")
        assert not (v.root / "_meta" / "agents" / "CURATION.md").exists()
    finally:
        shutil.rmtree(vaults_root, ignore_errors=True)
        shutil.rmtree(target_root, ignore_errors=True)
