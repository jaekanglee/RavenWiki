"""CHECK_REGISTRY가 실제 run_all() 산출 check id를 전부 커버하는지 회귀 검증.

새 check_* 함수가 lint.py에 추가됐는데 CHECK_REGISTRY 등록을 빠뜨리면 이 테스트가
실패해 즉시 드러난다 (대시보드/CLI 14개↔23개 drift 재발 방지).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core import lint as lint_module
from raven.core.vault import Vault


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-lintreg-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-lintreg-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("lintreg-test", target_root / "lintreg-test", bootstrap=False)
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def test_check_registry_covers_all_produced_ids(vault):
    result = lint_module.run_all(vault)
    produced_ids = set(result["by_check"].keys())
    registry_ids = set(lint_module.CHECK_REGISTRY.keys())
    missing = produced_ids - registry_ids
    assert not missing, f"CHECK_REGISTRY에 등록되지 않은 check id: {missing}"


def test_check_registry_fn_names_resolve_to_real_functions():
    for cid, meta in lint_module.CHECK_REGISTRY.items():
        fn_name = meta.get("fn")
        if fn_name is None:
            continue
        assert hasattr(lint_module, fn_name), (
            f"{cid}: CHECK_REGISTRY.fn={fn_name!r} 가 raven.core.lint에 없음"
        )


def test_run_all_embeds_checks_field(vault):
    result = lint_module.run_all(vault)
    assert "checks" in result
    assert result["checks"] == {
        cid: meta["name"] for cid, meta in lint_module.CHECK_REGISTRY.items()
    }
