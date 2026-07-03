"""AGENTS.md §15 ↔ PROJECT-WORKFLOW.md §10 "자가 평가 기준" 동기화 회귀 가드.

두 문서는 Tier1(raven 코드베이스)/Tier2(vault로 복사되는 템플릿) 각각에서
동일한 "에이전트 자가 평가 기준" 섹션을 의도적으로 거의 통째 복제 유지한다
(Tier2는 raven 소스 접근 없이도 자기완결적이어야 하므로).

실제로 한쪽만 갱신되고 다른 쪽이 stale 해지는 사고가 있었다 — v0.7.44에서
type taxonomy가 issue 포함 9종으로 통일됐지만 AGENTS.md §15는 "8종"으로
남아 있었음. 이 테스트는 그 재발을 잡는다. SCHEMA.md의 실제 canonical
개수에는 의존하지 않고, 두 문서가 "서로" 같은 숫자/문구를 말하는지만 본다
— canonical 값 자체가 바뀌어도(예: 신규 type 추가) 이 테스트는 두 문서가
함께 갱신됐는지만 확인한다.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"
WORKFLOW = ROOT / "raven/core/templates/agent/PROJECT-WORKFLOW.md"

AGENTS_HEADER = "## 15. 에이전트 자가 평가 기준"
WORKFLOW_HEADER = "## 🤖 10. 에이전트 자가 평가 기준"


def _section(path: Path, header: str) -> str:
    text = path.read_text(encoding="utf-8")
    assert header in text, f"{path.name} missing expected header: {header!r}"
    return text.split(header, 1)[1]


def test_type_taxonomy_count_matches_between_agents_and_workflow() -> None:
    agents_section = _section(AGENTS, AGENTS_HEADER)
    workflow_section = _section(WORKFLOW, WORKFLOW_HEADER)

    # "N종 타입"만 본다 — lite bootstrap 5종, Diátaxis 4종 등 무관한 "N종"
    # 표현과 섞이지 않도록 '타입'과 함께 등장하는 패턴만 매칭.
    agents_counts = set(re.findall(r"(\d+)종\s*타입", agents_section))
    workflow_counts = set(re.findall(r"(\d+)종\s*타입", workflow_section))

    assert agents_counts, "AGENTS.md §15 must mention 'N종 타입'"
    assert workflow_counts, "PROJECT-WORKFLOW.md §10 must mention 'N종 타입'"
    assert agents_counts == workflow_counts, (
        f"type 종수 불일치: AGENTS.md §15={agents_counts}, "
        f"PROJECT-WORKFLOW.md §10={workflow_counts} — 한쪽만 갱신됨 "
        "(SCHEMA.md 기준 실제 canonical 개수로 둘 다 맞춰야 함)"
    )


def test_karpathy_hermes_principles_present_in_both() -> None:
    agents_section = _section(AGENTS, AGENTS_HEADER)
    workflow_section = _section(WORKFLOW, WORKFLOW_HEADER)

    principles = (
        "Think Before Searching",
        "Surgical Retrieval",
        "Goal-Driven Knowledge Extraction",
        "Root-Cause Investigation",
    )
    for p in principles:
        assert p in agents_section, f"AGENTS.md §15 missing principle: {p}"
        assert p in workflow_section, f"PROJECT-WORKFLOW.md §10 missing principle: {p}"


def test_storage_decision_four_signals_phrase_matches() -> None:
    agents_section = _section(AGENTS, AGENTS_HEADER)
    workflow_section = _section(WORKFLOW, WORKFLOW_HEADER)

    phrase = "저장 결정 4가지 신호(재사용성, 인수인계, 맥락 추적, 실패 기록)"
    assert phrase in agents_section, f"AGENTS.md §15 missing exact phrase: {phrase!r}"
    assert phrase in workflow_section, (
        f"PROJECT-WORKFLOW.md §10 missing exact phrase: {phrase!r}"
    )
