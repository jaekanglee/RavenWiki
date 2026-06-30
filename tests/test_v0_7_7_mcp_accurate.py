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


def test_makefile_dev_starts_mcp_via_http() -> None:
    """v0.7.8+: make dev는 MCP를 HTTP transport로 자동 띄움 (port 8766).

    v0.7.7 이전: stdio라 background 불가 → make dev에서 MCP 빠짐.
    v0.7.8+: HTTP transport (--transport http) → background 가능 → 4 진입점 ready.
    v0.7.9+: 정확한 진입점 = raven.mcp.cli (NOT raven.mcp — 패키지 직접 실행 ❌)
    """
    content = MAKEFILE.read_text(encoding="utf-8")
    # make dev가 MCP를 HTTP로 띄움
    assert "raven.mcp.cli --transport http" in content, (
        "make dev must start MCP via 'python -m raven.mcp.cli --transport http' (correct module path)"
    )
    # 옛 잘못된 진입점 (raven.mcp 직접) ❌ — 패키지 직접 실행 불가
    assert "nohup env PYTHONPATH=. $(PY) -m raven.mcp --transport" not in content, (
        "make dev must NOT use 'raven.mcp' (no __main__.py)"
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
    """v0.7.11+: make dev가 4개 모두 띄움. status 메시지는 정확한 안내."""
    content = MAKEFILE.read_text(encoding="utf-8")
    assert "make dev" in content and "make stop" in content, (
        "make status must suggest both 'make dev' and 'make stop'"
    )