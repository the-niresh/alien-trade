"""
pytest bootstrap for the agent runtime tests.

Puts the repo root (so `import agent` works) and `core/` (so `from backtest…`
works) on sys.path. Run from repo root with the core venv:

    core/.venv/Scripts/python.exe -m pytest agent/tests -v
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_CORE = _ROOT / "core"
for p in (str(_ROOT), str(_CORE)):
    if p not in sys.path:
        sys.path.insert(0, p)
