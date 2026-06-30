"""Tests for Lite Tier 1↔2 boundary enforcement (M4 F10).

Tier 1 (raven package internal — never copied to vault):
    _meta/system/OPERATIONS.md
    _meta/agent/* (README, TOOLS, WORKFLOW, SAFETY)
    raven-policy.md

Tier 2 (user vault — Lite bootstrap):
    _meta/system/SCHEMA.md
    _meta/system/RULES.md
    _meta/system/README.md
    _meta/agents/PROJECT-WORKFLOW.md
    log.md

These tests guarantee:
  - `_LITE_BOOTSTRAP_FILES` never includes Tier 1 paths.
  - `Vault.clone()` (default + data_only) never copies Tier 1 files.
  - `Vault.sync_meta(lite=True)` never lists Tier 1 paths.
  - `Vault.create()` never leaks Tier 1 files even if source vault has them.
  - The Tier 1 `agent/` directory is never created during bootstrap.
  - Bootstrap target paths use approved Tier 2 locations.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core.vault import Vault, _LITE_BOOTSTRAP_FILES
from raven.core.registry import registry


# ─── Tier 1 reference set (single source of truth for these tests) ───

TIER1_FILES: tuple[str, ...] = (
    "_meta/system/OPERATIONS.md",
    "_meta/agent/README.md",
    "_meta/agent/TOOLS.md",
    "_meta/agent/WORKFLOW.md",
    "_meta/agent/SAFETY.md",
    "raven-policy.md",
)


# ─── fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def isolated_vaults_root(monkeypatch):
    """Redirect WIKI_VAULTS_DIR so registry doesn't touch real vaults."""
    tmp = Path(tempfile.mkdtemp(prefix="raven-tier-test-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def isolated_target(monkeypatch):
    """Separate temp dir for the actual vault path (not the registry root)."""
    tmp = Path(tempfile.mkdtemp(prefix="raven-tier-target-"))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


# ─── tests: whitelist purity ────────────────────────────────────────


def test_lite_bootstrap_files_excludes_tier1():
    """`_LITE_BOOTSTRAP_FILES` MUST NOT contain any Tier 1 path.

    This is the single source of truth for "what gets bootstrapped into a
    user vault". If a Tier 1 path sneaks in here, every downstream
    guarantee (clone, sync_meta, create) is silently violated.
    """
    for tier1 in TIER1_FILES:
        assert tier1 not in _LITE_BOOTSTRAP_FILES, (
            f"Tier 1 leak in _LITE_BOOTSTRAP_FILES: {tier1!r}"
        )


def test_lite_bootstrap_files_size_matches_documented_whitelist():
    """Sanity: the whitelist must be the canonical user-facing Lite set."""
    canonical_lite = {
        "_meta/system/SCHEMA.md",
        "_meta/system/RULES.md",
        "_meta/system/README.md",
        "_meta/agents/PROJECT-WORKFLOW.md",
        "log.md",
    }
    # Every entry in the whitelist must be in the canonical Lite set
    # (no Tier 1, no surprise files).
    for path in _LITE_BOOTSTRAP_FILES:
        assert path in canonical_lite, (
            f"_LITE_BOOTSTRAP_FILES contains unexpected entry: {path!r}. "
            f"Allowed: {sorted(canonical_lite)}"
        )


# ─── tests: clone() excludes Tier 1 ─────────────────────────────────


def test_clone_default_excludes_tier1(isolated_vaults_root, isolated_target):
    """`Vault.clone()` default (no copy_meta): only content/ is copied.

    Tier 1 can't leak because src's _meta/ is never copied.
    """
    src = Vault.create("src", isolated_target / "src", bootstrap=True)
    dst = Vault.clone(src, name="dst", path=isolated_target / "dst")
    for tier1 in TIER1_FILES:
        assert not (dst.root / tier1).exists(), f"Tier 1 leak in clone: {tier1}"


def test_clone_data_only_excludes_tier1(isolated_vaults_root, isolated_target):
    """`Vault.clone(data_only=True)`: explicit content-only mode.

    Even more conservative than default — must also exclude Tier 1.
    """
    src = Vault.create("src_do", isolated_target / "src_do", bootstrap=True)
    dst = Vault.clone(
        src, name="dst_do", path=isolated_target / "dst_do", data_only=True
    )
    for tier1 in TIER1_FILES:
        assert not (dst.root / tier1).exists(), f"Tier 1 leak in clone(data_only): {tier1}"
    # And dst has no _meta/system/ files at all (data_only skips _meta entirely)
    assert not (dst.root / "_meta" / "system" / "SCHEMA.md").exists()


def test_clone_with_tier1_in_src_still_excluded_by_default(
    isolated_vaults_root, isolated_target
):
    """Even if src vault somehow has Tier 1 files (e.g., via --copy-meta
    leakage from dev workflow), default clone() must NOT copy them.

    This protects against a "polluted source vault" scenario where Tier 1
    docs leaked into a vault via `raven meta sync --full --force`.
    """
    src = Vault.create("polluted", isolated_target / "polluted", bootstrap=True)
    # Inject Tier 1 files into src (simulates prior full-sync leak)
    for tier1 in TIER1_FILES:
        target = src.root / tier1
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# leaked: {tier1}\n")

    # Default clone (no copy_meta) → _meta/ not copied → no Tier 1 leak
    dst = Vault.clone(
        src, name="dst_clean", path=isolated_target / "dst_clean"
    )
    for tier1 in TIER1_FILES:
        assert not (dst.root / tier1).exists(), (
            f"Tier 1 leaked from src to dst: {tier1} (default clone)"
        )


# ─── tests: sync_meta(lite=True) excludes Tier 1 ───────────────────


def test_sync_meta_lite_excludes_tier1(isolated_vaults_root, isolated_target):
    """`sync_meta(lite=True)` (default) MUST NOT include Tier 1 paths.

    Inspect both the file_map shape (via result["copied"]) AND confirm
    nothing Tier 1 actually lands in the vault.
    """
    v = Vault.create("sync_t1", isolated_target / "sync_t1", bootstrap=False)
    result = v.sync_meta()  # lite=True default
    for tier1 in TIER1_FILES:
        assert tier1 not in result["copied"], f"sync_meta(lite) copied Tier 1: {tier1}"
        assert tier1 not in result["skipped"], f"sync_meta(lite) skipped Tier 1: {tier1}"
        assert not (v.root / tier1).exists(), f"Tier 1 exists after sync_meta(lite): {tier1}"


# ─── tests: Vault.create() does not leak Tier 1 ────────────────────


def test_create_with_bootstrap_only_tier2(isolated_vaults_root, isolated_target):
    """`Vault.create(bootstrap=True)` produces a pure Tier 2 vault.

    Tier 1 paths MUST be absent on disk immediately after create returns.
    """
    v = Vault.create("pure", isolated_target / "pure", bootstrap=True)
    for tier1 in TIER1_FILES:
        assert not (v.root / tier1).exists(), (
            f"Tier 1 leaked into fresh vault via Vault.create: {tier1}"
        )


# ─── tests: structural guarantees ──────────────────────────────────


def test_tier1_dir_not_in_bootstrap(isolated_vaults_root, isolated_target):
    """The `agent/` directory MUST NOT exist in a freshly-bootstrapped vault.

    Tier 1 directory existence is itself a leak signal — even if all its
    files are empty, `agent/` is raven-internal namespace.
    """
    v = Vault.create("nodir", isolated_target / "nodir", bootstrap=True)
    assert not (v.root / "_meta" / "agent").exists(), (
        "Tier 1 directory `_meta/agent/` was created during Lite bootstrap"
    )
    assert not (v.root / "agent").exists(), (
        "Top-level `agent/` was created during Lite bootstrap"
    )


def test_bootstrap_path_constants_use_user_surface_dirs():
    """All Lite bootstrap paths MUST live under approved Tier 2 locations."""
    allowed_files = {
        "_meta/system/SCHEMA.md",
        "_meta/system/RULES.md",
        "_meta/system/README.md",
        "_meta/agents/PROJECT-WORKFLOW.md",
        "log.md",
    }
    for path in _LITE_BOOTSTRAP_FILES:
        assert path in allowed_files, (
            f"Bootstrap path {path!r} is not an approved Tier 2 user-surface file."
        )


def test_tier1_files_absent_after_full_sync_with_lite_default_unchanged(
    isolated_vaults_root, isolated_target
):
    """Calling `sync_meta(lite=True)` repeatedly must never introduce Tier 1.

    This guards against a future regression where someone changes the
    default of `lite=` from True to False.
    """
    v = Vault.create("guard", isolated_target / "guard", bootstrap=True)
    # Run sync_meta a few times — lite default should be sticky
    for _ in range(3):
        v.sync_meta()  # default lite=True
    for tier1 in TIER1_FILES:
        assert not (v.root / tier1).exists()
