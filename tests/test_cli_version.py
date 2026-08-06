"""raven --version → SOT(raven/__init__.py __version__)와 일치하는 버전 출력 검증.

v0.7.183 (톡머리 vault operator report): 설치본 CLI에 --version이 없어
CLI/MCP/DB 스키마 버전 불일치를 사용자가 감지할 수 없었다.
"""
from __future__ import annotations

import sys
from pathlib import Path

from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven import __version__ as RAVEN_VERSION
from raven.cli.__main__ import app

runner = CliRunner()


def test_version_long_flag_prints_sot_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0, result.stderr
    assert f"raven {RAVEN_VERSION}" in result.stdout


def test_version_short_flag_prints_sot_version() -> None:
    result = runner.invoke(app, ["-V"])
    assert result.exit_code == 0, result.stderr
    assert RAVEN_VERSION in result.stdout


def test_version_flag_does_not_break_subcommand() -> None:
    # --version 없이 build 명령 등은 정상 동작해야 한다 (exit 2 = usage error
    # 가 아니라 실제 vault 미설정 에러 등으로만 나가야 함).
    result = runner.invoke(app, ["build", "--help"])
    assert result.exit_code == 0, result.stderr
    assert "Rebuild wiki.db" in result.stdout
