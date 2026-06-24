"""pytest config — add scripts/ root to sys.path so build_db is importable."""
import sys
from pathlib import Path

# scripts/ root is the parent of tests/
SCRIPTS_ROOT = Path(__file__).resolve().parent.parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
