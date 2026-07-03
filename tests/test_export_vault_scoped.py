"""test_export_vault_scoped.py — `raven export`가 실제 vault를 대상으로 동작하는지.

회귀 가드 (2026-07-04 제품 평가 P0#1): scripts/export_static.py의 __main__이
argv(vault 경로, --out)를 무시하고 저장소 루트를 vault로 간주 + 실패해도
exit 0으로 종료 → CLI/API가 "✅ exported"로 성공 위장하던 silent failure.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from raven.core.vault import Vault
from raven.core import export as export_module
from raven.core import db as db_module


@pytest.fixture
def built_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Vault:
    """페이지 1개 + wiki.db까지 빌드된 vault."""
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp_path))
    root = tmp_path / "expo"
    vault = Vault.create("expo", root, bootstrap=True)
    (root / "content" / "수출-테스트.md").write_text(
        "---\ntitle: 수출 테스트\ntype: concept\ncreated: 2026-07-04\nupdated: 2026-07-04\n---\n\n본문\n",
        encoding="utf-8",
    )
    db_module.build_db(vault)
    return vault


def test_export_writes_vault_pages_to_out_dir(built_vault: Vault, tmp_path: Path):
    """지정한 --out 디렉토리에 해당 vault의 페이지가 실제로 export된다."""
    out = tmp_path / "static-out"
    result = export_module.export_static(built_vault, out_dir=out)

    assert result["ok"] is True, result
    index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    slugs = {p["slug"] for p in index}
    assert "content/수출-테스트" in slugs
    assert (out / "tree.json").exists()
    assert (out / "graph.json").exists()


def test_export_fails_loudly_when_db_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """wiki.db 없는 vault export는 ok=False (성공 위장 금지)."""
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp_path))
    root = tmp_path / "nodb"
    vault = Vault.create("nodb", root, bootstrap=True)
    assert not vault.db_path.exists()

    out = tmp_path / "static-out2"
    result = export_module.export_static(vault, out_dir=out)

    assert result["ok"] is False, f"silent failure: {result}"
