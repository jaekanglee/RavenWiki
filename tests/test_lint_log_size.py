"""Tests for raven.core.lint — v0.5.1+ log_size check (#12 of 12, 회귀).

카파시 가이드: log.md > 500 entries → info (rotation 권장).
v0.5.1+: check_log_size는 list[dict] (issue 리스트) 반환.
"""
from __future__ import annotations

import sys
import shutil
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core.lint import LOG_ROTATE_THRESHOLD, check_log_size
from raven.core.log import append
from raven.core.vault import Vault


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-lint-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-lint-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("lint-test", target_root / "lint-test", bootstrap=False)
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def test_log_size_below_threshold(vault):
    """499 entries → info 0."""
    for i in range(LOG_ROTATE_THRESHOLD - 1):
        append(vault, "chore", f"entry {i}")
    issues = check_log_size(vault)
    assert issues == []


def test_log_size_at_threshold(vault):
    """500 entries → info 1."""
    for i in range(LOG_ROTATE_THRESHOLD):
        append(vault, "chore", f"entry {i}")
    issues = check_log_size(vault)
    assert len(issues) == 1
    assert issues[0]["id"] == "#12"
    assert issues[0]["severity"] == "info"
    assert "500" in issues[0]["message"]


def test_log_size_no_log_file(vault):
    """log.md 없으면 빈 리스트."""
    issues = check_log_size(vault)
    assert issues == []


def test_log_size_above_threshold(vault):
    """600 entries → 1개 info."""
    for i in range(600):
        append(vault, "chore", f"entry {i}")
    issues = check_log_size(vault)
    assert len(issues) == 1
    assert issues[0]["id"] == "#12"
