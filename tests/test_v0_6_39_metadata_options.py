"""v0.6.39+ — mode 메타데이터 강등 + Tier 1 leak lint 옵션화 회귀 가드.

사용자 north star (v0.6.37 재정렬): "기본 정체성 = Obsidian 대체 자체 구현. LLM Wiki = vault 안 +α 옵션. mode = 옳았음, 다만 vault 전체 강제가 아니라 vault 안 영역에 +α로."

v0.6.39 변경:
  - mode 필드는 display-only metadata로 강등 (코드 분기 0건 확인됨)
  - VaultMeta에 allow_tier1_leak, features 추가
  - Tier 1 leak lint #14 옵션화 (allow_tier1_leak=True 시 warning 강등)

회귀 가드 (v0.6.39):
  1. VaultMeta에 allow_tier1_leak 필드
  2. VaultMeta에 features 필드 (tuple)
  3. to_json이 allow_tier1_leak/features 직렬화
  4. from_json이 두 필드 역직렬화 (없으면 default False / 빈 tuple)
  5. Tier 1 leak lint #14가 vault.meta.allow_tier1_leak 반영
  6. 기본 vault (allow_tier1_leak=False)는 critical
  7. 옵트인 vault (allow_tier1_leak=True)는 warning
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PY = ROOT / "raven" / "core" / "registry.py"
LINT_PY = ROOT / "raven" / "core" / "lint.py"


def test_vault_meta_has_allow_tier1_leak() -> None:
    content = REGISTRY_PY.read_text(encoding="utf-8")
    assert "allow_tier1_leak" in content, \
        "VaultMeta missing allow_tier1_leak field (v0.6.39+)"


def test_vault_meta_has_features() -> None:
    content = REGISTRY_PY.read_text(encoding="utf-8")
    assert "features" in content, \
        "VaultMeta missing features field (v0.6.39+)"
    assert 'features: tuple' in content or 'features: tuple =' in content, \
        "VaultMeta features should be tuple (hashable for frozen dataclass)"


def test_to_json_serializes_allow_tier1_leak() -> None:
    content = REGISTRY_PY.read_text(encoding="utf-8")
    assert 'if self.allow_tier1_leak:' in content, \
        "to_json must serialize allow_tier1_leak when True"


def test_to_json_serializes_features() -> None:
    content = REGISTRY_PY.read_text(encoding="utf-8")
    assert 'if self.features:' in content, \
        "to_json must serialize features when non-empty"


def test_from_json_reads_allow_tier1_leak() -> None:
    content = REGISTRY_PY.read_text(encoding="utf-8")
    assert 'data.get("allow_tier1_leak", False)' in content, \
        "from_json must read allow_tier1_leak with default False"


def test_from_json_reads_features() -> None:
    content = REGISTRY_PY.read_text(encoding="utf-8")
    assert 'data.get("features", {})' in content, \
        "from_json must read features with default empty dict"


def test_lint_tier_integrity_respects_allow_tier1_leak() -> None:
    """check_tier_integrity가 allow_tier1_leak 반영해야 함."""
    content = LINT_PY.read_text(encoding="utf-8")
    assert "allow_tier1_leak" in content, \
        "lint.py must check vault.meta.allow_tier1_leak"
    assert 'severity = "warning"' in content and "allow_tier1_leak" in content, \
        "lint.py must downgrade severity to warning when allow_tier1_leak=True"
    assert 'severity = "critical"' in content or '"critical"' in content, \
        "lint.py must keep critical as default severity"


def test_default_vault_still_critical() -> None:
    """기본 vault (allow_tier1_leak 없음)는 여전히 critical — 안전망 유지."""
    content = LINT_PY.read_text(encoding="utf-8")
    # severity = "warning" if getattr(vault.meta, "allow_tier1_leak", False) else "critical"
    assert 'getattr(vault.meta, "allow_tier1_leak", False)' in content, \
        "lint must use getattr with default False to preserve safety"


def test_vault_meta_roundtrip() -> None:
    """VaultMeta 직렬화 라운드트립 — features/allow_tier1_leak 보존."""
    from raven.core.registry import VaultMeta
    meta = VaultMeta(
        name="test-vault",
        path=Path("/tmp/test"),
        mode="personal",
        allow_tier1_leak=True,
        features=(("llm_wiki", True),),
    )
    j = meta.to_json()
    assert j.get("allow_tier1_leak") is True
    assert j.get("features") == {"llm_wiki": True}
    # roundtrip
    meta2 = VaultMeta.from_json("test-vault", j)
    assert meta2.allow_tier1_leak is True
    assert meta2.features == (("llm_wiki", True),)
    # default values
    meta3 = VaultMeta(name="v3", path=Path("/tmp/v3"))
    assert meta3.allow_tier1_leak is False
    assert meta3.features == ()