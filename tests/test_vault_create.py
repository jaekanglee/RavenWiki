"""Tests for Vault.create bootstrap behavior (v2026-06-26, Lite policy).

Tier 1 ↔ Tier 2 boundary: user vault never receives raven-internal docs.
Lite bootstrap copies ONLY: _meta/system/SCHEMA.md, _meta/system/RULES.md, log.md.
"""
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
from raven.core.log import load
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


# ─── Lite bootstrap (default, 2-tier boundary) ─────────────


def test_bootstrap_creates_content_and_meta_dirs(isolated_vaults_root, isolated_target):
    """Lite bootstrap: content/ + _meta/ + .vault.json exist."""
    v = Vault.create("smoke1", isolated_target / "smoke1", bootstrap=True)
    assert (v.root / "content").is_dir()
    assert (v.root / "_meta").is_dir()
    assert (v.root / ".vault.json").is_file()


def test_bootstrap_copies_lite_templates(isolated_vaults_root, isolated_target):
    """Lite bootstrap: user-facing schema/rules/guides/log are copied."""
    v = Vault.create("smoke2", isolated_target / "smoke2", bootstrap=True)
    # Must exist (Lite whitelist)
    assert (v.root / "_meta" / "system" / "SCHEMA.md").is_file()
    assert (v.root / "_meta" / "system" / "RULES.md").is_file()
    assert (v.root / "_meta" / "system" / "AGENTS.md").is_file()
    assert (v.root / "_meta" / "agents" / "PROJECT-WORKFLOW.md").is_file()
    assert (v.root / "log.md").is_file()
    # content sanity
    schema = (v.root / "_meta" / "system" / "SCHEMA.md").read_text()
    assert "Source of Truth" in schema
    assert "wikilink" in schema.lower()


def test_bootstrap_does_not_copy_raven_internals(isolated_vaults_root, isolated_target):
    """CRITICAL: Tier 1 raven-internal docs must NEVER be in user vault (Lite policy)."""
    v = Vault.create("tier", isolated_target / "tier", bootstrap=True)
    # All raven-internal docs must be ABSENT
    assert not (v.root / "_meta" / "system" / "OPERATIONS.md").exists()
    assert not (v.root / "_meta" / "agent").exists()  # no agent/ subdir
    assert not (v.root / "raven-policy.md").exists()
    # No leftover dirs
    assert not (v.root / "_meta" / "agent" / "README.md").exists()
    assert not (v.root / "_meta" / "agent" / "TOOLS.md").exists()
    assert not (v.root / "_meta" / "agent" / "WORKFLOW.md").exists()
    assert not (v.root / "_meta" / "agent" / "SAFETY.md").exists()


def test_bootstrap_lite_idempotent_does_not_overwrite(isolated_vaults_root, isolated_target):
    """Re-running _bootstrap_lite must not overwrite user-edited files."""
    v = Vault.create("idem", isolated_target / "idem", bootstrap=True)
    custom = v.root / "_meta" / "system" / "RULES.md"
    custom.write_text("# My custom rules\n")
    Vault._bootstrap_lite(v.root)
    assert custom.read_text() == "# My custom rules\n"


# ─── bootstrap off (--no-bootstrap) ─────────────────────────


def test_no_bootstrap_creates_empty_dirs_but_no_template_files(
    isolated_vaults_root, isolated_target
):
    """--no-bootstrap creates empty content/ + _meta/ but no template files.

    v0.5.5+ silent-write fix: Vault.create() 가 log.md 를 보장하고 create entry 를
    1개 남기므로 --no-bootstrap 라도 log.md 가 존재한다 (silent write). 단, Lite
    bootstrap (SCHEMA/RULES) 은 여전히 복사되지 않음을 검증.
    """
    v = Vault.create("existing1", isolated_target / "existing1", bootstrap=False)
    assert (v.root / ".vault.json").is_file()
    assert (v.root / "content").is_dir()   # empty, exists
    assert (v.root / "_meta").is_dir()     # empty, exists
    # no Lite bootstrap templates copied
    assert not (v.root / "_meta" / "system" / "SCHEMA.md").exists()
    assert not (v.root / "_meta" / "system" / "RULES.md").exists()
    # silent-write fix: log.md is auto-created by Vault.create() with 1 create entry
    # (this is the v0.5.5+ behavior — log.md is now guaranteed, not a bootstrap artifact)
    assert (v.root / "log.md").is_file()
    entries = load(v)
    assert len(entries) == 1
    assert entries[0].action == "create"


