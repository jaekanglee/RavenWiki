"""wikisys.core.lint — vault-aware lint runner.

Wraps `scripts/lint.py`. Counts critical/warning/info issues per vault.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .vault import Vault


def run_lint(vault: Vault) -> dict:
    """Run scripts/lint.py for `vault` and return a counts dict.

    Falls back to a fast inline scan if the legacy script is absent.
    """
    repo_root = _repo_root()
    script = repo_root / "scripts" / "lint.py" if repo_root else None
    if script and script.exists():
        return _run_legacy(script, vault)
    return _inline_scan(vault)


def _repo_root() -> Optional[Path]:
    return Path(__file__).resolve().parents[2]


def _run_legacy(script: Path, vault: Vault) -> dict:
    argv = [sys.executable, str(script), str(vault.root)]
    env = os.environ.copy()
    result = subprocess.run(argv, capture_output=True, text=True, env=env)
    text = (result.stdout or "") + (result.stderr or "")
    counts = {"critical": 0, "warning": 0, "info": 0, "total": 0}
    m = re.search(r"(\d+)\s*critical,\s*(\d+)\s*warning,\s*(\d+)\s*info,\s*(\d+)\s*total", text)
    if m:
        counts = {k: int(v) for k, v in zip(["critical", "warning", "info", "total"], m.groups())}
    return {
        "ok": result.returncode == 0,
        "vault": vault.meta.name,
        "counts": counts,
        "returncode": result.returncode,
        "output_tail": text[-800:],
    }


def _inline_scan(vault: Vault) -> dict:
    """Tiny fallback: count broken wikilinks + missing frontmatter."""
    broken = 0
    no_front = 0
    pages = list(vault.content_root.rglob("*.md"))
    for p in pages:
        text = p.read_text(errors="replace")
        if not text.startswith("---"):
            no_front += 1
        for m in re.finditer(r"\[\[([^\[\]\n]+?)\]\]", text):
            tgt = m.group(1).strip().split("|")[0]
            if "/" in tgt:
                if not (vault.root / f"{tgt}.md").exists():
                    broken += 1
    return {
        "ok": True,
        "vault": vault.meta.name,
        "counts": {
            "critical": broken + no_front,
            "warning": 0,
            "info": len(pages),
            "total": broken + no_front + len(pages),
        },
        "mode": "inline",
    }
