"""raven.core.db — vault-aware SQLite index builder.

Wraps `scripts/build_db.py` so any vault can rebuild its own wiki.db.

Strategy:
    - The original `scripts/build_db.py` is a stable 293-line script that takes
      a vault path and an optional --db output. We don't rewrite it; we just
      invoke it as a subprocess with the right argv.
    - This file is the public face used by `raven.cli.build` and the API.
    - Falls back to a minimal inline build if the script is missing (e.g. when
      installed as a package without the `scripts/` dir).
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .vault import Vault


# ────────────────────────── public API ──────────────────────────


def build_db(vault: Vault, db_path: Optional[Path] = None, *, run_lint: bool = True) -> dict:
    """Rebuild the wiki.db index for `vault`. Returns a small status dict.

    Args:
        vault: the active vault handle (root + meta).
        db_path: where to write the DB (default: <vault>/wiki.db).
        run_lint: build 직후 lint 14개 자동 실행. 기본 True.

    Side effect: appends a `build` entry to log.md on success or failure.
    """
    db_path = Path(db_path) if db_path else vault.db_path
    repo_root = _repo_root()
    script = repo_root / "scripts" / "build_db.py" if repo_root else None
    if script and script.exists():
        result = _run_legacy_build(script, vault, db_path)
    else:
        result = _inline_build(vault, db_path)

    # log.md에 build entry 자동 append (실패해도 계속)
    try:
        from . import log as _log
        status = "ok" if result.get("ok") else "fail"
        pages = result.get("pages") or "?"
        _log.append(
            vault,
            action="build",
            subject=f"wiki.db rebuild ({status}, {pages} pages)",
            extra={"db": str(db_path), "returncode": str(result.get("returncode", "?"))},
        )
    except Exception:
        # log append 실패는 무시 — build 자체엔 영향 ❌
        pass

    # ─── index.md 마크다운 카탈로그 자동 컴파일 (v0.7.27) ───
    if result.get("ok"):
        try:
            from .index_builder import build_index
            build_index(vault)
        except Exception as e:
            result["index_error"] = f"{type(e).__name__}: {e}"

    # build 직후 lint 14개 자동 실행
    if run_lint:
        try:
            from . import lint as _lint
            lint_result = _lint.run_all(vault)
            result["lint"] = lint_result
        except Exception as e:
            result["lint_error"] = f"{type(e).__name__}: {e}"

    return result


def connect(vault: Vault) -> sqlite3.Connection:
    """Open a read-only connection to vault's wiki.db (build it if missing)."""
    if not vault.db_path.exists():
        build_db(vault)
    return sqlite3.connect(f"file:{vault.db_path}?mode=ro", uri=True)


# ────────────────────────── internals ──────────────────────────


def _repo_root() -> Optional[Path]:
    """Locate the raven code repo (parent of `raven/`)."""
    # raven/core/db.py → parents[2] = repo root
    return Path(__file__).resolve().parents[2]


def _run_legacy_build(script: Path, vault: Vault, db_path: Path) -> dict:
    """Invoke scripts/build_db.py with vault path + db output."""
    argv = [sys.executable, str(script), str(vault.root), "--db", str(db_path)]
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", "")
    result = subprocess.run(argv, capture_output=True, text=True, env=env)
    return {
        "ok": result.returncode == 0,
        "vault": vault.meta.name,
        "db_path": str(db_path),
        "stdout_tail": result.stdout[-500:] if result.stdout else "",
        "stderr_tail": result.stderr[-500:] if result.stderr else "",
        "returncode": result.returncode,
    }


def _inline_build(vault: Vault, db_path: Path) -> dict:
    """Minimal fallback: if scripts/build_db.py is gone, walk content/ and
    build a tiny SQLite index with pages + tags + links tables.

    Used by installed-package scenarios. Not the canonical path; the real
    builder is scripts/build_db.py.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(
        """
        CREATE TABLE pages (
          slug TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          type TEXT NOT NULL DEFAULT 'concept',
          path TEXT NOT NULL,
          content TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE tags (page_slug TEXT NOT NULL, tag TEXT NOT NULL,
                           PRIMARY KEY (page_slug, tag));
        CREATE TABLE links (source_slug TEXT NOT NULL, target_slug TEXT NOT NULL,
                            PRIMARY KEY (source_slug, target_slug));
        """
    )
    n_pages = 0
    for fp in vault.content_root.rglob("*.md"):
        slug = str(fp.relative_to(vault.root))[:-3]
        text = fp.read_text(errors="replace")
        title = slug.split("/")[-1]
        if text.startswith("---"):
            try:
                fm = text.split("---", 2)[1]
                for line in fm.splitlines():
                    if line.startswith("title:"):
                        title = line.split(":", 1)[1].strip()
            except Exception:
                pass
        con.execute(
            "INSERT INTO pages (slug, title, type, path, content) VALUES (?,?,?,?,?)",
            (slug, title, "concept", str(fp), text),
        )
        n_pages += 1
    con.commit()
    con.close()
    return {"ok": True, "vault": vault.meta.name, "db_path": str(db_path), "pages": n_pages, "mode": "inline"}
