"""Pytest configuration to ensure package imports resolve from src/.
This allows running `pytest` without setting PYTHONPATH.
"""

import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
