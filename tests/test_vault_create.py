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

from raven.core.registry import VAULTS_ROOT, registry
from raven.core.vault import Vault


@pytest.fixture
def isolated_vaults_root(monkeypatch):
    """Redirect WIKI_VAULTS_DIR to a temp dir so registry doesn't touch real vaults."""
    tmp = Path(tempfile.mkdtemp(prefix="raven-test-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def isolated_target(monkeypatch):
    """Separate temp dir for the actual vault path (not the registry root)."""
    tmp = Path(tempfile.mkdtemp(prefix="raven-target-"))
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
    assert (v.root / "_meta" / "system" / "SCHEMA.md").is_file()
    assert (v.root / "_meta" / "system" / "RULES.md").is_file()
    # content sanity
    schema = (v.root / "_meta" / "system" / "SCHEMA.md").read_text()
    assert "Source of Truth" in schema
    assert "wikilink" in schema.lower()


def test_bootstrap_does_not_overwrite_existing_user_rules(isolated_vaults_root, isolated_target):
    v = Vault.create("smoke3", isolated_target / "smoke3", bootstrap=True)
    # user customizes RULES.md
    custom = (v.root / "_meta" / "system" / "RULES.md")
    custom.write_text("# My custom rules\n")
    # re-call bootstrap (simulating upgrade) — should NOT overwrite
    Vault._bootstrap(v.root)
    assert custom.read_text() == "# My custom rules\n"


# ─── bootstrap off (--no-bootstrap) ─────────────────────────


def test_no_bootstrap_creates_empty_dirs_but_no_template_files(isolated_vaults_root, isolated_target):
    """v0.4: --no-bootstrap now creates empty content/ + _meta/ (was: only .vault.json).

    Rationale: users need a writable starting point. Templates are not copied,
    but the directories exist so `raven page new content/foo` works immediately.
    """
    v = Vault.create("existing1", isolated_target / "existing1", bootstrap=False)
    assert (v.root / ".vault.json").is_file()
    assert (v.root / "content").is_dir()   # empty, exists
    assert (v.root / "_meta").is_dir()     # empty, exists
    # templates NOT copied (system/ and agent/ subdirs not created)
    assert not (v.root / "_meta" / "system" / "SCHEMA.md").exists()
    assert not (v.root / "_meta" / "system" / "RULES.md").exists()
    assert not (v.root / "_meta" / "agent" / "README.md").exists()


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
    custom = (v.root / "_meta" / "system" / "RULES.md")
    custom.write_text("# Old content\n")
    result = v.sync_meta()
    # v0.8+: copied는 vault-relative path, system/ + agent/ 분리 구조
    assert "_meta/system/RULES.md" in result["copied"]
    assert "_meta/system/SCHEMA.md" in result["copied"]
    assert "_meta/system/OPERATIONS.md" in result["copied"]
    assert "_meta/agent/README.md" in result["copied"]
    assert "_meta/agent/TOOLS.md" in result["copied"]
    assert "_meta/agent/WORKFLOW.md" in result["copied"]
    assert "_meta/agent/SAFETY.md" in result["copied"]
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


# ─── _meta/system/ + _meta/agent/ 분리 구조 (v0.8+) ──────────


def test_bootstrap_creates_system_and_agent_subdirs(isolated_vaults_root, isolated_target):
    """bootstrap=True must create _meta/system/ and _meta/agent/ subdirectories."""
    v = Vault.create("split1", isolated_target / "split1", bootstrap=True)
    assert (v.root / "_meta" / "system").is_dir()
    assert (v.root / "_meta" / "agent").is_dir()


def test_bootstrap_creates_all_system_templates(isolated_vaults_root, isolated_target):
    """_meta/system/ must contain SCHEMA.md, RULES.md, OPERATIONS.md."""
    v = Vault.create("split2", isolated_target / "split2", bootstrap=True)
    system_dir = v.root / "_meta" / "system"
    for fname in ("SCHEMA.md", "RULES.md", "OPERATIONS.md"):
        assert (system_dir / fname).is_file(), f"missing _meta/system/{fname}"
    # content sanity
    schema = (system_dir / "SCHEMA.md").read_text()
    assert "audience: system" in schema
    assert "혼용 ❌" in schema
    ops = (system_dir / "OPERATIONS.md").read_text()
    assert "audience: system" in ops
    assert "agent/" in ops


def test_bootstrap_creates_all_agent_templates(isolated_vaults_root, isolated_target):
    """_meta/agent/ must contain README.md, TOOLS.md, WORKFLOW.md, SAFETY.md."""
    v = Vault.create("split3", isolated_target / "split3", bootstrap=True)
    agent_dir = v.root / "_meta" / "agent"
    for fname in ("README.md", "TOOLS.md", "WORKFLOW.md", "SAFETY.md"):
        assert (agent_dir / fname).is_file(), f"missing _meta/agent/{fname}"
    # audience sanity
    for fname in ("README.md", "TOOLS.md", "WORKFLOW.md", "SAFETY.md"):
        text = (agent_dir / fname).read_text()
        assert "audience: agent" in text, f"_meta/agent/{fname} missing audience: agent"


def test_bootstrap_idempotent_does_not_overwrite_agent_files(isolated_vaults_root, isolated_target):
    """Re-running _bootstrap must not overwrite existing agent/ files."""
    v = Vault.create("split4", isolated_target / "split4", bootstrap=True)
    readme = v.root / "_meta" / "agent" / "README.md"
    readme.write_text("# My custom agent guide\n")
    Vault._bootstrap(v.root)
    assert readme.read_text() == "# My custom agent guide\n"


def test_sync_meta_creates_system_and_agent_dirs_if_missing(isolated_vaults_root, isolated_target):
    """sync_meta() must create _meta/system/ and _meta/agent/ if they don't exist."""
    v = Vault.create("split5", isolated_target / "split5", bootstrap=False)
    result = v.sync_meta()
    assert (v.root / "_meta" / "system").is_dir()
    assert (v.root / "_meta" / "agent").is_dir()
    assert "_meta/system/SCHEMA.md" in result["copied"]
    assert "_meta/agent/README.md" in result["copied"]
    assert result["errors"] == []
