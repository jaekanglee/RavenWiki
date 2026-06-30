"""v0.7.1+ — Lite bootstrap 도구 표면 회귀 가드.

사용자 정정 (2026-06-30):
  '사용자는 Raven이 정의한 최소한의 vault 구조 내에서 자기 프로덕트를
   알아서 문서화하는 사람이지, Raven의 세부 로직이나 구현사항을 알 필요는
   없음. 알아야 할 건 명확히 Raven이 제공하는 도구로써의 표면일 뿐.'

Lite bootstrap AGENTS.md = vault 사용자 표면 가이드.
Lite bootstrap PROJECT-WORKFLOW.md = 프로젝트 작업 에이전트 공통 워크플로우.
Raven 내부 구현 (Tier 1 leak 정책, vendor 예시, OPERATIONS/agent/raven-policy
복사 금지 등) ❌. 도구 사용자가 알 필요 없음.

회귀 가드 (v0.7.1):
  1. Lite bootstrap AGENTS.md에 vendor 예시 0회
  2. Lite bootstrap AGENTS.md에 Tier 1 leak 정책 0회
  3. Lite bootstrap AGENTS.md에 도구 내부 정책 0회
  4. Lite bootstrap AGENTS.md는 vault 사용자 표면만
  5. Lite bootstrap AGENTS.md 헤더 = "Vault User Guide"
  6. 기존 vault (harumoa, raven-dev) AGENTS.md 동기화 확인
  7. (v0.7.1 확장) Lite bootstrap SCHEMA.md에도 도구 내부 정책 0회
  8. (v0.7.1 확장) Lite bootstrap SCHEMA.md에 도메인 가정 (karpathy 등) 0회
  9. (v0.7.1 확장) Lite bootstrap log.md에 도메인 가정 0회
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LITE_AGENTS = ROOT / "raven" / "core" / "templates" / "system" / "AGENTS.md"
LITE_SCHEMA = ROOT / "raven" / "core" / "templates" / "system" / "SCHEMA.md"
LITE_LOG = ROOT / "raven" / "core" / "templates" / "log.md"
LITE_PROJECT_WORKFLOW = ROOT / "raven" / "core" / "templates" / "agent" / "PROJECT-WORKFLOW.md"

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

# 도메인 가정 (Lite bootstrap에 박히면 안 됨)
FORBIDDEN_DOMAIN_TERMS = (
    "karpathy",                # 원본/영감 가정
    "llm-wiki",                # 도메인 가정 (vault 자유)
    "Karpathy",                # 대문자도 동일
)
# "LLM Wiki +α 패턴"은 사용자 표면 가이드 (docs/vault-patterns.md) 링크이므로
# OK — 사용자가 직접 참조할 수 있는 표면 가이드 자체.
# 단독 "LLM Wiki" 박힘은 도메인 가정으로 간주하지만, "+α 패턴" 같은 표면 참조는 OK.


def _assert_no_terms(content: str, terms: tuple, file_label: str) -> None:
    for term in terms:
        assert term not in content, (
            f"{file_label} has forbidden term '{term}' — "
            f"사용자 표면 가이드에 raven 도구 내부/도메인 가정 노출 ❌"
        )


def test_lite_agents_no_vendor_examples() -> None:
    content = LITE_AGENTS.read_text(encoding="utf-8")
    _assert_no_terms(content, FORBIDDEN_VENDORS, "Lite bootstrap AGENTS.md")


def test_lite_agents_no_internal_policy() -> None:
    content = LITE_AGENTS.read_text(encoding="utf-8")
    _assert_no_terms(content, FORBIDDEN_INTERNAL_TERMS, "Lite bootstrap AGENTS.md")


def test_lite_agents_has_vault_user_surface() -> None:
    content = LITE_AGENTS.read_text(encoding="utf-8")
    assert "재사용 가능성" in content, "missing 4가지 신호 #1"
    assert "인수인계 필요성" in content, "missing 4가지 신호 #2"
    assert "결정 근거" in content, "missing 4가지 신호 #3"
    assert "save" in content and "ingest" in content and "query" in content and "lint" in content
    assert "content/" in content and "_meta/" in content and "log.md" in content
    assert "concept" in content and "journal" in content


def test_lite_agents_starts_with_user_guide() -> None:
    content = LITE_AGENTS.read_text(encoding="utf-8")
    assert "Vault User Guide" in content, \
        "Lite bootstrap AGENTS.md must be 'Vault User Guide'"


def test_existing_vaults_synced() -> None:
    """raven-dev Lite bootstrap files가 새 템플릿과 일치.

    v0.7.4+: harumoa는 운영자가 실제 사용 중이라 sync 테스트에서 제외
    (운영자 자유 존중 — vault 데이터 write 정책). raven-dev만 검증.
    """
    template_agents = LITE_AGENTS.read_text(encoding="utf-8")
    template_schema = LITE_SCHEMA.read_text(encoding="utf-8")
    template_log = LITE_LOG.read_text(encoding="utf-8")
    template_project_workflow = LITE_PROJECT_WORKFLOW.read_text(encoding="utf-8")
    # raven-dev만 검증 (harumoa는 운영 중이라 자유)
    for label, template in (
        ("_meta/system/AGENTS.md", template_agents),
        ("_meta/system/SCHEMA.md", template_schema),
        ("_meta/agents/PROJECT-WORKFLOW.md", template_project_workflow),
        ("log.md", template_log),
    ):
        target = Path(f"/Users/jaekanglee/Raven/raven-dev/{label}")
        if not target.exists():
            continue
        target_content = target.read_text(encoding="utf-8")
        assert target_content == template, (
            f"raven-dev/{label}가 새 템플릿과 다름 ❌"
        )


def test_lite_schema_no_internal_policy() -> None:
    """v0.7.1+: Lite bootstrap SCHEMA.md에도 도구 내부 정책 0회."""
    content = LITE_SCHEMA.read_text(encoding="utf-8")
    _assert_no_terms(content, FORBIDDEN_INTERNAL_TERMS, "Lite bootstrap SCHEMA.md")


def test_lite_schema_no_domain_assumptions() -> None:
    """v0.7.1+: Lite bootstrap SCHEMA.md에 도메인 가정 (karpathy 등) 0회."""
    content = LITE_SCHEMA.read_text(encoding="utf-8")
    _assert_no_terms(content, FORBIDDEN_DOMAIN_TERMS, "Lite bootstrap SCHEMA.md")


def test_lite_log_no_domain_assumptions() -> None:
    """v0.7.1+: Lite bootstrap log.md에 도메인 가정 0회."""
    content = LITE_LOG.read_text(encoding="utf-8")
    _assert_no_terms(content, FORBIDDEN_DOMAIN_TERMS, "Lite bootstrap log.md")


def test_lite_project_workflow_is_user_surface() -> None:
    """v0.7.6+: PROJECT-WORKFLOW.md는 도구 표면 (vendor-neutral, 도구 내부 정책 ❌).

    옛 의도 (v0.7.3+): "project name" / "vault path" / "current task" Runtime Inputs 검증.
    v0.7.6+: PROJECT-WORKFLOW.md 본문 강화 — 사람/에이전트 이중 헤더 + BLUF + type 8종 템플릿.
    옛 Runtime Inputs 단어 검증은 v0.7.6+ 새 본문에서 제거 (의미 변동).
    """
    content = LITE_PROJECT_WORKFLOW.read_text(encoding="utf-8")
    _assert_no_terms(content, FORBIDDEN_VENDORS, "Lite bootstrap PROJECT-WORKFLOW.md")
    _assert_no_terms(content, FORBIDDEN_INTERNAL_TERMS, "Lite bootstrap PROJECT-WORKFLOW.md")
    # v0.7.6+: 새 키워드 (BLUF, type 8종, 사람/에이전트 이중 헤더)
    assert "BLUF" in content
    assert "concept" in content and "decision" in content
    assert "🤖" in content or "Agent" in content
    assert "📝" in content or "사람" in content


def test_lite_project_workflow_has_bluf_guidance() -> None:
    """v0.7.6+: PROJECT-WORKFLOW.md는 BLUF/템플릿 가이드 포함 (type 8종 일관성)."""
    content = LITE_PROJECT_WORKFLOW.read_text(encoding="utf-8")
    # BLUF 강조
    assert "BLUF" in content, "PROJECT-WORKFLOW.md must include BLUF guidance"
    # 4가지 결정 (결론/분업/트리거/금지)
    assert "결론" in content and "분업" in content
    assert "트리거" in content and "금지" in content
    # type 8종 가이드
    assert "concept" in content and "decision" in content and "journal" in content
    assert "rule" in content and "person" in content and "tool" in content
    assert "comparison" in content and "query" in content and "project" in content
    # 일관성 체크리스트
    assert "체크리스트" in content, "PROJECT-WORKFLOW.md must include consistency checklist"
    # 저장 신호 4가지
    assert "재사용 가능성" in content
    assert "인수인계 필요성" in content
    assert "결정 근거" in content
    assert "실패/리스크" in content or "실패" in content


def test_lite_project_workflow_prefers_human_readability() -> None:
    """PROJECT-WORKFLOW는 사람 가독성 우선 + 얇은 공통 포맷을 명시해야 한다."""
    content = LITE_PROJECT_WORKFLOW.read_text(encoding="utf-8")
    assert "사람 우선 문서 원칙" in content
    assert "frontmatter는 구조화" in content
    assert "본문은 자연스러운 문장" in content
    assert "운영 메타" in content
    assert "요약" in content and "내용" in content and "관련" in content


def test_lite_project_workflow_has_dual_audience_headings() -> None:
    """PROJECT-WORKFLOW는 헤더를 순수 자연어 위주로 유지해야 한다."""
    content = LITE_PROJECT_WORKFLOW.read_text(encoding="utf-8")
    assert "순수 자연어 헤더" in content
    assert "## 결론" in content
    assert "## 분업" in content
    assert "(BLUF)" in content
    assert "(Division)" in content


def test_lite_project_workflow_is_only_in_agent_template() -> None:
    """v0.7.6+: PROJECT-WORKFLOW.md는 templates/agent/ 한 곳에만 박힘 (정합성)."""
    agent_dir = ROOT / "raven" / "core" / "templates" / "agent" / "PROJECT-WORKFLOW.md"
    agents_dir = ROOT / "raven" / "core" / "templates" / "agents"  # 옛 path (s)
    assert agent_dir.exists(), f"{agent_dir} not found"
    assert not agents_dir.exists(), (
        f"{agents_dir} should NOT exist (path consolidation)"
    )
