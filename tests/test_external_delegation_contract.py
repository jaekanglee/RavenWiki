"""v0.6.34+ — agent/README.md 외부 위임 backend 가이드 회귀 가드.

subagent 분석에서 제안한 'raven-delegate.md 톤 한 줄 추가'는 실제 파일이
없어서 agent/README.md에 적용. Codex/Antigravity CLI 한 줄 가이드 보존 확인.

회귀 가드:
  1. agent/README.md에 '외부 위임' 또는 'Antigravity' / 'Codex' 키워드
  2. wrap-up 단계 fix 침습 금지 톤 ('분석만' 또는 'wrap-up')
  3. 사용자 명시 / Gemini cross-check 시점 명시
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_README = ROOT / "raven" / "core" / "templates" / "agent" / "README.md"


def test_agent_readme_mentions_external_delegation() -> None:
    content = AGENT_README.read_text(encoding="utf-8")
    # Codex 또는 Antigravity 중 하나는 명시되어야 함
    has_codex = "Codex" in content or "codex" in content
    has_agy = "Antigravity" in content or "agy" in content
    assert has_codex or has_agy, \
        "agent/README.md must mention Codex CLI or Antigravity CLI"


def test_agent_readme_wrapup_fix_constraint() -> None:
    """wrap-up 단계에서 fix 침습 금지 톤이 명시되어야 함."""
    content = AGENT_README.read_text(encoding="utf-8")
    has_constraint = (
        "wrap-up" in content.lower() and
        ("분석만" in content or "fix 침습" in content or "wrap-up 단계" in content)
    )
    assert has_constraint, \
        "agent/README.md must have wrap-up fix constraint"


def test_agent_readme_user_explicit_or_gemini_check() -> None:
    """사용자 명시 또는 Gemini cross-check 시점 명시."""
    content = AGENT_README.read_text(encoding="utf-8")
    has_trigger = (
        "사용자 명시" in content or
        "Gemini" in content
    )
    assert has_trigger, \
        "agent/README.md must specify when to delegate (user-explicit or Gemini check)"