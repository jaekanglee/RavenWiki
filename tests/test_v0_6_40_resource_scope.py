"""v0.6.40+ — AgentScope resource scope (allowed_paths / deny_paths) 회귀 가드.

사용자 north star (v0.6.37 재정렬): "vault 자유, 정책 강제 ❌, 단 opt-in 안전벨트는 사용자 책임."

v0.6.40 변경:
  - AgentScope에 allowed_paths / deny_paths 필드 추가 (path-level scope)
  - allows_path(slug) 메서드 — glob 매칭 (deny_paths 우선)
  - AgentVault.write()가 path scope 위반 시 Result(ok=False, error=...) 반환
  - 기존 vault_names 격리는 그대로 유지 (vault-level scope)

회귀 가드 (v0.6.40):
  1. AgentScope에 allowed_paths, deny_paths 필드
  2. allows_path() 메서드 존재
  3. deny_paths 매칭 시 False (deny wins)
  4. allowed_paths 비어있으면 모두 허용 (현재 동작)
  5. allowed_paths 매칭 시 True
  6. allowed_paths 비어있지 않고 미매칭 시 False
  7. AgentVault.write()가 scope 위반 시 Result(ok=False) 반환
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_PY = ROOT / "raven" / "agents" / "agent.py"


def test_agentscope_has_allowed_paths() -> None:
    content = AGENT_PY.read_text(encoding="utf-8")
    assert "allowed_paths: tuple[str, ...]" in content, \
        "AgentScope missing allowed_paths field (v0.6.40+)"


def test_agentscope_has_deny_paths() -> None:
    content = AGENT_PY.read_text(encoding="utf-8")
    assert "deny_paths: tuple[str, ...]" in content, \
        "AgentScope missing deny_paths field (v0.6.40+)"


def test_agentscope_has_allows_path_method() -> None:
    content = AGENT_PY.read_text(encoding="utf-8")
    assert "def allows_path" in content, \
        "AgentScope missing allows_path() method (v0.6.40+)"
    assert "fnmatch" in content, \
        "allows_path() must use fnmatch for glob matching"


def test_allows_path_deny_wins() -> None:
    """deny_paths 매칭이 allowed_paths보다 우선해야 함."""
    from raven.agents import AgentScope
    scope = AgentScope(
        vault_names=("test",),
        allowed_paths=("**",),  # everything
        deny_paths=("raw/**",),  # but not raw/
    )
    assert scope.allows_path("content/foo") is True, \
        "deny_paths should NOT match content/foo"
    assert scope.allows_path("raw/articles/bar") is False, \
        "deny_paths MUST match raw/articles/bar (deny wins)"


def test_allows_path_no_allowlist_passes_all() -> None:
    """allowed_paths 비어있으면 모든 slug 허용 (현재 동작 보존)."""
    from raven.agents import AgentScope
    scope = AgentScope(vault_names=("test",))
    assert scope.allows_path("anywhere/foo") is True
    assert scope.allows_path("_meta/system/AGENTS.md") is True
    assert scope.allows_path("raw/articles/x") is True


def test_allows_path_with_allowlist_matches() -> None:
    """allowed_paths 매칭 시 True."""
    from raven.agents import AgentScope
    scope = AgentScope(
        vault_names=("test",),
        allowed_paths=("content/compiled/**", "content/claims/**"),
    )
    assert scope.allows_path("content/compiled/x") is True
    assert scope.allows_path("content/claims/y") is True


def test_allows_path_with_allowlist_no_match() -> None:
    """allowed_paths 비어있지 않고 미매칭 시 False."""
    from raven.agents import AgentScope
    scope = AgentScope(
        vault_names=("test",),
        allowed_paths=("content/compiled/**",),
    )
    assert scope.allows_path("content/other/x") is False, \
        "non-matching path should be denied when allowlist is set"
    assert scope.allows_path("raw/x") is False


def test_write_respects_path_scope() -> None:
    """AgentVault.write()가 path scope 위반 시 Result(ok=False) 반환."""
    content = AGENT_PY.read_text(encoding="utf-8")
    assert "not allowed at path" in content, \
        "AgentVault.write() must reject writes outside path scope"
    assert "Result(" in content and "ok=False" in content, \
        "write() must return Result(ok=False) on scope violation"