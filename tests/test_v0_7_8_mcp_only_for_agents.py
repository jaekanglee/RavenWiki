"""v0.7.8+ — MCP = 에이전트 단일 통로 회귀 가드.

사용자 정정 (2026-06-30):
  'MCP가 에이전트를 위한 프로토콜이잖아'
  '에이전트가 API호출을 다이렉트로 하는게 아니라, MCP만을 바라보게 하고싶은거야'

v0.7.8 정책:
  - 사람: 3개 진입 자유 (Dashboard / CLI / API 직접)
  - 에이전트: MCP 단일 (Python adapter ❌, API 직접 ❌)
  - write 경로: 단일 (API → Raven core → vault)

회귀 가드 (v0.7.8+):
  1. README.md "단일 에이전트" 행: "MCP 단일" 명시
  2. AGENTS.md §3 사용자 3종 표: "에이전트 = MCP 표준" 명시
  3. AGENTS.md §5.5: MCP = 에이전트 표준 프로토콜 (v0.7.8+) 섹션 추가
  4. AGENTS.md §3 다음 줄: "에이전트 ↔ Raven 인터페이스 = MCP만 (단일 표준)" 명시
  5. _meta/diagrams/three-flows: 에이전트 = MCP only 강조
  6. (v0.7.9+) raven/agents/ 모듈 제거됨
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
AGENTS = ROOT / "AGENTS.md"
DIAGRAM_TXT = ROOT / "_meta" / "diagrams" / "three-flows.txt"


def test_readme_agent_mcp_only() -> None:
    """README.md 단일 에이전트 행: MCP 단일 명시."""
    content = README.read_text(encoding="utf-8")
    assert "단일 에이전트" in content
    # "Python adapter" 단독 표현 ❌ (에이전트 진입점에)
    # "MCP :8766" 또는 "MCP가 표준" 명시
    assert "MCP :8766" in content or "MCP가 표준" in content, (
        "README.md must indicate MCP as the agent entry point"
    )
    assert "raven/agents/" not in content, (
        "README.md must not mention removed raven/agents/ path"
    )


def test_agents_md_agent_mcp_only() -> None:
    """AGENTS.md §3 사용자 3종: 에이전트 = MCP 표준."""
    content = AGENTS.read_text(encoding="utf-8")
    # v0.7.8+ 정책 박힘 확인
    assert "MCP 표준" in content or "MCP만" in content, (
        "AGENTS.md must indicate MCP as the agent standard"
    )
    # §5.5 섹션
    assert "5.5" in content, "AGENTS.md must have §5.5 MCP = 에이전트 표준"
    assert "표준" in content


def test_agents_md_python_adapter_deprecated_for_agent() -> None:
    """Python adapter는 사람/스크립트 보조 (에이전트 ❌)."""
    content = AGENTS.read_text(encoding="utf-8")
    # "에이전트가 우리 API 직접 호출 ❌" 명시
    assert "에이전트가 우리 API 직접 호출" in content or "API 직접 ❌" in content, (
        "AGENTS.md must explicitly mark 'API 직접 호출' ❌ for agents"
    )


def test_three_flows_diagram_mcp_only() -> None:
    """다이어그램 three-flows.txt: 에이전트 = MCP 단일 명시."""
    content = DIAGRAM_TXT.read_text(encoding="utf-8")
    # "에이전트: MCP 단일" 또는 "MCP 단일" 박힘
    assert "MCP 단일" in content, \
        "three-flows.txt must indicate MCP single (에이전트 표준)"
    # "Python adapter ❌" 명시
    assert "Python adapter ❌" in content, \
        "three-flows.txt must mark Python adapter ❌ for agents"


def test_raven_agents_module_removed() -> None:
    """v0.7.9+: raven/agents/ 모듈 제거됨 (Python adapter deprecated).

    사용자 정정 (2026-06-30):
      'deprecated면 지금 날려도 되지않아?'

    → raven.agents = 제거. 에이전트는 MCP only.
    """
    agents_dir = ROOT / "raven" / "agents"
    assert not agents_dir.exists(), (
        f"raven/agents/ should NOT exist (v0.7.9+ removed). "
        f"Use MCP for agent interface (see AGENTS.md §5.5)."
    )
    # test_agent.py도 삭제
    test_agent = ROOT / "tests" / "test_agent.py"
    assert not test_agent.exists(), (
        "tests/test_agent.py should NOT exist (raven.agents removed)"
    )


def test_no_python_adapter_imports_in_user_paths() -> None:
    """v0.7.9+: raven/agents/ import ❌ (라이브러리 코드/user guide/CLI)."""
    import subprocess
    # 라이브러리 코드 + 진입점 검색
    r = subprocess.run(
        ["grep", "-rln", "--include=*.py", "from raven.agents", "raven/"],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    if r.stdout.strip():
        # raven.agents 모듈이 없으면 import는 다 실패 (테스트 의미 없음)
        # 모듈이 없으면 grep 결과 0건 → 빈 stdout → 정상
        pytest.fail(
            f"raven/agents/ import in 라이브러리 코드: {r.stdout}"
        )


def test_agents_md_mcp_protocol_reasons() -> None:
    """AGENTS.md §5.5: MCP = 표준 protocol의 4가지 이유 (표준화/Discovery/schema/권한) 명시."""
    content = AGENTS.read_text(encoding="utf-8")
    for keyword in ("표준화", "Discovery", "schema", "권한"):
        assert keyword in content, (
            f"AGENTS.md §5.5 must explain MCP rationale keyword '{keyword}'"
        )
