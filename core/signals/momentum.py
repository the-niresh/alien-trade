"""
Momentum / Trend signal (backbone of the strategy).
EMA cross + Rate-of-Change, normalized by ATR so the score is volatility-agnostic.
Output: float in [-1, +1].  +1 = strong uptrend, -1 = strong downtrend, 0 = flat/chop.
"""
from __future__ import annotations

import numpy as np

from backtest.engine import Bar

# ── Public API ────────────────────────────────────────────────────────────────

def momentum_signal(
    history: list[Bar],
    fast: int = 8,
    slow: int = 21,
    roc_period: int = 10,
) -> float:
    """
    Combined momentum score in [-1, 1].
    Component 1 (60%): EMA-cross divergence normalised by ATR.
    Component 2 (40%): ROC normalised by ATR.
    Returns 0.0 when there are fewer bars than the slow EMA period.
    """
    closes = [b.close for b in history]
    n = len(closes)
    if n < slow + 1:
        return 0.0

    ema_f = _ema_last(closes, fast)
    ema_s = _ema_last(closes, slow)
    if ema_s == 0:
        return 0.0

    ema_score = (ema_f - ema_s) / ema_s          # fractional EMA divergence

    roc_score = 0.0
    if n >= roc_period + 1:
        base = closes[-roc_period - 1]
        if base > 0:
            roc_score = (closes[-1] - base) / base

    # ATR normalization — 1 ATR of signal = 0.5 raw score → clips to ±1 at 2 ATRs
    atr_pct = _atr_pct(history[-30:] if n >= 30 else history)
    if atr_pct < 1e-8:
        return 0.0

    raw = 0.6 * (ema_score / atr_pct) + 0.4 * (roc_score / atr_pct)
    return float(np.clip(raw / 2.0, -1.0, 1.0))


# ── Signal components (exported for attribution) ──────────────────────────────

def ema_cross_score(history: list[Bar], fast: int = 8, slow: int = 21) -> float:
    """Raw EMA cross as fraction of slow EMA. Unbounded."""
    closes = [b.close for b in history]
    if len(closes) < slow + 1:
        return 0.0
    ema_f = _ema_last(closes, fast)
    ema_s = _ema_last(closes, slow)
    return (ema_f - ema_s) / ema_s if ema_s > 0 else 0.0


def roc_score(history: list[Bar], period: int = 10) -> float:
    """Rate of change over `period` bars. Unbounded."""
    closes = [b.close for b in history]
    if len(closes) < period + 1:
        return 0.0
    base = closes[-period - 1]
    return (closes[-1] - base) / base if base > 0 else 0.0


def atr_pct_current(history: list[Bar], lookback: int = 14) -> float:
    """Current ATR as a fraction of last close price."""
    window = history[-lookback:] if len(history) >= lookback else history
    return _atr_pct(window)


def ema_value(history: list[Bar], period: int) -> float:
    """EMA of close over `period` bars. NaN if fewer than `period` bars.
    Public helper for the strategy's long-term trend filter."""
    return _ema_last([b.close for b in history], period)


# ── Private helpers ───────────────────────────────────────────────────────────

def _ema_last(values: list[float], period: int) -> float:
    """EMA of the last value using Wilder's smoothing (alpha = 2/(period+1))."""
    if len(values) < period:
        return float("nan")
    alpha = 2.0 / (period + 1)
    ema = sum(values[:period]) / period          # SMA seed
    for v in values[period:]:
        ema = alpha * v + (1.0 - alpha) * ema
    return ema


def _atr_pct(bars: list[Bar]) -> float:
    """Average True Range as fraction of last close."""
    if len(bars) < 2:
        return 0.0
    trs = []
    for i in range(1, len(bars)):
        prev_close = bars[i - 1].close
        high, low = bars[i].high, bars[i].low
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    last_close = bars[-1].close
    return float(np.mean(trs) / last_close) if last_close > 0 else 0.0
