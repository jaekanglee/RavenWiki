"""v0.6.36+ — agent/README.md 외부 LLM cross-check 가이드 회귀 가드.

v0.6.34에서 제안된 'agent/README.md 외부 위임 backend' 가이드는
v0.6.36에서 vendor-agnostic으로 재정렬됨. vendor명 자체를 정책 문서에
박지 않고, "외부 LLM cross-check"으로 추상화.

회귀 가드:
  1. agent/README.md에 '외부 LLM' 또는 'cross-check' 키워드 (vendor-neutral)
  2. wrap-up 단계 fix 침습 금지 톤 ('분석만' 또는 'wrap-up')
  3. 사용자 명시 / cross-check 시점 명시 (vendor-neutral trigger)
  4. (v0.6.36+) 정책 문서에 vendor명 (Codex/Antigravity/Hermes/Claude/Gemini)
     직접 표기 ❌ — north star 재정렬 영구화
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_README = ROOT / "raven" / "core" / "templates" / "agent" / "README.md"

# vendor-neutral 키워드 (1-A 재정렬 후)
VENDOR_NEUTRAL_KEYWORDS = ("외부 LLM", "cross-check")

# 정책 문서에 직접 박히면 안 되는 vendor명 (north star 위반)
FORBIDDEN_VENDORS_IN_POLICY = (
    "Codex", "codex",
    "Antigravity", "agy",
    "Gemini",
)


def _read_agent_readme() -> str:
    return AGENT_README.read_text(encoding="utf-8")


def test_agent_readme_mentions_external_llm_crosscheck() -> None:
    """agent/README.md에 vendor-neutral 외부 LLM cross-check 키워드가 있어야 함."""
    content = _read_agent_readme()
    has_vendor_neutral = any(kw in content for kw in VENDOR_NEUTRAL_KEYWORDS)
    assert has_vendor_neutral, (
        f"agent/README.md must mention vendor-neutral keyword "
        f"({' or '.join(VENDOR_NEUTRAL_KEYWORDS)})"
    )


def test_agent_readme_wrapup_fix_constraint() -> None:
    """wrap-up 단계에서 fix 침습 금지 톤이 명시되어야 함 (v0.6.34 유지)."""
    content = _read_agent_readme()
    has_constraint = (
        "wrap-up" in content.lower()
        and ("분석만" in content or "fix 침습" in content or "wrap-up 단계" in content)
    )
    assert has_constraint, (
        "agent/README.md must have wrap-up fix constraint"
    )


def test_agent_readme_user_explicit_or_crosscheck_trigger() -> None:
    """사용자 명시 또는 cross-check 시점이 vendor-neutral로 명시되어야 함."""
    content = _read_agent_readme()
    has_trigger = "사용자 명시" in content and "cross-check" in content
    assert has_trigger, (
        "agent/README.md must specify user-explicit or cross-check trigger "
        "(vendor-neutral)"
    )


def test_agent_readme_no_forbidden_vendor_names() -> None:
    """v0.6.36+ 정책: agent/README.md 외부 위임 섹션에 vendor명 직접 표기 ❌.

    north star (Karpathy LLM Wiki) 재정렬 — 어떤 vendor가 와도 동일하게 다룬다.
    vendor명 자체를 정책 문서에 박지 않는다.
    """
    content = _read_agent_readme()
    # 외부 위임 섹션에서만 검사 (문서 전반의 vendor 예시는 OK)
    # 섹션 헤더부터 끝까지 추출
    section_start = content.find("## 외부 LLM cross-check")
    assert section_start != -1, (
        "agent/README.md must have '외부 LLM cross-check' section header"
    )
    section_end = content.find("\n## ", section_start + 1)
    if section_end == -1:
        section_end = len(content)
    section = content[section_start:section_end]

    for vendor in FORBIDDEN_VENDORS_IN_POLICY:
        assert vendor not in section, (
            f"agent/README.md 외부 LLM cross-check 섹션에 vendor명 "
            f"'{vendor}' 박힘 ❌ — north star 위반 (v0.6.36+). "
            f"vendor-neutral 표현으로 변경 필요."
        )