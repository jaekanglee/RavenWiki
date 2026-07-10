"""raven lint summary / raven lint check CLI가 CHECK_REGISTRY 23개를 전부 반영하는지 검증."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.cli.__main__ import app
from raven.core import lint as lint_module

runner = CliRunner()


@pytest.fixture
def fresh_env(monkeypatch):
    vaults_root = Path(tempfile.mkdtemp(prefix="raven-lintcli-vaults-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-lintcli-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(vaults_root))
    result = runner.invoke(app, [
        "vault", "create", "lintcli-test", str(target_root / "lintcli-test"),
        "--no-bootstrap",
    ])
    assert result.exit_code == 0, result.stderr
    yield
    shutil.rmtree(vaults_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def test_lint_summary_shows_all_registered_checks(fresh_env):
    result = runner.invoke(app, ["lint", "summary", "--vault", "lintcli-test"])
    assert result.exit_code == 0, result.stdout
    for cid in lint_module.CHECK_REGISTRY:
        assert cid in result.stdout, f"{cid} 가 lint summary 출력에 없음"


def test_lint_check_unsupported_link_based_check_gives_clear_message(fresh_env):
    result = runner.invoke(app, ["lint", "check", "#1", "--vault", "lintcli-test"])
    assert result.exit_code == 1
    assert "link_module" in result.stdout or "link_module" in result.stderr


def test_lint_check_runs_registered_function(fresh_env):
    result = runner.invoke(app, ["lint", "check", "#4", "--vault", "lintcli-test"])
    assert result.exit_code == 0, result.stdout
    assert "#4" in result.stdout
