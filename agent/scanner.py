"""
Cross-sectional rotation scanner.

Each cycle, score every symbol in the trading universe, pick the one with
the highest contrarian signal that exceeds the entry threshold.  Returns None
when no symbol qualifies (→ stay in USDT, zero drawdown).

Runs in parallel (ThreadPoolExecutor) to keep latency under one Binance
round-trip even across 9 symbols.  Each per-symbol call is failure-isolated
so a bad kline response never blocks the others.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from risk.guardrails import TRADING_UNIVERSE
from strategy.combined import StrategyParams, score_breakdown

log = logging.getLogger(__name__)


class SymbolScanner:
    """
    Score all symbols in the universe and return the best one.

    Args:
        universe:     Ordered tuple of symbol strings to scan.
        params:       The active StrategyParams (weights, thresholds).
        interval:     Bar interval passed to BinanceLiveFeed (default "1h").
        history_bars: How many bars to fetch per symbol (default 200).
    """

    def __init__(
        self,
        params: StrategyParams,
        universe: tuple[str, ...] = TRADING_UNIVERSE,
        interval: str = "1h",
        history_bars: int = 200,
    ):
        self.universe = universe
        self.params = params
        self.interval = interval
        self.history_bars = history_bars

    def best_symbol(self) -> Optional[str]:
        """
        Fetch bars for all universe symbols in parallel, score each with
        score_breakdown, and return the symbol with the highest target score
        that exceeds entry_threshold.  Returns None when the universe is quiet.
        """
        from data.binance_client import BinanceClient
        client = BinanceClient()

        def _score_one(sym: str) -> tuple[str, float]:
            try:
                bars = client.fetch_recent_bars(sym, self.interval, self.history_bars)
                if not bars or len(bars) < 50:
                    return sym, -999.0
                bd = score_breakdown(bars, self.params)
                return sym, float(bd["target"])
            except Exception as exc:  # noqa: BLE001
                log.debug("scanner: %s failed: %s", sym, exc)
                return sym, -999.0

        scores: dict[str, float] = {}
        with ThreadPoolExecutor(max_workers=len(self.universe)) as pool:
            futures = {pool.submit(_score_one, sym): sym for sym in self.universe}
            for fut in as_completed(futures):
                sym, score = fut.result()
                scores[sym] = score

        threshold = self.params.entry_threshold
        qualifying = {sym: sc for sym, sc in scores.items() if sc >= threshold}
        if not qualifying:
            log.debug("scanner: no symbol above threshold %.2f — staying in USDT", threshold)
            return None

        winner = max(qualifying, key=qualifying.__getitem__)
        log.debug(
            "scanner: winner=%s target=%.4f  scores=%s",
            winner,
            scores[winner],
            {s: round(v, 3) for s, v in sorted(scores.items(), key=lambda x: -x[1])},
        )
        return winner
