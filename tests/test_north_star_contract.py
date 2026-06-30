"""v0.6.37+ — North Star 재정렬 회귀 가드.

v0.6.31~36은 'Karpathy LLM Wiki self-host 구현체' 톤으로 박혀 있었음.
v0.6.37에서 사용자 north star 재정렬:
  - 기본 정체성 = Obsidian 대체 자체 구현체 (사람 1차, 자유)
  - LLM Wiki = vault 안 +α 옵션 (강제 ❌)
  - Karpathy = 영감/출발점 (필수 인용 아님)

회귀 가드 (v0.6.37):
  1. README에 "## North Star" 헤더
  2. README에 새 north star 한 줄 ("사람을 1차 사용자로")
  3. README에 "Obsidian" 모티브 명시
  4. README에 "+α" 또는 "opt-in" 표현 (LLM Wiki 강제 아님)
  5. wikisys-policy.md에 "## North Star" 헤더
  6. wikisys-policy.md에 새 north star 한 줄
  7. 분업 (사람 source curate) 명시
  8. "컴파일 후 reuse" (v0.6.31 톤 보존)
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
POLICY = ROOT / "raven" / "core" / "templates" / "wikisys-policy.md"


def test_readme_has_north_star_header() -> None:
    content = README.read_text(encoding="utf-8")
    assert "## North Star" in content, "README missing '## North Star' header"


def test_readme_states_human_first() -> None:
    content = README.read_text(encoding="utf-8")
    assert "사람을 1차 사용자로" in content, \
        "README must state '사람을 1차 사용자로' (v0.6.37 human-first north star)"
    assert "Obsidian" in content, \
        "README must mention Obsidian as base motivation"


def test_readme_states_llm_wiki_as_optional_alpha() -> None:
    content = README.read_text(encoding="utf-8")
    has_optional = any(kw in content for kw in (
        "LLM Wiki 패턴은 vault 안에서 +α",
        "+α로 켜",
        "원하는 vault 영역에만",
    ))
    assert has_optional, \
        "README must state LLM Wiki as optional +α (not mandatory)"


def test_readme_states_compile_reuse_not_rebuild() -> None:
    content = README.read_text(encoding="utf-8")
    assert "컴파일 후 reuse" in content, \
        "README must state '컴파일 후 reuse'"
    assert "매번 재구성" in content, \
        "README must contrast '매번 재구성 ❌'"


def test_policy_has_north_star_header() -> None:
    content = POLICY.read_text(encoding="utf-8")
    assert "## North Star" in content, "wikisys-policy.md missing '## North Star' header"


def test_policy_states_human_first() -> None:
    content = POLICY.read_text(encoding="utf-8")
    assert "사람을 1차 사용자로" in content, \
        "wikisys-policy.md must state '사람을 1차 사용자로' (v0.6.37)"


def test_policy_states_llm_wiki_as_optional_alpha() -> None:
    content = POLICY.read_text(encoding="utf-8")
    has_optional = "+α" in content and "원하면" in content
    assert has_optional, \
        "wikisys-policy.md must state LLM Wiki as optional +α with '원하면'"


def test_policy_mentions_division_of_labor() -> None:
    content = POLICY.read_text(encoding="utf-8")
    # 사람 source curate + 에이전트 (조건부) compile 분업 명시
    assert "사람" in content, "wikisys-policy.md must mention 사람"
    assert "에이전트" in content, "wikisys-policy.md must mention 에이전트"
    assert "compile" in content, "wikisys-policy.md must mention compile"