"""
agent - Alien-Trade live runtime.

Runs the SAME `/core` strategy as the backtest, on a live (or replayed) feed.
Zero duplicate strategy logic lives here - this package only orchestrates:
feed → core strategy (risk-wrapped) → executor → Convex state bus.

Importing this package puts `core/` on sys.path so the top-level core modules
(`backtest`, `signals`, `strategy`, `risk`, `exec`, `data`, `config`) resolve
both at runtime and under pytest.
"""
from __future__ import annotations

import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parent.parent / "core"
if _CORE.is_dir() and str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))
