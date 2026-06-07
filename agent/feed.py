"""
Market feed abstraction for the live loop.

A feed yields a point-in-time history slice per cycle — exactly what the sim
hands the strategy. Two implementations:

  ReplayFeed     — deterministic; replays a fixed bar list one bar at a time.
                   Used for paper rehearsal, sim-vs-live parity, and chaos tests.
  BinanceLiveFeed — real live feed: seeds from historical bars, then re-pulls
                    the latest completed candles each cycle. Same source + schema
                    as the historical pull, so live bars match what the sim saw.

The `next()` contract mirrors the backtest's per-bar call: it returns the full
history visible at the current cycle (bars[0..i]); None when the stream ends.
"""
from __future__ import annotations

from typing import Optional, Protocol

from backtest.engine import Bar


class MarketFeed(Protocol):
    def next(self) -> Optional[list[Bar]]:
        """Point-in-time history for the next cycle, or None when exhausted."""
        ...


# ── Replay (deterministic) ────────────────────────────────────────────────────

class ReplayFeed:
    """
    Replays `bars` one cycle at a time. Cycle k exposes bars[0..k] (1-indexed
    length), identically to how run_backtest calls strategy(bars[:i+1]).
    Exhausts to None after the final bar — drives a finite, reproducible run.
    """

    def __init__(self, bars: list[Bar], warmup: int = 0):
        self._bars = list(bars)
        self._cursor = max(0, warmup)   # bars before warmup are skipped entirely

    def next(self) -> Optional[list[Bar]]:
        if self._cursor >= len(self._bars):
            return None
        self._cursor += 1
        return self._bars[: self._cursor]

    @property
    def exhausted(self) -> bool:
        return self._cursor >= len(self._bars)


# ── Live (Binance klines) ─────────────────────────────────────────────────────

class BinanceLiveFeed:
    """
    Live feed backed by Binance public klines (same source as the 2-yr history).
    Each `next()` re-pulls the most recent completed candles for the symbol.
    Stateless between calls beyond the client — safe to retry.
    """

    def __init__(self, symbol: str, interval: str = "1h", history_bars: int = 200, client=None):
        self.symbol = symbol
        self.interval = interval
        self.history_bars = history_bars
        if client is None:
            from data.binance_client import BinanceClient
            client = BinanceClient()
        self._client = client

    def next(self) -> Optional[list[Bar]]:
        bars = self._client.fetch_recent_bars(
            self.symbol, interval=self.interval, limit=self.history_bars
        )
        return bars or None