def test_no_bootstrap_does_not_delete_existing(isolated_vaults_root, isolated_target):
    """If folder already has files, bootstrap=False must not touch them."""
    target = isolated_target / "existing2"
    target.mkdir()
    (target / "my-old-doc.md").write_text("# old\n")
    v = Vault.create("existing2", target, bootstrap=False)
    assert (target / "my-old-doc.md").read_text() == "# old\n"


# ─── sync_meta (Lite default, --full option) ────────────────


def test_sync_meta_lite_default(isolated_vaults_root, isolated_target):
    """sync_meta(lite=True) default — copies missing Lite user-facing files.

    v0.5.5+ silent-write fix: Vault.create() 가 log.md 를 보장하므로 sync_meta() 가
    다시 복사하지 않고 skipped 에 들어간다. 나머지 Lite 파일은 bootstrap=False 라 미존재
    → copied.
    """
    # bootstrap=False so SCHEMA/RULES don't exist yet
    v = Vault.create("sync1", isolated_target / "sync1", bootstrap=False)
    result = v.sync_meta()  # lite=True default
    assert "_meta/system/SCHEMA.md" in result["copied"]
    assert "_meta/system/RULES.md" in result["copied"]
    assert "_meta/system/AGENTS.md" in result["copied"]
    assert "_meta/agents/PROJECT-WORKFLOW.md" in result["copied"]
    # log.md already exists (silent-write by Vault.create) → skipped, not copied
    assert "log.md" not in result["copied"]
    assert "log.md" in result["skipped"]
    # No raven-internals
    assert "_meta/system/OPERATIONS.md" not in result["copied"]
    assert "_meta/agent/README.md" not in result["copied"]


def test_sync_meta_lite_no_op_when_already_bootstrapped(
    isolated_vaults_root, isolated_target
):
    """sync_meta(lite=True) on a Lite-bootstrapped vault = no-op (everything exists)."""
    v = Vault.create("sync1b", isolated_target / "sync1b", bootstrap=True)
    result = v.sync_meta()  # everything already exists
    assert result["copied"] == []
    # All Lite files in 'skipped' (because they exist)
    assert "_meta/system/SCHEMA.md" in result["skipped"]
    assert "_meta/system/RULES.md" in result["skipped"]
    assert "_meta/system/AGENTS.md" in result["skipped"]
    assert "_meta/agents/PROJECT-WORKFLOW.md" in result["skipped"]
    assert "log.md" in result["skipped"]


def test_sync_meta_does_not_overwrite_by_default(isolated_vaults_root, isolated_target):
    """sync_meta() default does NOT overwrite user-edited files."""
    v = Vault.create("sync2", isolated_target / "sync2", bootstrap=True)
    custom = v.root / "_meta" / "system" / "RULES.md"
    custom.write_text("# My custom rules\n")
    result = v.sync_meta()
    # Should be in 'skipped', not 'copied'
    assert "_meta/system/RULES.md" not in result["copied"]
    assert "_meta/system/RULES.md" in result["skipped"]
    assert custom.read_text() == "# My custom rules\n"


def test_sync_meta_full_copies_raven_internals(isolated_vaults_root, isolated_target):
    """v0.7.6+: sync_meta(full=True, force=True) = lite 5종 only (Tier 1 leak ❌).

    v0.7.1+ Lite bootstrap 정책: 사용자 vault는 도구 표면만.
    full 옵션은 deprecated (lite와 동일) — Tier 1 internal sync 거부.
    옛 테스트의 의도 (Tier 1 internal sync)는 v0.6.39+ Tier 1 leak 정책과 충돌.
    """
    v = Vault.create("sync3", isolated_target / "sync3", bootstrap=True)
    # With force=True, full mode now overwrites lite 5종 (Tier 1 internal ❌)
    result = v.sync_meta(lite=False, force=True)
    # Lite 5종만 복사
    assert "_meta/system/SCHEMA.md" in result["copied"]
    assert "_meta/system/RULES.md" in result["copied"]
    assert "_meta/system/AGENTS.md" in result["copied"]
    assert "_meta/agents/PROJECT-WORKFLOW.md" in result["copied"]
    assert "log.md" in result["copied"]
    # Tier 1 internal ❌ (v0.7.1+ Lite bootstrap 정책)
    assert "_meta/system/OPERATIONS.md" not in result["copied"]
    assert "_meta/agent/README.md" not in result["copied"]
    assert "_meta/agent/TOOLS.md" not in result["copied"]
    assert "_meta/agent/WORKFLOW.md" not in result["copied"]
    assert "_meta/agent/SAFETY.md" not in result["copied"]
    assert "raven-policy.md" not in result["copied"]


