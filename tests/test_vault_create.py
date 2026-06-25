"""Tests for Vault.create bootstrap behavior."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wikisys.core.registry import VAULTS_ROOT, registry
from wikisys.core.vault import Vault


@pytest.fixture
def isolated_vaults_root(monkeypatch):
    """Redirect WIKI_VAULTS_DIR to a temp dir so registry doesn't touch real vaults."""
    tmp = Path(tempfile.mkdtemp(prefix="wikisys-test-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def isolated_target(monkeypatch):
    """Separate temp dir for the actual vault path (not the registry root)."""
    tmp = Path(tempfile.mkdtemp(prefix="wikisys-target-"))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


# ─── bootstrap on (default) ──────────────────────────────────


def test_bootstrap_creates_content_and_meta_dirs(isolated_vaults_root, isolated_target):
    v = Vault.create("smoke1", isolated_target / "smoke1", bootstrap=True)
    assert (v.root / "content").is_dir()
    assert (v.root / "_meta").is_dir()
    assert (v.root / ".vault.json").is_file()


def test_bootstrap_copies_schema_and_rules(isolated_vaults_root, isolated_target):
    v = Vault.create("smoke2", isolated_target / "smoke2", bootstrap=True)
    assert (v.root / "_meta" / "SCHEMA.md").is_file()
    assert (v.root / "_meta" / "RULES.md").is_file()
    # content sanity
    schema = (v.root / "_meta" / "SCHEMA.md").read_text()
    assert "Source of Truth" in schema
    assert "wikilink" in schema.lower()


def test_bootstrap_does_not_overwrite_existing_user_rules(isolated_vaults_root, isolated_target):
    v = Vault.create("smoke3", isolated_target / "smoke3", bootstrap=True)
    # user customizes RULES.md
    custom = (v.root / "_meta" / "RULES.md")
    custom.write_text("# My custom rules\n")
    # re-call bootstrap (simulating upgrade) — should NOT overwrite
    Vault._bootstrap(v.root)
    assert custom.read_text() == "# My custom rules\n"


# ─── bootstrap off (--no-bootstrap) ─────────────────────────


def test_no_bootstrap_creates_empty_dirs_but_no_template_files(isolated_vaults_root, isolated_target):
    """v0.4: --no-bootstrap now creates empty content/ + _meta/ (was: only .vault.json).

    Rationale: users need a writable starting point. Templates are not copied,
    but the directories exist so `wikisys page new content/foo` works immediately.
    """
    v = Vault.create("existing1", isolated_target / "existing1", bootstrap=False)
    assert (v.root / ".vault.json").is_file()
    assert (v.root / "content").is_dir()   # empty, exists
    assert (v.root / "_meta").is_dir()     # empty, exists
    # but templates NOT copied
    assert not (v.root / "_meta" / "SCHEMA.md").exists()
    assert not (v.root / "_meta" / "RULES.md").exists()


def test_no_bootstrap_does_not_delete_existing(isolated_vaults_root, isolated_target):
    """If folder already has files, bootstrap=False must not touch them."""
    target = isolated_target / "existing2"
    target.mkdir()
    (target / "my-old-doc.md").write_text("# old\n")
    v = Vault.create("existing2", target, bootstrap=False)
    assert (target / "my-old-doc.md").read_text() == "# old\n"


# ─── sync_meta ───────────────────────────────────────────────


def test_sync_meta_overwrites_existing(isolated_vaults_root, isolated_target):
    v = Vault.create("sync1", isolated_target / "sync1", bootstrap=True)
    custom = (v.root / "_meta" / "RULES.md")
    custom.write_text("# Old content\n")
    result = v.sync_meta()
    assert "RULES.md" in result["copied"]
    assert "Old content" not in custom.read_text()
    assert "Vault Editing Rules" in custom.read_text()


# ─── registry integration ───────────────────────────────────


def test_create_registers_in_registry(isolated_vaults_root, isolated_target):
    name = "reg-test"
    v = Vault.create(name, isolated_target / name, bootstrap=True)
    reg = registry()
    meta = reg.get(name)
    assert meta is not None
    assert meta.path == v.root
    # vault appears in list
    names = [m.name for m in reg.list()]
    assert name in names


def test_create_registers_with_first_default(isolated_vaults_root, isolated_target):
    """The first vault created in a fresh registry becomes the default."""
    v = Vault.create("first", isolated_target / "first", bootstrap=True)
    assert registry()._data.get("default") == "first"
