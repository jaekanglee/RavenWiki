"""v0.7.67 (평가 A#4) — core.lock.FileLock의 stale lock 자동 회수 가드.

pre-v0.7.67 FileLock에는 소유자(PID/시각) 정보가 없어, 락을 쥔 프로세스가
죽으면 `<lock_dir>`가 영원히 남고 이후 모든 write가 timeout 뒤 실패했다
(수동으로 `.mcp/locks/` 삭제 전까지 복구 불가).
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from raven.core.lock import FileLock, lock_for_file


def test_acquire_and_release_writes_and_clears_owner(tmp_path: Path):
    lock_dir = tmp_path / "x.lock"
    with FileLock(lock_dir) as lock:
        assert lock.acquired
        assert (lock_dir / "owner").exists()
    assert not lock_dir.exists()  # released + cleaned up


def test_reclaims_lock_held_by_dead_pid(tmp_path: Path):
    lock_dir = tmp_path / "x.lock"
    lock_dir.mkdir()
    dead_pid = 999999  # astronomically unlikely to be a live process
    (lock_dir / "owner").write_text(f"{dead_pid}:{time.time()}", encoding="utf-8")

    # Would previously block for `timeout` seconds then raise TimeoutError.
    with FileLock(lock_dir, timeout=2.0) as lock:
        assert lock.acquired


def test_reclaims_lock_older_than_stale_after(tmp_path: Path):
    lock_dir = tmp_path / "x.lock"
    lock_dir.mkdir()
    # Alive PID (our own), but acquired long ago.
    old_ts = time.time() - 120
    (lock_dir / "owner").write_text(f"{os.getpid()}:{old_ts}", encoding="utf-8")

    with FileLock(lock_dir, timeout=2.0, stale_after=1.0) as lock:
        assert lock.acquired


def test_does_not_reclaim_fresh_lock_held_by_live_pid(tmp_path: Path):
    lock_dir = tmp_path / "x.lock"
    lock_dir.mkdir()
    (lock_dir / "owner").write_text(f"{os.getpid()}:{time.time()}", encoding="utf-8")

    with pytest.raises(TimeoutError):
        with FileLock(lock_dir, timeout=0.3, stale_after=60.0):
            pass


def test_reclaims_lock_with_missing_owner_file_after_stale_after(tmp_path: Path):
    """No owner file at all (e.g. crash mid-write_owner) — fall back to dir mtime."""
    lock_dir = tmp_path / "x.lock"
    lock_dir.mkdir()
    old = time.time() - 120
    os.utime(lock_dir, (old, old))

    with FileLock(lock_dir, timeout=2.0, stale_after=1.0) as lock:
        assert lock.acquired


def test_lock_for_file_survives_reclaim_end_to_end(tmp_path: Path):
    vault_root = tmp_path
    target = vault_root / "content" / "page.md"
    target.parent.mkdir(parents=True)
    target.write_text("v1", encoding="utf-8")

    stuck = lock_for_file(vault_root, target, timeout=1.0)
    stuck.lock_dir.mkdir(parents=True, exist_ok=True)
    (stuck.lock_dir / "owner").write_text(f"999999:{time.time()}", encoding="utf-8")

    fresh = lock_for_file(vault_root, target, timeout=2.0)
    with fresh:
        assert fresh.acquired
