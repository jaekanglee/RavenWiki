"""v0.7.1+ — Lite bootstrap AGENTS.md 도구 표면 회귀 가드.

사용자 정정 (2026-06-30):
  '사용자는 Raven이 정의한 최소한의 vault 구조 내에서 자기 프로덕트를
   알아서 문서화하는 사람이지, Raven의 세부 로직이나 구현사항을 알 필요는
   없음. 알아야 할 건 명확히 Raven이 제공하는 도구로써의 표면일 뿐.'

Lite bootstrap AGENTS.md = vault 사용자 표면 가이드.
Raven 내부 구현 (Tier 1 leak 정책, vendor 예시, OPERATIONS/agent/raven-policy
복사 금지 등) ❌. 도구 사용자가 알 필요 없음.

회귀 가드 (v0.7.1):
  1. Lite bootstrap AGENTS.md에 vendor 예시 (Codex/Claude/Cursor/agy) 0회
  2. Lite bootstrap AGENTS.md에 Tier 1 leak 정책 (OPERATIONS/agent/raven-policy 복사 금지) 0회
  3. Lite bootstrap AGENTS.md에 도구 내부 정책 ('raven 운영 코드' 등) 0회
  4. Lite bootstrap AGENTS.md는 vault 사용자 표면만 (저장 신호, 권한, 페이지 작성)
  5. 기존 vault (harumoa, raven-dev) AGENTS.md 동기화 확인
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LITE_AGENTS = ROOT / "raven" / "core" / "templates" / "system" / "AGENTS.md"

# vendor 예시 (Lite bootstrap에 박히면 안 됨)
FORBIDDEN_VENDORS = ("Codex", "Claude Code", "Cursor", "Antigravity", "agy")

# 도구 내부 정책 (Lite bootstrap에 박히면 안 됨)
FORBIDDEN_INTERNAL_TERMS = (
    "Tier 1 leak",            # raven 내부 lint 정책
    "raven 운영 코드",         # raven 내부 정책
    "OPERATIONS.md",           # raven internal doc
    "raven-policy",            # raven internal doc
    "vendor에 종속",          # 도구 무관 위반
)


def test_lite_agents_no_vendor_examples() -> None:
    """Lite bootstrap AGENTS.md에 vendor 예시 0회."""
    content = LITE_AGENTS.read_text(encoding="utf-8")
    for vendor in FORBIDDEN_VENDORS:
        assert vendor not in content, (
            f"Lite bootstrap AGENTS.md has vendor example '{vendor}' — "
            f"사용자에게 도구 vendor 노출 ❌ (north star 위반)"
        )


def test_lite_agents_no_internal_policy() -> None:
    """Lite bootstrap AGENTS.md에 도구 내부 정책 0회."""
    content = LITE_AGENTS.read_text(encoding="utf-8")
    for term in FORBIDDEN_INTERNAL_TERMS:
        assert term not in content, (
            f"Lite bootstrap AGENTS.md has internal policy '{term}' — "
            f"사용자에게 raven 도구 내부 노출 ❌"
        )


def test_lite_agents_has_vault_user_surface() -> None:
    """Lite bootstrap AGENTS.md는 vault 사용자 표면 (저장 신호, 권한, 페이지 작성)."""
    content = LITE_AGENTS.read_text(encoding="utf-8")
    # 4가지 저장 신호
    assert "재사용 가능성" in content, "missing 4가지 신호 #1"
    assert "인수인계 필요성" in content, "missing 4가지 신호 #2"
    assert "결정 근거" in content, "missing 4가지 신호 #3"
    # 4 키워드
    assert "save" in content and "ingest" in content and "query" in content and "lint" in content
    # vault 3개 영역
    assert "content/" in content and "_meta/" in content and "log.md" in content
    # type 8종
    assert "concept" in content and "journal" in content


def test_lite_agents_starts_with_user_guide() -> None:
    """Lite bootstrap AGENTS.md가 'Vault User Guide'로 시작해야 함."""
    content = LITE_AGENTS.read_text(encoding="utf-8")
    assert "Vault User Guide" in content, \
        "Lite bootstrap AGENTS.md must be 'Vault User Guide' (not 'Vault Agent Operations')"


def test_existing_vaults_synced() -> None:
    """기존 vault (harumoa, raven-dev) AGENTS.md가 새 템플릿과 일치."""
    template_content = LITE_AGENTS.read_text(encoding="utf-8")
    for vault_name in ("harumoa", "raven-dev"):
        target = Path(f"/Users/jaekanglee/Raven/{vault_name}/_meta/system/AGENTS.md")
        if not target.exists():
            continue
        target_content = target.read_text(encoding="utf-8")
        assert target_content == template_content, (
            f"{vault_name}/_meta/system/AGENTS.md가 새 템플릿과 다름 ❌. "
            f"`cp` 명령으로 동기화 필요."
        )