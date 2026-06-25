"""Tests for wikisys.core.lint — v0.5.0+ log_size check (#12 of 12).

카파시 가이드: log.md > 500 entries → info (rotation 권장).
"""
from __future__ import annotations

import sys
import shutil
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wikisys.core.lint import LOG_ROTATE_THRESHOLD, check_log_size
from wikisys.core.log import append
from wikisys.core.vault import Vault


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="wikisys-lint-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="wikisys-lint-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("lint-test", target_root / "lint-test", bootstrap=False)
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def test_log_size_below_threshold(vault):
    """499 entries → info 0."""
    for i in range(LOG_ROTATE_THRESHOLD - 1):
        append(vault, "chore", f"entry {i}")
    result = check_log_size(vault)
    assert result["info"] == 0
    assert result["needs_rotate"] is False
    assert result["entries"] == LOG_ROTATE_THRESHOLD - 1


def test_log_size_at_threshold(vault):
    """500 entries → info 1, needs_rotate True."""
    for i in range(LOG_ROTATE_THRESHOLD):
        append(vault, "chore", f"entry {i}")
    result = check_log_size(vault)
    assert result["info"] == 1
    assert result["needs_rotate"] is True
    assert result["entries"] == LOG_ROTATE_THRESHOLD


def test_log_size_no_log_file(vault):
    """log.md 없으면 info 0 (bootstrap이 알아서 만듦)."""
    result = check_log_size(vault)
    assert result["info"] == 0
    assert result["exists"] is False
    assert result["entries"] == 0


def test_log_size_above_threshold(vault):
    """600 entries → 여전히 info 1 (1개 권고)."""
    for i in range(600):
        append(vault, "chore", f"entry {i}")
    result = check_log_size(vault)
    assert result["info"] == 1
    assert result["entries"] == 600
