"""pytest config — make `mcp` and `scripts/` importable from tests."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent  # .../Wiki
MCP_DIR = Path(__file__).resolve().parent.parent      # .../Wiki/mcp
SCRIPTS_DIR = ROOT / "scripts"

for p in (str(ROOT), str(MCP_DIR), str(SCRIPTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


# ─────────────── fixtures ───────────────


@pytest.fixture(scope="session")
def vault_root() -> Path:
    """Path to the live vault under test (= ~/Desktop/Dev/Project/Wiki)."""
    return ROOT


@pytest.fixture(scope="session")
def wiki_db(vault_root: Path) -> Path:
    p = vault_root / "wiki.db"
    if not p.exists():
        pytest.skip(f"wiki.db not found at {p}; run scripts/build_db.py first")
    return p


@pytest.fixture
def sample_slug(wiki_db: Path) -> str:
    """A real slug we know exists in the built DB."""
    import sqlite3
    conn = sqlite3.connect(str(wiki_db))
    try:
        row = conn.execute("SELECT slug FROM pages LIMIT 1").fetchone()
    finally:
        conn.close()
    assert row is not None, "no pages in wiki.db"
    return row[0]