def test_sync_meta_full_refuses_to_overwrite_without_force(
    isolated_vaults_root, isolated_target
):
    """sync_meta(full=True) without --force must refuse if any target exists.

    v0.7.6+: lite와 동일 5종 기준. Tier 1 internal은 sync 대상 ❌.
    """
    v = Vault.create("sync4", isolated_target / "sync4", bootstrap=True)
    # Lite creates _meta/system/RULES.md
    assert (v.root / "_meta" / "system" / "RULES.md").is_file()
    # Full mode without force should raise (safety check)
    with pytest.raises(ValueError, match="force=True"):
        v.sync_meta(lite=False, force=False)


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


def test_is_llm_wiki_does_not_use_raw_folder_alone_as_signal(isolated_vaults_root, isolated_target):
    """raw/ alone is not enough to force strict LLM Wiki mode."""
    v = Vault.create("rawopt", isolated_target / "rawopt", bootstrap=False, profile="basic")
    assert v.is_llm_wiki is False
    (v.root / "raw").mkdir()
    assert v.is_llm_wiki is False


def test_is_llm_wiki_detects_agents_folder_without_feature_flag(isolated_vaults_root, isolated_target):
    """_meta/agents presence is also a structural opt-in signal."""
    v = Vault.create("agentopt", isolated_target / "agentopt", bootstrap=False, profile="basic")
    assert v.is_llm_wiki is False
    (v.root / "_meta" / "agents").mkdir(parents=True)
    assert v.is_llm_wiki is True


def test_is_llm_wiki_does_not_use_log_md_alone_as_signal(isolated_vaults_root, isolated_target):
    """log.md alone is operational noise, not enough to force LLM Wiki mode."""
    v = Vault.create("logonly", isolated_target / "logonly", bootstrap=False, profile="basic")
    (v.root / "log.md").write_text("# log\n", encoding="utf-8")
    assert v.is_llm_wiki is False


# ─── clone (data_only option) ───────────────────────────────


def test_clone_copies_content_only_with_data_only(isolated_vaults_root, isolated_target):
    """clone(data_only=True) copies content/ but skips _meta/ (no policy leak)."""
    src = Vault.create("src", isolated_target / "src", bootstrap=True)
    # Add some user content
    (src.root / "content" / "hello.md").write_text("# Hello\n")
    # Add a custom _meta/ file that shouldn't leak
    (src.root / "_meta" / "custom.md").write_text("# Custom\n")

    dst = Vault.clone(
        src,
        name="dst",
        path=isolated_target / "dst",
        data_only=True,
    )
    # content/ copied
    assert (dst.root / "content" / "hello.md").is_file()
    # _meta/ created (empty) but no copy of src's custom
    assert (dst.root / "_meta").is_dir()
    assert not (dst.root / "_meta" / "custom.md").exists()
    # _meta/system/SCHEMA.md NOT copied (data_only + no bootstrap)
    assert not (dst.root / "_meta" / "system" / "SCHEMA.md").exists()


def test_clone_copies_meta_by_default(isolated_vaults_root, isolated_target):
    """clone() default: content + _meta both copied."""
    src = Vault.create("src2", isolated_target / "src2", bootstrap=True)
    dst = Vault.clone(
        src,
        name="dst2",
        path=isolated_target / "dst2",
        copy_meta=True,
    )
    # _meta/system/ copied
    assert (dst.root / "_meta" / "system" / "SCHEMA.md").is_file()
    assert (dst.root / "_meta" / "system" / "RULES.md").is_file()
    # Note: even src has no raven-internals (Lite bootstrap), so dst has none either
    assert not (dst.root / "_meta" / "system" / "OPERATIONS.md").exists()
