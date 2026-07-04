"""raven.core.git — thin subprocess wrapper for read-only git introspection.

Relocated from `raven/api/server.py` (v0.7.68, 평가 B#3) — a pure function
with no FastAPI/HTTP dependency, so it belongs in core alongside the rest
of the read-only vault introspection helpers.
"""
from __future__ import annotations

import shutil
import subprocess


def run_git(cwd: str, args: list[str]) -> tuple[bool, str]:
    """Run `git <args>` in `cwd`. Returns (success, stdout-or-stderr)."""
    if not shutil.which("git"):
        return False, "git binary not found on the server"
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            errors="replace",
        )
        if res.returncode != 0:
            return False, res.stderr.strip()
        return True, res.stdout
    except Exception as e:
        return False, str(e)
