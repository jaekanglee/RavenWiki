"""Tests for raven.core.archive — archive list/clean/restore."""
from __future__ import annotations

import datetime as _dt
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core.archive import (
    ARCHIVE_TS_RE,
    CleanResult,
    clean_archived,
    list_archived,
    restore_archived,
)
from raven.core.vault import Vault


@pytest.fixture
def isolated_env(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-archive-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-archive-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("test", target_root / "test", bootstrap=False)
    yield {"reg_root": reg_root, "target_root": target_root, "vault": v}
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def _make_archived(vault_root: Path, original_slug: str, ts: _dt.datetime) -> Path:
    """Create an archived file at the correct mirror path with given timestamp."""
    ts_str = ts.strftime("%Y%m%d-%H%M%S")
    parts = original_slug.split("/")
    stem = parts[-1]
    parent_dir = vault_root / "_archive" / "/".join(parts[:-1])
    parent_dir.mkdir(parents=True, exist_ok=True)
    fp = parent_dir / f"{stem}-{ts_str}.md"
    fp.write_text(f"# archived from {original_slug}\n", encoding="utf-8")
    return fp


# ─── list_archived ──────────────────────────────────────────


def test_list_empty(isolated_env):
    entries = list_archived(isolated_env["vault"])
    assert entries == []


def test_list_single(isolated_env):
    v = isolated_env["vault"]
    ts = _dt.datetime.now()
    _make_archived(v.root, "content/foo", ts)
    entries = list_archived(v)
    assert len(entries) == 1
    e = entries[0]
    assert e.original_slug == "content/foo"
    assert e.timestamp is not None
    assert e.age_days is not None
    assert e.age_days < 1.0


def test_list_multiple_nested(isolated_env):
    v = isolated_env["vault"]
    now = _dt.datetime.now()
    _make_archived(v.root, "content/foo", now)
    _make_archived(v.root, "content/sub/bar", now)
    _make_archived(v.root, "_meta/old-rule", now - _dt.timedelta(days=60))
    entries = list_archived(v)
    slugs = sorted(e.original_slug for e in entries)
    assert slugs == ["_meta/old-rule", "content/foo", "content/sub/bar"]


def test_list_preserves_relative_path(isolated_env):
    v = isolated_env["vault"]
    _make_archived(v.root, "content/sub/nested", _dt.datetime.now())
    entries = list_archived(v)
    # Verify the rel_path matches the expected pattern
    import re
    assert re.match(
        r"^_archive/content/sub/nested-\d{8}-\d{6}\.md$",
        entries[0].rel_path,
    )


# ─── clean_archived (dry-run) ───────────────────────────────


def test_clean_dry_run_does_not_delete(isolated_env):
    v = isolated_env["vault"]
    fp = _make_archived(v.root, "content/foo", _dt.datetime.now() - _dt.timedelta(days=10))
    assert fp.exists()
    result = clean_archived(v, older_than_days=5, apply=False)
    assert result.dry_run is True
    assert len(result.would_delete) == 1
    assert len(result.deleted) == 0
    assert fp.exists()  # still there


def test_clean_skips_recent(isolated_env):
    v = isolated_env["vault"]
    old_fp = _make_archived(v.root, "content/old", _dt.datetime.now() - _dt.timedelta(days=100))
    new_fp = _make_archived(v.root, "content/recent", _dt.datetime.now() - _dt.timedelta(days=1))
    result = clean_archived(v, older_than_days=30, apply=False)
    slugs = [e.original_slug for e in result.would_delete]
    assert "content/old" in slugs
    assert "content/recent" not in slugs
    # both files still exist (dry-run)
    assert old_fp.exists()
    assert new_fp.exists()


def test_clean_zero_days_includes_all(isolated_env):
    """older_than_days=0 means 'delete everything in _archive/'."""
    v = isolated_env["vault"]
    _make_archived(v.root, "content/a", _dt.datetime.now())
    _make_archived(v.root, "content/b", _dt.datetime.now() - _dt.timedelta(days=2))
    result = clean_archived(v, older_than_days=0, apply=False)
    assert len(result.would_delete) == 2


# ─── clean_archived (apply) ─────────────────────────────────


def test_clean_apply_deletes(isolated_env):
    v = isolated_env["vault"]
    old_fp = _make_archived(v.root, "content/old", _dt.datetime.now() - _dt.timedelta(days=100))
    keep_fp = _make_archived(v.root, "content/keep", _dt.datetime.now() - _dt.timedelta(days=1))
    result = clean_archived(v, older_than_days=30, apply=True)
    assert result.dry_run is False
    assert len(result.deleted) == 1
    assert not old_fp.exists()
    assert keep_fp.exists()


def test_clean_apply_cleans_empty_parents(isolated_env):
    """After deleting the only file in _archive/content/sub/, the empty
    sub/ dir is removed (content/ may or may not survive — both are valid)."""
    v = isolated_env["vault"]
    _make_archived(v.root, "content/sub/only", _dt.datetime.now() - _dt.timedelta(days=100))
    assert (v.root / "_archive" / "content" / "sub").exists()
    clean_archived(v, older_than_days=30, apply=True)
    # sub/ must be gone (was empty after file removal)
    assert not (v.root / "_archive" / "content" / "sub").exists()
    # _archive/ itself must still exist (we never delete the root)
    assert (v.root / "_archive").exists()


# ─── restore_archived ───────────────────────────────────────


def test_restore_basic(isolated_env):
    v = isolated_env["vault"]
    fp = _make_archived(v.root, "content/foo", _dt.datetime.now())
    rel = str(fp.relative_to(v.root))
    result = restore_archived(v, rel)
    assert result.ok, result.error
    assert result.original_slug == "content/foo"
    assert (v.root / "content" / "foo.md").is_file()
    assert not fp.exists()  # moved


def test_restore_nested_path(isolated_env):
    v = isolated_env["vault"]
    fp = _make_archived(v.root, "content/sub/nested", _dt.datetime.now())
    rel = str(fp.relative_to(v.root))
    result = restore_archived(v, rel)
    assert result.ok, result.error
    assert (v.root / "content" / "sub" / "nested.md").is_file()


def test_restore_target_exists_rejected(isolated_env):
    """If original target exists, refuse to overwrite."""
    v = isolated_env["vault"]
    fp = _make_archived(v.root, "content/foo", _dt.datetime.now())
    # Pre-create the target
    (v.root / "content").mkdir(exist_ok=True)
    (v.root / "content" / "foo.md").write_text("# exists\n", encoding="utf-8")
    result = restore_archived(v, str(fp.relative_to(v.root)))
    assert not result.ok
    assert "already exists" in result.error
    # Both files still exist (rejected)
    assert fp.exists()
    assert (v.root / "content" / "foo.md").exists()


def test_restore_by_slug_picks_latest(isolated_env):
    """v0.7.66 (평가 P1#7): 원래 slug로 복원 — 여러 벌이면 최신본."""
    v = isolated_env["vault"]
    old = _make_archived(v.root, "content/foo", _dt.datetime(2026, 1, 1, 0, 0, 0))
    new = _make_archived(v.root, "content/foo", _dt.datetime(2026, 6, 1, 0, 0, 0))
    result = restore_archived(v, "content/foo")
    assert result.ok, result.error
    assert (v.root / "content" / "foo.md").is_file()
    assert not new.exists()  # 최신본이 이동됨
    assert old.exists()      # 구본은 그대로


def test_restore_by_slug_without_archive_fails_clearly(isolated_env):
    v = isolated_env["vault"]
    result = restore_archived(v, "content/ghost")
    assert not result.ok
    assert "no archived file" in result.error


def test_restore_missing_file(isolated_env):
    v = isolated_env["vault"]
    result = restore_archived(v, "_archive/content/ghost-20260625-000000.md")
    assert not result.ok
    assert "not found" in result.error


# ─── filename pattern ───────────────────────────────────────


def test_archive_ts_regex():
    assert ARCHIVE_TS_RE.search("foo-20260625-123456.md")
    assert ARCHIVE_TS_RE.search("content/sub/bar-20260101-000000.md")
    assert not ARCHIVE_TS_RE.search("foo.md")  # no timestamp
    assert not ARCHIVE_TS_RE.search("foo-20260625.md")  # wrong format


# ─── CleanResult shape ──────────────────────────────────────


def test_clean_result_to_dict(isolated_env):
    v = isolated_env["vault"]
    _make_archived(v.root, "content/x", _dt.datetime.now() - _dt.timedelta(days=100))
    r = clean_archived(v, older_than_days=30, apply=False)
    d = r.to_dict()
    assert d["ok"] is True
    assert d["dry_run"] is True
    assert d["would_delete_count"] == 1
    assert d["deleted_count"] == 0
    assert "errors" in d
