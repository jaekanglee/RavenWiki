"""v0.8.1+ 에이전트 포인터 스텁 (AGENTS.md/CLAUDE.md/GEMINI.md/.cursorrules/.windsurfrules).

_meta/agents/PROJECT-WORKFLOW.md가 존재하는 vault는 profile과 무관하게
5개 포인터 스텁을 얻는다. basic 프로필(PROJECT-WORKFLOW.md 없음)은 스텁도 없다.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core.vault import Vault, AGENT_POINTER_STUB_FILES, AGENT_POINTER_STUB_CONTENT


@pytest.fixture
def isolated_vaults_root(monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="raven-stub-reg-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def isolated_target():
    tmp = Path(tempfile.mkdtemp(prefix="raven-stub-target-"))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def test_llm_wiki_profile_creates_all_stub_files(isolated_vaults_root, isolated_target):
    v = Vault.create("stub-llm", isolated_target / "stub-llm", profile="llm-wiki")
    for fname in AGENT_POINTER_STUB_FILES:
        fp = v.root / fname
        assert fp.is_file(), f"{fname} should exist for llm-wiki profile"
        assert fp.read_text(encoding="utf-8") == AGENT_POINTER_STUB_CONTENT


def test_basic_profile_creates_no_stub_files(isolated_vaults_root, isolated_target):
    v = Vault.create("stub-basic", isolated_target / "stub-basic", profile="basic")
    for fname in AGENT_POINTER_STUB_FILES:
        assert not (v.root / fname).exists(), f"{fname} should NOT exist for basic profile"


def test_sync_meta_backfills_stubs_after_basic_to_llm_wiki_transition(isolated_vaults_root, isolated_target):
    v = Vault.create("stub-transition", isolated_target / "stub-transition", profile="basic")
    for fname in AGENT_POINTER_STUB_FILES:
        assert not (v.root / fname).exists()
    v.sync_meta()
    assert (v.root / "_meta" / "agents" / "PROJECT-WORKFLOW.md").is_file()
    for fname in AGENT_POINTER_STUB_FILES:
        fp = v.root / fname
        assert fp.is_file(), f"{fname} should appear after sync_meta() backfills PROJECT-WORKFLOW.md"
        assert fp.read_text(encoding="utf-8") == AGENT_POINTER_STUB_CONTENT


def test_sync_meta_always_overwrites_stub_files_even_when_manually_edited(isolated_vaults_root, isolated_target):
    v = Vault.create("stub-overwrite", isolated_target / "stub-overwrite", profile="llm-wiki")
    tampered = v.root / "CLAUDE.md"
    tampered.write_text("사용자가 직접 고친 내용\n", encoding="utf-8")
    v.sync_meta()
    assert tampered.read_text(encoding="utf-8") == AGENT_POINTER_STUB_CONTENT


def test_lite_bootstrap_file_map_is_shared_single_source(isolated_vaults_root, isolated_target):
    """LITE_BOOTSTRAP_FILE_MAP 통합 회귀 가드: 두 경로가 같은 상수를 참조한다."""
    from raven.core.vault import LITE_BOOTSTRAP_FILE_MAP
    assert set(LITE_BOOTSTRAP_FILE_MAP.keys()) == {
        "_meta/agents/SCHEMA.md",
        "_meta/agents/PROJECT-WORKFLOW.md",
        "log.md",
    }
    v = Vault.create("stub-consistency", isolated_target / "stub-consistency", profile="llm-wiki")
    for rel_target in LITE_BOOTSTRAP_FILE_MAP:
        assert (v.root / rel_target).is_file()
