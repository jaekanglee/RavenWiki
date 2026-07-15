"""Regression tests for build_db result shape used by Dashboard rebuild UI."""
from __future__ import annotations

from pathlib import Path

from raven.core import db as db_module
from raven.core.vault import Vault


def test_build_db_result_includes_pages_and_returncode(tmp_path: Path, monkeypatch) -> None:
    reg_root = tmp_path / "registry"
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    vault = Vault.create("build-result", tmp_path / "vault")
    content_dir = vault.root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    (content_dir / "hello.md").write_text(
        "---\ntitle: Hello\ntype: concept\ncreated: 2026-01-01\nupdated: 2026-01-01\n---\n\nbody\n",
        encoding="utf-8",
    )

    result = db_module.build_db(vault, run_lint=False)

    assert result["ok"] is True
    assert isinstance(result.get("pages"), int)
    assert result["pages"] >= 1
    assert result.get("returncode") == 0
