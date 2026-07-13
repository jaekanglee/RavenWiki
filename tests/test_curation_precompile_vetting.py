"""CURATION.md의 Pre-Compile Source Vetting Checklist 섹션 회귀 가드.

기존 §1-4 내용은 문장 단위로 보존되어야 하고(번호만 밀림), 새 §1은
frontmatter 신호(status/confidence/lint 번호)만으로 판정 가능해야 한다
(2026-07-13 스펙 — 새 frontmatter 필드 발명 금지).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURATION = ROOT / "raven" / "core" / "templates" / "agent" / "CURATION.md"


def _content() -> str:
    return CURATION.read_text(encoding="utf-8")


def test_new_precompile_section_exists_as_section_1():
    content = _content()
    assert "## 1. 컴파일 전 소스 검증 체크리스트 (Pre-Compile Source Vetting)" in content


def test_precompile_section_uses_existing_signals_only():
    content = _content()
    for signal in (
        "status: contested",
        "status: archived",
        "confidence: low",
        "lint #7",
        "lint #4",
        "lint #20",
        "lint #17",
    ):
        assert signal in content, f"신호 '{signal}'이 체크리스트에 없음"


def test_precompile_section_defines_three_verdicts():
    content = _content()
    assert "⛔ 인용 금지" in content
    assert "⚠️ 캐비어 달고 인용" in content
    assert "✅ 그대로 인용" in content


def test_existing_sections_preserved_and_renumbered():
    content = _content()
    assert "## 2. 큐레이션 및 클렌징의 3대 대원칙" in content
    assert "## 3. 린트 규칙별 세부 클렌징 및 조치 가이드" in content
    assert "## 4. 변증법적 갈등 해소 (Dialectic Contradiction Resolver)" in content
    assert "## 5. 지식 계보 및 기원(Provenance) 보존" in content
    # 옛 번호는 더 이상 헤딩으로 존재하면 안 됨
    assert "## 1. 큐레이션 및 클렌징의 3대 대원칙" not in content
    assert "## 3. 변증법적 갈등 해소" not in content


def test_existing_body_text_untouched():
    content = _content()
    # §2(구 §1) 대원칙 3개 문구가 그대로 남아있는지
    assert "원문 보존 + 증분 누적 (Layer 1 존중)" in content
    assert "플레이스홀더(TBD) 박멸" in content
    assert "맥락적 연결 (Semantic Wikilink)" in content
    # §4(구 §3) 변증법 프로토콜 3단계가 그대로 남아있는지
    assert "상호 contested 처리" in content
    assert "지시 문서(Issue) 발의" in content
    assert "인간 판정 대기" in content
