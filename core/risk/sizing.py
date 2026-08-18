"""
Position sizing: volatility targeting + capped fractional Kelly.
Principle: constant dollar risk regardless of market turbulence.

vol_target_size: scales position so expected daily P&L vol equals a fixed target.
kelly_fraction:  edges the size toward the mathematically optimal fraction, hard-capped.
compute_position_size: combines both, respects hard caps.
"""
from __future__ import annotations

import numpy as np

from backtest.engine import Bar

# ── Defaults ──────────────────────────────────────────────────────────────────

_TARGET_VOL_ANN = 0.15        # 15% annualized target vol - deliberately conservative
_ATR_LOOKBACK   = 14          # bars for realized-vol estimate
_KELLY_CAP      = 0.25        # never use more than 25% of full Kelly
_MIN_FRACTION   = 0.10        # floor: 10% of base - keeps signal alive in high vol
_MAX_FRACTION   = 2.00        # ceiling: never lever beyond 2× base


# ── Vol-targeted sizing ───────────────────────────────────────────────────────

def vol_target_size(
    history: list[Bar],
    base_size_usd: float,
    capital: float,
    max_pct: float = 0.25,
    target_vol: float = _TARGET_VOL_ANN,
    lookback: int = _ATR_LOOKBACK,
) -> float:
    """
    Scale base_size by target_vol / realized_vol.
    High vol  → smaller position (auto risk-off).
    Low vol   → larger position (up to MAX_FRACTION × base).
    Hard cap: min(vol-sized, capital × max_pct).
    """
    rv = _realized_vol_ann(history, lookback)
    if rv < 1e-8:
        multiplier = 1.0
    else:
        multiplier = float(np.clip(target_vol / rv, _MIN_FRACTION, _MAX_FRACTION))

    vol_sized = base_size_usd * multiplier
    cap = capital * max_pct
    return float(min(vol_sized, cap))


def realized_vol(history: list[Bar], lookback: int = _ATR_LOOKBACK) -> float:
    """Annualized realized volatility estimate (public helper for tests/attribution)."""
    return _realized_vol_ann(history, lookback)


# ── Fractional Kelly ─────────────────────────────────────────────────────────

def kelly_fraction(
    win_rate: float,
    avg_win_pct: float,
    avg_loss_pct: float,
    cap: float = _KELLY_CAP,
) -> float:
    """
    Capped fractional Kelly: f* = (p*b - q) / b  where b = avg_win/avg_loss.
    Returns 0.0 when edge is zero or negative (sit out).
    Capped at `cap` × full Kelly to guard against sample variance.
    """
    if win_rate <= 0 or avg_win_pct <= 0 or avg_loss_pct <= 0:
        return 0.0
    b = avg_win_pct / avg_loss_pct
    q = 1.0 - win_rate
    full_kelly = (win_rate * b - q) / b
    if full_kelly <= 0:
        return 0.0
    return float(min(full_kelly * cap, cap))


def kelly_size_from_trades(
    base_size_usd: float,
    recent_pnls: list[float],
    cap: float = _KELLY_CAP,
) -> float:
    """
    Estimate Kelly size from a list of recent trade P&Ls (in USD).
    Falls back to base_size when insufficient history (< 5 trades).
    """
    if len(recent_pnls) < 5:
        return base_size_usd

    wins  = [p for p in recent_pnls if p > 0]
    losses = [abs(p) for p in recent_pnls if p < 0]

    if not wins or not losses:
        return base_size_usd

    wr = len(wins) / len(recent_pnls)
    avg_w = float(np.mean(wins))
    avg_l = float(np.mean(losses))

    # Convert to % (Kelly needs ratios, not absolute $)
    avg_w_pct = avg_w / base_size_usd if base_size_usd > 0 else 0.02
    avg_l_pct = avg_l / base_size_usd if base_size_usd > 0 else 0.01

    kf = kelly_fraction(wr, avg_w_pct, avg_l_pct, cap)
    if kf <= 0:
        return base_size_usd * 0.5   # no edge → half size

    # kf is fraction of capital; normalise to a multiple of base_size
    return float(np.clip(base_size_usd * kf * 4.0, base_size_usd * _MIN_FRACTION,
                         base_size_usd * _MAX_FRACTION))


# ── Combined sizing ───────────────────────────────────────────────────────────

def compute_position_size(
    history: list[Bar],
    base_size_usd: float,
    capital: float,
    recent_pnls: list[float] | None = None,
    max_pct: float = 0.25,
    target_vol: float = _TARGET_VOL_ANN,
) -> float:
    """
    Final size = min(vol_targeted, kelly_sized, capital × max_pct).
    Kelly is only applied when enough trade history exists.
    """
    v_size = vol_target_size(history, base_size_usd, capital, max_pct, target_vol)

    if recent_pnls and len(recent_pnls) >= 5:
        k_size = kelly_size_from_trades(base_size_usd, recent_pnls)
        return float(min(v_size, k_size))

    return v_size


# ── Private ───────────────────────────────────────────────────────────────────

def _realized_vol_ann(history: list[Bar], lookback: int) -> float:
    """Daily log-return std × sqrt(252) over the lookback window."""
    window = history[-lookback:] if len(history) >= lookback else history
    if len(window) < 2:
        return 0.0
    closes = np.array([b.close for b in window], dtype=float)
    log_rets = np.diff(np.log(closes))
    return float(log_rets.std() * np.sqrt(252))
