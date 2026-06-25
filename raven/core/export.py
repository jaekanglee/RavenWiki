"""raven.core.export — vault-aware static JSON export for the GUI.

Wraps `scripts/export_static.py` so any vault can produce its dashboard JSON
bundle (index.json, tree.json, graph.json, search.idx.json, page-<slug>.json).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .vault import Vault


def export_static(
    vault: Vault,
    out_dir: Optional[Path] = None,
) -> dict:
    """Run scripts/export_static.py against `vault`.

    Args:
        vault: source vault.
        out_dir: where to write JSON files (default: <repo>/dashboard/public/api).
    """
    repo_root = _repo_root()
    if out_dir is None and repo_root:
        out_dir = repo_root / "dashboard" / "public" / "api"
    if out_dir is None:
        raise ValueError("out_dir required when repo_root not found")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    script = repo_root / "scripts" / "export_static.py" if repo_root else None
    if script and script.exists():
        return _run_legacy(script, vault, out_dir)
    return {"ok": False, "reason": "scripts/export_static.py missing"}


def _repo_root() -> Optional[Path]:
    return Path(__file__).resolve().parents[2]


def _run_legacy(script: Path, vault: Vault, out_dir: Path) -> dict:
    argv = [sys.executable, str(script), str(vault.root), "--out", str(out_dir)]
    env = os.environ.copy()
    result = subprocess.run(argv, capture_output=True, text=True, env=env)
    return {
        "ok": result.returncode == 0,
        "vault": vault.meta.name,
        "out_dir": str(out_dir),
        "stdout_tail": result.stdout[-500:] if result.stdout else "",
        "stderr_tail": result.stderr[-500:] if result.stderr else "",
        "returncode": result.returncode,
    }
