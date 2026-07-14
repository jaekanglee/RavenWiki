"""v0.7.65+ — Lite bootstrap 2-file agent-only surface 회귀 가드.

v0.7.65 재설계: `_meta/system/{SCHEMA,RULES,README}.md` (3개) →
`_meta/agents/SCHEMA.md` (데이터 계약) + `_meta/agents/RAVEN-CONTRACT.md` (기술 계약).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_SYSTEM_SCHEMA = ROOT / "raven" / "core" / "templates" / "system" / "SCHEMA.md"
OLD_SYSTEM_RULES = ROOT / "raven" / "core" / "templates" / "system" / "RULES.md"
OLD_SYSTEM_README = ROOT / "raven" / "core" / "templates" / "system" / "README.md"
NEW_SCHEMA = ROOT / "raven" / "core" / "templates" / "agent" / "SCHEMA.md"
NEW_RAVEN_CONTRACT = ROOT / "raven" / "core" / "templates" / "agent" / "RAVEN-CONTRACT.md"

FORBIDDEN_VENDORS = ("Codex", "Claude Code", "Cursor", "Antigravity", "agy")
FORBIDDEN_AGENT_SOUL_TERMS = ("Hermes Constitution", "자가 평가 기준", "Self-Evaluation")


def _assert_no_terms(content: str, terms: tuple, file_label: str) -> None:
    for term in terms:
        assert term not in content, (
            f"{file_label} has forbidden term '{term}'"
        )


def test_old_system_lite_files_removed() -> None:
    assert not OLD_SYSTEM_SCHEMA.exists(), "old system/SCHEMA.md must be removed"
    assert not OLD_SYSTEM_RULES.exists(), "old system/RULES.md must be removed"
    assert not OLD_SYSTEM_README.exists(), "old system/README.md must be removed"


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


def test_new_raven_contract_no_vendor_or_agent_soul_content() -> None:
    content = NEW_RAVEN_CONTRACT.read_text(encoding="utf-8")
    _assert_no_terms(content, FORBIDDEN_VENDORS, "agent/RAVEN-CONTRACT.md")
    _assert_no_terms(content, FORBIDDEN_AGENT_SOUL_TERMS, "agent/RAVEN-CONTRACT.md")


def test_new_raven_contract_has_operating_facts() -> None:
    content = NEW_RAVEN_CONTRACT.read_text(encoding="utf-8")
    assert "Model Context Protocol" in content
    assert "Permission Modes" in content
    assert "Hard Path Protections" in content
    assert "Audit Records" in content
    assert "log.md" in content
    assert "Freshness Check" in content
