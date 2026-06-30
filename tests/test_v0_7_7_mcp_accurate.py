"""v0.7.7+ — make dev/status MCP 정확성 회귀 가드.

사용자 (2026-06-30):
  'make dev 했는데 왜 MCP가 살아있다고 하지? pid 89254는 Codex인데'

근본 원인:
1. v0.7.3+ Makefile의 MCP background 실행 → MCP는 stdio 기반이라 background 시 stdin 닫혀서 즉시 죽음
2. make status의 `pgrep -f 'raven.mcp'`이 Codex Computer Use의 SkyComputerUseClient까지 매칭 (false positive)

v0.7.7 수정:
1. make dev에서 MCP 자동 띄우기 제거 (3 진입점만)
2. make mcp 별도 target (stdio 명시, foreground 또는 별도 terminal)
3. make status의 pgrep을 `python.*-m raven.mcp`로 정확히

회귀 가드 (v0.7.7):
  1. Makefile dev target은 MCP 자동 띄우기 ❌ (stdio 부적합)
  2. Makefile mcp target 존재 (별도 실행)
  3. Makefile status pgrep이 정확한 패턴 사용
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"


def test_makefile_dev_does_not_start_mcp() -> None:
    """make dev는 MCP 자동 띄우기 ❌ (stdio 부적합)."""
    content = MAKEFILE.read_text(encoding="utf-8")
    # dev target만 검사 (간단히 전체)
    assert "nohup env PYTHONPATH=. $(PY) -m raven.mcp" not in content, (
        "make dev must NOT auto-start MCP via nohup (stdio dies immediately)"
    )


def test_makefile_has_mcp_target() -> None:
    """make mcp 별도 target 존재 (사용자가 명시적으로 실행)."""
    content = MAKEFILE.read_text(encoding="utf-8")
    assert ".PHONY: mcp" in content, "Makefile must have '.PHONY: mcp' target"
    assert "raven.mcp" in content, "make mcp must run raven.mcp"
    # mcp는 foreground (stdio 기반)
    assert "PYTHONPATH=. $(PY) -m raven.mcp" in content, (
        "make mcp must use foreground execution (no nohup)"
    )


def test_makefile_status_pgrep_accurate() -> None:
    """make status의 pgrep은 정확한 패턴 사용 (Codex false positive ❌)."""
    content = MAKEFILE.read_text(encoding="utf-8")
    # 정확한 패턴: python.*-m raven.mcp (Codex 매칭 안 됨)
    assert "python.*-m raven\\.mcp" in content, (
        "make status must use pgrep 'python.*-m raven.mcp' "
        "(avoid Codex false positive)"
    )
    # 옛 단순 pgrep 'raven.mcp' ❌ (Codex와 매칭)
    assert "pgrep -f 'raven.mcp'" not in content, (
        "make status must NOT use bare 'pgrep -f raven.mcp' "
        "(matches Codex Computer Use)"
    )


def test_makefile_status_handles_mcp_not_running() -> None:
    """make status는 MCP 안 떠 있을 때 친절한 안내."""
    content = MAKEFILE.read_text(encoding="utf-8")
    assert "make mcp" in content, (
        "make status MCP section must suggest 'make mcp' command"
    )