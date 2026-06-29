"""v0.6.31+ — North Star 한 줄 선언 회귀 가드.

Karpathy LLM Wiki 본질을 README + wikisys-policy.md에 박아서 모든
운영 결정의 자석으로 사용. 둘 중 한 곳이라도 빠지면 회귀.

회귀 가드:
  1. README에 "## North Star" 헤더 + "compounding knowledge" 문구
  2. README에 "Karpathy LLM Wiki (2026)" 명시
  3. wikisys-policy.md에 "## North Star" 헤더 + "컴파일 후 reuse" 문구
  4. wikisys-policy.md에 분업 (사람/에이전트) 명시
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
POLICY = ROOT / "raven" / "core" / "templates" / "wikisys-policy.md"


def test_readme_has_north_star_header() -> None:
    content = README.read_text(encoding="utf-8")
    assert "## North Star" in content, "README missing '## North Star' header"


def test_readme_cites_karpathy_llm_wiki_2026() -> None:
    content = README.read_text(encoding="utf-8")
    assert "Karpathy LLM Wiki (2026)" in content, \
        "README must cite Karpathy LLM Wiki (2026) as origin"


def test_readme_states_compounding_knowledge() -> None:
    content = README.read_text(encoding="utf-8")
    assert "compounding knowledge" in content, \
        "README must state 'compounding knowledge' north star"


def test_readme_states_compile_reuse_not_rebuild() -> None:
    content = README.read_text(encoding="utf-8")
    assert "컴파일 후 reuse" in content, \
        "README must state '컴파일 후 reuse'"
    assert "매번 재구성" in content, \
        "README must contrast '매번 재구성 ❌'"


def test_policy_has_north_star_header() -> None:
    content = POLICY.read_text(encoding="utf-8")
    assert "## North Star" in content, \
        "wikisys-policy.md missing '## North Star' header"


def test_policy_states_compile_reuse() -> None:
    content = POLICY.read_text(encoding="utf-8")
    assert "컴파일 후 reuse" in content, \
        "wikisys-policy.md must state '컴파일 후 reuse'"


def test_policy_mentions_division_of_labor() -> None:
    content = POLICY.read_text(encoding="utf-8")
    # 사람 source curate + 에이전트 compile 분업 명시
    assert "사람" in content, "wikisys-policy.md must mention 사람"
    assert "에이전트" in content, "wikisys-policy.md must mention 에이전트"
    assert "compile" in content, "wikisys-policy.md must mention compile"