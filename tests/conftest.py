"""Pytest config — ensure repo root on sys.path for `import raven`."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
