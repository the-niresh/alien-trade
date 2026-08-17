"""Objective-score simulator.

Bootstrap historical N-day windows through the objective
(Sortino − 2·|maxDD|) → a distribution of the score per strategy variant.
We tune for expected percentile, turning "is cash-default too timid vs a pump regime?"
from a fear into a measured tradeoff. Also usable to price the activity-floor drag.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LAMBDA = 2.0  # rubric weight on drawdown (locked objective: Sortino − 2·|maxDD|)


def _max_drawdown(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / np.where(peak == 0, 1, peak)
    return float(dd.min())  # <= 0


def _sortino(returns: np.ndarray) -> float:
    if len(returns) == 0:
        return 0.0
    downside = returns[returns < 0]
    dd = np.sqrt(np.mean(downside ** 2)) if len(downside) else 0.0
    if dd == 0:
        return 0.0
    return float(np.mean(returns) / dd)


def window_objective(equity_window: np.ndarray) -> float:
    eq = np.asarray(equity_window, dtype=float)
    rets = np.diff(eq) / np.where(eq[:-1] == 0, 1, eq[:-1])
    obj = _sortino(rets) - LAMBDA * abs(_max_drawdown(eq))
    return float(obj) if np.isfinite(obj) else 0.0


def score_sim(equity: pd.Series, window_days: int = 7, n_boot: int = 1000,
              bars_per_day: int = 1, seed: int = 0) -> np.ndarray:
    """Return an array of `n_boot` objective scores from random contiguous windows."""
    eq = np.asarray(equity, dtype=float)
    wlen = max(window_days * bars_per_day, 2)
    rng = np.random.default_rng(seed)
    if len(eq) <= wlen:
        return np.zeros(n_boot)
    starts = rng.integers(0, len(eq) - wlen, size=n_boot)
    return np.array([window_objective(eq[s:s + wlen]) for s in starts])
