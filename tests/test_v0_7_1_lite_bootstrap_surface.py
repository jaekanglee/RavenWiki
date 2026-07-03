"""v0.7.65+ — Lite bootstrap 2-file agent-only surface 회귀 가드.

v0.7.65 재설계: `_meta/system/{SCHEMA,RULES,README}.md` (3개) →
`_meta/agents/SCHEMA.md` (데이터 계약) + `_meta/agents/PROJECT-WORKFLOW.md`
(운영 사실) 2개로 병합. 사람 안내 톤 제거, 다른 에이전트 프로필의 자가평가
기준(Hermes Constitution) 제거, "이 문서에 없는 것" 경계 선언 추가.

회귀 가드:
  1. 옛 `_meta/system/{SCHEMA,RULES,README}.md` 템플릿 파일이 존재하지 않음
  2. 새 SCHEMA.md에 vendor 예시 / 도메인 가정(karpathy) 0회
  3. 새 SCHEMA.md가 데이터 계약 핵심 내용을 포함 (type 9종, wikilink, raw 권한)
  4. 새 PROJECT-WORKFLOW.md에 vendor 예시 / Hermes Constitution 0회
  5. 새 PROJECT-WORKFLOW.md가 운영 사실 핵심 내용을 포함 (MCP 매핑, 저장 신호 4가지, 체크리스트)
  6. 새 PROJECT-WORKFLOW.md에 "이 문서에 없는 것" 경계 선언 존재
  7. PROJECT-WORKFLOW.md는 templates/agent/ 한 곳에만 존재
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_SYSTEM_SCHEMA = ROOT / "raven" / "core" / "templates" / "system" / "SCHEMA.md"
OLD_SYSTEM_RULES = ROOT / "raven" / "core" / "templates" / "system" / "RULES.md"
OLD_SYSTEM_README = ROOT / "raven" / "core" / "templates" / "system" / "README.md"
NEW_SCHEMA = ROOT / "raven" / "core" / "templates" / "agent" / "SCHEMA.md"
NEW_PROJECT_WORKFLOW = ROOT / "raven" / "core" / "templates" / "agent" / "PROJECT-WORKFLOW.md"

FORBIDDEN_VENDORS = ("Codex", "Claude Code", "Cursor", "Antigravity", "agy")
FORBIDDEN_AGENT_SOUL_TERMS = ("Hermes Constitution", "자가 평가 기준", "Self-Evaluation")


def _assert_no_terms(content: str, terms: tuple, file_label: str) -> None:
    for term in terms:
        assert term not in content, (
            f"{file_label} has forbidden term '{term}'"
        )


def test_old_system_lite_files_removed() -> None:
    assert not OLD_SYSTEM_SCHEMA.exists(), "old system/SCHEMA.md must be removed (merged into agent/SCHEMA.md)"
    assert not OLD_SYSTEM_RULES.exists(), "old system/RULES.md must be removed (merged into agent/SCHEMA.md)"
    assert not OLD_SYSTEM_README.exists(), "old system/README.md must be removed (merged into agent/PROJECT-WORKFLOW.md)"


def test_new_schema_no_vendor_or_domain_assumptions() -> None:
    content = NEW_SCHEMA.read_text(encoding="utf-8")
    _assert_no_terms(content, FORBIDDEN_VENDORS, "agent/SCHEMA.md")
    _assert_no_terms(content, ("karpathy", "Karpathy"), "agent/SCHEMA.md")


def test_new_schema_has_data_contract_content() -> None:
    content = NEW_SCHEMA.read_text(encoding="utf-8")
    assert "Type Taxonomy" in content
    for t in ("concept", "person", "comparison", "project", "tool", "rule", "query", "journal", "issue"):
        assert t in content
    assert "wikilink" in content.lower()
    assert "raw/ 권한" in content
    assert "페이지 템플릿" in content


def test_new_project_workflow_no_vendor_or_agent_soul_content() -> None:
    content = NEW_PROJECT_WORKFLOW.read_text(encoding="utf-8")
    _assert_no_terms(content, FORBIDDEN_VENDORS, "agent/PROJECT-WORKFLOW.md")
    _assert_no_terms(content, FORBIDDEN_AGENT_SOUL_TERMS, "agent/PROJECT-WORKFLOW.md")


def test_new_project_workflow_has_operating_facts() -> None:
    content = NEW_PROJECT_WORKFLOW.read_text(encoding="utf-8")
    assert "MCP 도구" in content
    assert "재사용 가능성" in content
    assert "인수인계 필요성" in content
    assert "결정 근거" in content
    assert "실패/리스크 기록" in content
    assert "체크리스트" in content
    assert "BLUF" in content


def test_new_project_workflow_has_boundary_declaration() -> None:
    content = NEW_PROJECT_WORKFLOW.read_text(encoding="utf-8")
    assert "이 문서에 없는 것" in content
    assert "검색 판단" in content
    assert "정리/폐기 판단" in content


def test_project_workflow_is_only_in_agent_template() -> None:
    agents_plural_dir = ROOT / "raven" / "core" / "templates" / "agents"  # 옛 오타 path
    assert NEW_PROJECT_WORKFLOW.exists(), f"{NEW_PROJECT_WORKFLOW} not found"
    assert not agents_plural_dir.exists(), f"{agents_plural_dir} should NOT exist (path consolidation)"
