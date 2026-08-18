"""
Deterministic regime detector: TREND / CHOP / HIGH_VOL / CRASH.
Uses only data visible at the current bar - no look-ahead.

Decision tree (evaluated in priority order):
  1. CRASH   - price > 15% below rolling peak in the lookback window
  2. HIGH_VOL - ATR/price > 4% (daily ATR is large relative to price level)
  3. TREND   - linear regression slope > 0.3%/bar AND ATR/price < 3%
  4. CHOP    - everything else
"""
from __future__ import annotations

from enum import Enum

import numpy as np

from backtest.engine import Bar


class Regime(str, Enum):
    TREND = "trend"
    CHOP = "chop"
    HIGH_VOL = "high_vol"
    CRASH = "crash"


# ── Public API ────────────────────────────────────────────────────────────────

def detect_regime(history: list[Bar], lookback: int = 20) -> Regime:
    """
    Classify current market regime from `history` (point-in-time, no look-ahead).
    Returns Regime.CHOP if insufficient data.
    """
    if len(history) < max(lookback, 2):
        return Regime.CHOP

    window = history[-lookback:]
    closes = np.array([b.close for b in window], dtype=float)
    highs = np.array([b.high for b in window], dtype=float)
    lows = np.array([b.low for b in window], dtype=float)

    atr_pct = _atr_pct(closes, highs, lows)
    slope_pct = _slope_pct(closes)
    drawdown = _drawdown_from_peak(closes)

    if drawdown < -0.15:
        return Regime.CRASH
    if atr_pct > 0.04:
        return Regime.HIGH_VOL
    if abs(slope_pct) > 0.003 and atr_pct < 0.03:
        return Regime.TREND
    return Regime.CHOP


def regime_slice_metrics(
    bars: list[Bar],
    regimes: list[Regime],
    equity_curve: list[float],
) -> dict[str, dict]:
    """
    Split equity returns by regime and compute per-regime metrics.
    All three lists must be the same length.
    """
    assert len(bars) == len(regimes) == len(equity_curve)

    slices: dict[str, list[float]] = {r.value: [] for r in Regime}
    for i in range(1, len(equity_curve)):
        r = regimes[i].value
        ret = (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
        slices[r].append(ret)

    result: dict[str, dict] = {}
    for regime_name, rets in slices.items():
        if not rets:
            result[regime_name] = {"n_bars": 0}
            continue
        arr = np.array(rets)
        downside = arr[arr < 0]
        result[regime_name] = {
            "n_bars": len(arr),
            "mean_ret": round(float(arr.mean()), 6),
            "sharpe": round(float((arr.mean() / arr.std()) * np.sqrt(252)) if arr.std() > 0 else 0.0, 4),
            "sortino": round(float((arr.mean() / downside.std()) * np.sqrt(252)) if len(downside) > 0 and downside.std() > 0 else 0.0, 4),
        }
    return result


# ── Private helpers ───────────────────────────────────────────────────────────

def _atr_pct(closes: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> float:
    """Average True Range as a fraction of current close."""
    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1]),
        ),
    )
    return float(tr.mean() / closes[-1]) if closes[-1] > 0 else 0.0


def _slope_pct(closes: np.ndarray) -> float:
    """Linear regression slope per bar, normalised by first bar price."""
    x = np.arange(len(closes), dtype=float)
    slope = float(np.polyfit(x, closes, 1)[0])
    return slope / closes[0] if closes[0] > 0 else 0.0


def _drawdown_from_peak(closes: np.ndarray) -> float:
    """Drawdown of last price from the rolling peak within the window."""
    peak = closes.max()
    return float((closes[-1] - peak) / peak) if peak > 0 else 0.0
