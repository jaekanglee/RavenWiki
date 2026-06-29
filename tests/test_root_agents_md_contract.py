"""v0.6.35+ — root AGENTS.md 보강 회귀 가드.

사용자 보강 요청 (2026-06-30): Raven 루트 AGENTS.md + 연관 개발문서.
- §0.5: North Star 한 줄 + "이 레포는 LLM Wiki self-host" 선언
- §4.5: audience 라우팅 표 (3 독자 → 3 문서)
- §14: _meta/ SOT 인덱스 표
- frontmatter `updated: 2026-06-30`

회귀 가드:
  1. frontmatter updated 필드 2026-06-30
  2. §0.5 North Star 키워드 (compounding knowledge / Karpathy LLM Wiki)
  3. §4.5 audience 표 헤더 (사람 / Raven 개발팀 / LLM agent)
  4. §14 _meta/ 인덱스 표 헤더
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"


def test_agents_md_frontmatter_updated() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    # updated: 2026-06-30 (또는 그 이후)
    m = re.search(r"^updated:\s*(\d{4}-\d{2}-\d{2})", text, re.MULTILINE)
    assert m, "AGENTS.md frontmatter missing 'updated:'"
    assert m.group(1) >= "2026-06-30", \
        f"AGENTS.md stale (updated={m.group(1)}, expected >=2026-06-30)"


def test_agents_md_section_0_5_north_star() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert "## 0.5" in text, "AGENTS.md missing §0.5 (North Star)"
    assert "Karpathy LLM Wiki" in text, \
        "§0.5 must cite 'Karpathy LLM Wiki' as origin"
    assert "compounding knowledge" in text, \
        "§0.5 must state 'compounding knowledge' north star"


def test_agents_md_section_4_5_audience_table() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert "## 4.5" in text, "AGENTS.md missing §4.5 (audience routing)"
    # 3 audience 행: 사람 / Raven 개발팀 / LLM agent
    assert "사람" in text.split("## 4.5")[1].split("## 5.")[0], \
        "§4.5 must mention 사람 audience"
    assert "LLM agent" in text or "에이전트" in text, \
        "§4.5 must mention LLM agent audience"


def test_agents_md_section_14_meta_index() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert "## 14" in text, "AGENTS.md missing §14 (_meta/ index)"
    # _meta/ SOT 파일들 인덱스
    section_14 = text.split("## 14")[1]
    for key_file in ("SCHEMA.md", "RULES.md", "decisions/adr-", "ai-roadmap", "raven-architecture"):
        assert key_file in section_14, \
            f"§14 must reference {key_file}"


def test_agents_md_no_force_push_directive_changed() -> None:
    """§10 '하지 말 것' 의 force push ❌ 는 유지되어야 함 (회귀 가드)."""
    text = AGENTS.read_text(encoding="utf-8")
    assert "force push" in text, "AGENTS.md §10 force-push rule missing"
    assert "❌" in text.split("## 10")[1].split("## 11")[0], \
        "§10 still has ❌ markers"