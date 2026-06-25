"""wikisys.core.lint — vault-aware lint runner.

Wraps `scripts/lint.py`. Counts critical/warning/info issues per vault.

v0.5.0 additions:
    - log_size check (#12 of 12): log.md > 500 entries → info
    - log existence check: log.md 없으면 info (카파시 가이드)

v0.5.1+ planned: orphan, contradictions, confidence, stale, page size,
                 tag audit, frontmatter completeness, index completeness.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .vault import Vault


# Karpathy guide: rotate log when > 500 entries
LOG_ROTATE_THRESHOLD = 500


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
    # Append our own log_size check (v0.5.0+ #12)
    log_issues = check_log_size(vault)
    counts["info"] += log_issues["info"]
    counts["total"] += log_issues["info"]
    return {
        "ok": result.returncode == 0,
        "vault": vault.meta.name,
        "counts": counts,
        "returncode": result.returncode,
        "output_tail": text[-800:],
        "log_issues": log_issues,
    }


def _inline_scan(vault: Vault) -> dict:
    """Tiny fallback: count broken wikilinks + missing frontmatter + log issues."""
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
    log_issues = check_log_size(vault)
    return {
        "ok": True,
        "vault": vault.meta.name,
        "counts": {
            "critical": broken + no_front,
            "warning": 0,
            "info": len(pages) + log_issues["info"],
            "total": broken + no_front + len(pages) + log_issues["info"],
        },
        "mode": "inline",
        "log_issues": log_issues,
    }


# ────────────────────────── v0.5.0+ 추가 검사 ──────────────────────────


def check_log_size(vault: Vault) -> dict:
    """log.md size check (lint #12, 카파시 가이드).

    Returns:
        {"info": N, "exists": bool, "entries": M, "needs_rotate": bool}

    Rules:
        - log.md 없음 → info 0 (bootstrap이 알아서 만듦)
        - entries >= 500 → info +1 (rotation 권장)
        - entries < 500 → info 0
    """
    from . import log as _log
    path = _log.log_path(vault)
    if not path.exists():
        return {"info": 0, "exists": False, "entries": 0, "needs_rotate": False}
    entries = _log.count(vault)
    needs_rotate = entries >= LOG_ROTATE_THRESHOLD
    return {
        "info": 1 if needs_rotate else 0,
        "exists": True,
        "entries": entries,
        "needs_rotate": needs_rotate,
        "threshold": LOG_ROTATE_THRESHOLD,
    }
