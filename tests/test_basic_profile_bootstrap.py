"""v0.6.38+ — Lite bootstrap 프로파일화 회귀 가드.

사용자 north star (v0.6.37 재정렬): "기본 정체성 = Obsidian 대체 자체 구현. LLM Wiki = vault 안 +α 옵션. mode = 옳았음, 다만 vault 전체 강제가 아니라 vault 안 영역에 +α로."

vault create 시 --profile 옵션:
  - basic (사람 1차 Obsidian-style): WELCOME.md 1장만
  - llm-wiki (project/agent-ready): SCHEMA+RULES+AGENTS+PROJECT-WORKFLOW+log.md (5종)

회귀 가드 (v0.6.38):
  1. WELCOME.md 템플릿 존재
  2. _bootstrap_basic() 클래스 메서드 존재
  3. CLI에 --profile 옵션 존재
  4. CLI에 profile 검증 (basic / llm-wiki만 허용)
  5. _BASIC_BOOTSTRAP_FILES 상수 정의
  6. basic profile → log.md 생성 안 함 (사람 자유)
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WELCOME_TEMPLATE = ROOT / "raven" / "core" / "templates" / "system" / "WELCOME.md"
VAULT_PY = ROOT / "raven" / "core" / "vault.py"
CLI_PY = ROOT / "raven" / "cli" / "__main__.py"


def test_welcome_template_exists() -> None:
    """basic profile의 WELCOME.md 템플릿이 raven 패키지 안에 있어야 함."""
    assert WELCOME_TEMPLATE.exists(), (
        f"basic profile bootstrap template missing: {WELCOME_TEMPLATE}"
    )


def test_welcome_template_has_human_first_message() -> None:
    """WELCOME.md가 사람 1차 메시지를 명확히 담아야 함."""
    content = WELCOME_TEMPLATE.read_text(encoding="utf-8")
    has_human_first = "Obsidian" in content and "you decide" in content.lower()
    assert has_human_first, "WELCOME.md must convey human-first Obsidian-style message"


def test_vault_py_has_basic_bootstrap() -> None:
    """raven/core/vault.py에 _bootstrap_basic 클래스 메서드가 있어야 함."""
    content = VAULT_PY.read_text(encoding="utf-8")
    assert "def _bootstrap_basic" in content, \
        "vault.py missing _bootstrap_basic classmethod"


def test_vault_py_has_basic_whitelist() -> None:
    """vault.py에 _BASIC_BOOTSTRAP_FILES 상수가 정의되어야 함."""
    content = VAULT_PY.read_text(encoding="utf-8")
    assert "_BASIC_BOOTSTRAP_FILES" in content, \
        "vault.py missing _BASIC_BOOTSTRAP_FILES constant"


def test_vault_py_has_profile_param() -> None:
    """Vault.create()에 profile 파라미터가 있어야 함."""
    content = VAULT_PY.read_text(encoding="utf-8")
    assert "profile: str = \"llm-wiki\"" in content or "profile: str = 'llm-wiki'" in content, \
        "Vault.create() missing profile parameter"


def test_cli_has_profile_option() -> None:
    """CLI vault create에 --profile 옵션이 있어야 함."""
    content = CLI_PY.read_text(encoding="utf-8")
    assert "--profile" in content, "CLI vault create missing --profile option"
    assert "'basic'" in content or "\"basic\"" in content, \
        "CLI vault create missing 'basic' profile name"


def test_cli_validates_profile() -> None:
    """CLI가 잘못된 profile 거부해야 함."""
    content = CLI_PY.read_text(encoding="utf-8")
    assert "invalid profile" in content, \
        "CLI vault create must validate profile and reject invalid values"


def test_basic_profile_skips_log_md() -> None:
    """basic profile은 log.md 자동 append 안 함 (사람 자유)."""
    content = VAULT_PY.read_text(encoding="utf-8")
    # 'if profile != "basic":' check before log append
    assert 'if profile != "basic"' in content, \
        "vault.create must skip log.md append when profile='basic'"
