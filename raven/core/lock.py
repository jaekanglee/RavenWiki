"""lock.py — atomic directory-based file lock helper for concurrent write path.

Provides cross-platform advisory locks utilizing OS-level atomic mkdir operations.
"""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path


class FileLock:
    """Cross-platform directory-based locker."""

    def __init__(self, lock_dir: Path, timeout: float = 5.0, delay: float = 0.05):
        self.lock_dir = lock_dir
        self.timeout = timeout
        self.delay = delay
        self.acquired = False

    def __enter__(self) -> FileLock:
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            try:
                self.lock_dir.mkdir(parents=True, exist_ok=False)
                self.acquired = True
                return self
            except FileExistsError:
                time.sleep(self.delay)
        raise TimeoutError(
            f"Could not acquire lock on {self.lock_dir} after {self.timeout}s"
        )

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: object | None) -> None:
        if self.acquired:
            try:
                # Clean up the lock directory.
                self.lock_dir.rmdir()
            except OSError:
                pass


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
