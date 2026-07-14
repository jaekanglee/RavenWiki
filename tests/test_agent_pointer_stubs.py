"""Tests for preservation of conventional root agent instruction files.

Under no condition should Vault.create or sync_meta create, overwrite,
or delete root AGENTS.md, CLAUDE.md, GEMINI.md, .cursorrules, .windsurfrules.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core.vault import Vault

PRESERVATION_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".cursorrules",
    ".windsurfrules",
)


@pytest.fixture
def isolated_vaults_root(monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="raven-preservation-reg-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def isolated_target():
    tmp = Path(tempfile.mkdtemp(prefix="raven-preservation-target-"))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def test_root_agent_instructions_not_created_by_default(isolated_vaults_root, isolated_target):
    """Vault.create must not create any conventional root agent instruction files."""
    v = Vault.create("pres-default", isolated_target / "pres-default", bootstrap=True)
    for fname in PRESERVATION_FILES:
        assert not (v.root / fname).exists(), f"{fname} should NOT be created by default"


def test_root_agent_instructions_preserved_during_create(isolated_vaults_root, isolated_target):
    """Vault.create must preserve pre-existing root agent files byte-for-byte."""
    root_path = isolated_target / "pres-create"
    root_path.mkdir(parents=True, exist_ok=True)

    file_contents = {}
    for fname in PRESERVATION_FILES:
        fp = root_path / fname
        content = f"user content for {fname}\n"
        fp.write_text(content, encoding="utf-8")
        file_contents[fname] = content

    v = Vault.create("pres-create", root_path, bootstrap=True)

    for fname in PRESERVATION_FILES:
        fp = v.root / fname
        assert fp.is_file()
        assert fp.read_text(encoding="utf-8") == file_contents[fname]


def test_root_agent_instructions_preserved_during_sync(isolated_vaults_root, isolated_target):
    """sync_meta must preserve pre-existing root agent files byte-for-byte."""
    v = Vault.create("pres-sync", isolated_target / "pres-sync", bootstrap=True)

    file_contents = {}
    for fname in PRESERVATION_FILES:
        fp = v.root / fname
        content = f"user content for {fname}\n"
        fp.write_text(content, encoding="utf-8")
        file_contents[fname] = content

    v.sync_meta(force=True)

    for fname in PRESERVATION_FILES:
        fp = v.root / fname
        assert fp.is_file()
        assert fp.read_text(encoding="utf-8") == file_contents[fname]


def test_legacy_pointer_stub_api_is_removed(isolated_vaults_root, isolated_target):
    """Bootstrap must not expose a pointer-stub generation API."""
    import raven.core.vault as vault_module

    assert not hasattr(vault_module, "AGENT_POINTER_STUB_FILES")
    assert not hasattr(vault_module, "AGENT_POINTER_STUB_CONTENT")
    assert not hasattr(vault_module, "_write_agent_pointer_stubs")


def test_lite_bootstrap_file_map_is_shared_single_source(isolated_vaults_root, isolated_target):
    """LITE_BOOTSTRAP_FILE_MAP consistency test."""
    from raven.core.vault import LITE_BOOTSTRAP_FILE_MAP
    assert set(LITE_BOOTSTRAP_FILE_MAP.keys()) == {
        "_meta/agents/SCHEMA.md",
        "_meta/agents/RAVEN-CONTRACT.md",
        "log.md",
    }
    v = Vault.create("stub-consistency", isolated_target / "stub-consistency", bootstrap=True)
    for rel_target in LITE_BOOTSTRAP_FILE_MAP:
        assert (v.root / rel_target).is_file()
