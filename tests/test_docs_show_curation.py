"""`raven docs` no longer exposes CURATION.md (removed in neutral-tool refactor).

Only the negative guard remains: vault create must NOT copy CURATION.md.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core.vault import Vault


def test_vault_create_does_not_copy_curation_md(monkeypatch):
    vaults_root = Path(tempfile.mkdtemp(prefix="raven-curation-vaults-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-curation-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(vaults_root))
    try:
        v = Vault.create("curation-test", target_root / "curation-test")
        assert not (v.root / "_meta" / "agents" / "CURATION.md").exists()
    finally:
        shutil.rmtree(vaults_root, ignore_errors=True)
        shutil.rmtree(target_root, ignore_errors=True)
