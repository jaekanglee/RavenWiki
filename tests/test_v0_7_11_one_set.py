"""v0.7.11+ — `make dev` one-command = 풀세트 (4 진입점 일괄).

사용자 (2026-06-30):
  '하나의 패키지 처럼 세트로 올렸다 내렸다 하고싶거둔. 따로 관리하기 너무 복잡하잖아'

v0.7.11 정책:
  - make dev = backend 3개 + MCP stdio 모두 한 명령 (background + setsid for stdio)
  - make stop = 4개 모두 종료
  - CLI는 손대지 않음 (make raven ARGS="..." 또는 직접 python -m raven.cli)
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"


def test_make_dev_starts_all_4_entries() -> None:
    """make dev = API + MCP HTTP + MCP stdio + Dashboard 모두 띄움."""
    content = MAKEFILE.read_text(encoding="utf-8")
    # 1. API
    assert "raven.api --host $(HOST) --port 8765" in content, \
        "make dev must start API"
    # 2. MCP HTTP
    assert "raven.mcp.cli --transport http --host $(HOST) --port 8766" in content, \
        "make dev must start MCP HTTP"
    # 3. MCP stdio (setsid + background)
    assert "raven.mcp.cli --transport stdio" in content, \
        "make dev must start MCP stdio"
    assert "setsid" in content, \
        "make dev must use setsid for stdio (detached from make wrapper)"
    # 4. Dashboard
    assert "cd dashboard && nohup npm run dev" in content, \
        "make dev must start Dashboard"


def test_make_status_checks_all_4() -> None:
    """make status = API/Dashboard/MCP HTTP/MCP stdio 모두 표시."""
    content = MAKEFILE.read_text(encoding="utf-8")
    # status target 추출 (대략 grep)
    assert "API (8765)" in content
    assert "Dashboard (5173)" in content
    assert "MCP HTTP (8766)" in content, \
        "make status must show MCP HTTP section"
    assert "MCP stdio" in content, \
        "make status must show MCP stdio section"


def test_stop_dev_kills_all_4() -> None:
    """make stop-dev = 4개 모두 종료."""
    content = MAKEFILE.read_text(encoding="utf-8")
    # stop-dev에 port 8766 (MCP HTTP) 포함
    assert "lsof -ti :8766 2>/dev/null" in content or "ti :8766" in content, \
        "stop-dev must include port 8766 (MCP HTTP)"
    # stop-dev에 MCP stdio 패턴 포함
    assert "raven.mcp.cli" in content, \
        "stop-dev must include MCP process pattern (HTTP + stdio)"


def test_make_dev_one_command_full_set() -> None:
    """make dev = one command = full set (사용자 원안)."""
    content = MAKEFILE.read_text(encoding="utf-8")
    # 헤더 docstring에 "one command" 명시
    assert "one command" in content.lower(), \
        "Makefile dev header must indicate 'one command' semantics"
    # "full set" 또는 "one command" 메시지 출력
    assert "full set" in content or "one command" in content


def test_cli_not_in_make_dev() -> None:
    """CLI는 make dev에서 띄우지 않음 (on-demand)."""
    content = MAKEFILE.read_text(encoding="utf-8")
    # dev target이 'raven.cli' 또는 'make raven' 자동 실행 안 함
    # 단, 안내 메시지("make raven ARGS=")는 OK
    import re
    # dev target 안의 자동 실행 패턴 검색
    dev_match = re.search(r"^\.PHONY: dev\s*\n(.*?)(?=\n\.PHONY:|\Z)", content, re.DOTALL | re.MULTILINE)
    assert dev_match is not None, "dev target not found"
    dev_block = dev_match.group(1)
    # 자동 실행 패턴 ❌ (안내 메시지 OK)
    auto_patterns = [
        r"@make raven ",
        r"@\$\(PY\) -m raven\.cli",
    ]
    for pat in auto_patterns:
        assert not re.search(pat, dev_block), \
            f"dev target must NOT auto-execute CLI (pattern: {pat})"