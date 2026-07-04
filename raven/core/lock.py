"""lock.py — atomic directory-based file lock helper for concurrent write path.

Provides cross-platform advisory locks utilizing OS-level atomic mkdir operations.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
import time
from pathlib import Path


# v0.7.67 (평가 A#4): stale lock 자동 회수 기본 임계값.
# 이 시간을 넘긴 락은 소유 PID가 죽었거나 너무 오래 걸린 것으로 보고 강탈한다.
DEFAULT_STALE_AFTER = 60.0


class FileLock:
    """Cross-platform directory-based locker.

    v0.7.67 (평가 A#4): pre-v0.7.67에는 락 소유자 정보(PID/시각)가 전혀 기록되지
    않아, 락을 쥔 프로세스가 크래시하면 `<lock_dir>`가 영원히 남고 이후 모든
    write가 `timeout` 뒤 TimeoutError로 실패했다 (수동으로 `.mcp/locks/` 삭제
    전까지 복구 불가). 이제 락 획득 시 `<lock_dir>/owner`에 `pid:timestamp`를
    기록하고, 획득 실패 시 그 소유자가 (a) 죽은 PID이거나 (b) `stale_after`를
    넘겼으면 강탈한다.
    """

    def __init__(
        self,
        lock_dir: Path,
        timeout: float = 5.0,
        delay: float = 0.05,
        stale_after: float = DEFAULT_STALE_AFTER,
    ):
        self.lock_dir = lock_dir
        self.timeout = timeout
        self.delay = delay
        self.stale_after = stale_after
        self.acquired = False

    def __enter__(self) -> FileLock:
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            try:
                self.lock_dir.mkdir(parents=True, exist_ok=False)
                self.acquired = True
                self._write_owner()
                return self
            except FileExistsError:
                if self._reclaim_if_stale():
                    continue  # stale lock removed — retry immediately
                time.sleep(self.delay)
        raise TimeoutError(
            f"Could not acquire lock on {self.lock_dir} after {self.timeout}s"
        )

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: object | None) -> None:
        if self.acquired:
            try:
                owner = self.lock_dir / "owner"
                if owner.exists():
                    owner.unlink()
                # Clean up the lock directory.
                self.lock_dir.rmdir()
            except OSError:
                pass

    def _write_owner(self) -> None:
        try:
            (self.lock_dir / "owner").write_text(
                f"{os.getpid()}:{time.time()}", encoding="utf-8"
            )
        except OSError:
            pass  # best-effort — a missing owner file just disables staleness detection

    def _reclaim_if_stale(self) -> bool:
        """Return True if a stale lock was removed (caller should retry now)."""
        owner_path = self.lock_dir / "owner"
        try:
            raw = owner_path.read_text(encoding="utf-8")
            pid_str, _, ts_str = raw.partition(":")
            pid = int(pid_str)
            acquired_at = float(ts_str)
        except (OSError, ValueError):
            # No/unreadable owner file: can't tell who holds it or since when.
            # Only reclaim once the lock dir's own mtime exceeds stale_after —
            # avoids reclaiming a lock acquired a split-second ago (write_owner
            # hasn't landed yet).
            try:
                age = time.time() - self.lock_dir.stat().st_mtime
            except OSError:
                return False
            if age < self.stale_after:
                return False
            return self._rmtree_lock_dir()

        pid_alive = _pid_alive(pid)
        age = time.time() - acquired_at
        if pid_alive and age < self.stale_after:
            return False
        return self._rmtree_lock_dir()

    def _rmtree_lock_dir(self) -> bool:
        try:
            owner = self.lock_dir / "owner"
            if owner.exists():
                owner.unlink()
            self.lock_dir.rmdir()
            return True
        except OSError:
            return False


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # process exists, just owned by someone else
    except OSError:
        return False
    return True


def atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Write `content` to `path` atomically (tmp file + os.replace).

    v0.7.67 (평가 A#4/B#6): pre-v0.7.67 page/log writes used a plain
    `path.write_text(...)` — a crash or kill mid-write left a truncated
    file (SoT corruption for pages; a torn log.md for readers that don't
    take the write lock, like digest/lint). `os.replace` is atomic on the
    same filesystem, so a reader always sees either the old or the new
    content in full, never a partial write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding) as fh:
            fh.write(content)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def lock_for_file(vault_root: Path, file_path: Path, timeout: float = 5.0) -> FileLock:
    """Create a FileLock bound to a specific file's absolute path hash.

    Stores lock states under `<vault>/.mcp/locks/` to avoid polluting the workspace
    and to prevent conflict with other files.
    """
    hasher = hashlib.sha256(str(file_path.resolve()).encode("utf-8"))
    lock_name = hasher.hexdigest()[:16] + ".lock"
    # Keep lock files under the .mcp folder which is ignored by git
    locks_base = vault_root / ".mcp" / "locks"
    return FileLock(locks_base / lock_name, timeout=timeout)
