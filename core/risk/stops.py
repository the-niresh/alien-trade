"""
Pure stop-loss math — no I/O, no state. Used by RiskEngine to enforce a hard ATR
stop and an ATR trailing stop. Sim and live both run RiskEngine, so these run
identically in backtest and production (parity invariant, locked decision #2).
"""
from __future__ import annotations

from backtest.engine import Bar


def compute_atr(history: list[Bar], period: int = 14) -> float:
    """Average True Range over the last `period` bars. 0.0 if < 2 bars."""
    if len(history) < 2:
        return 0.0
    bars = history[-(period + 1):] if len(history) > period else history
    trs: list[float] = []
    for prev, cur in zip(bars[:-1], bars[1:]):
        tr = max(
            cur.high - cur.low,
            abs(cur.high - prev.close),
            abs(cur.low - prev.close),
        )
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0


def hard_stop_level(avg_entry: float, atr: float, mult: float) -> float:
    """Fixed stop a multiple of ATR below entry. 0.0 (disabled) if no ATR/entry."""
    if avg_entry <= 0.0 or atr <= 0.0 or mult <= 0.0:
        return 0.0
    return avg_entry - mult * atr


def trailing_stop_level(high_water: float, atr: float, mult: float) -> float:
    """Stop trailing a multiple of ATR below the position's high-water mark."""
    if high_water <= 0.0 or atr <= 0.0 or mult <= 0.0:
        return 0.0
    return high_water - mult * atr


def stop_triggered(price: float, stop: float) -> bool:
    """True when a positive stop level has been breached to the downside."""
    return stop > 0.0 and price <= stop
