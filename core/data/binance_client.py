"""
Binance public klines — free 2-year OHLCV history, no auth required.
Used as the primary historical source until CMC Pro / Agent Hub is confirmed.
Output schema is identical to cmc_client so the backtest engine is indifferent.

Symbol mapping: BNB→BNBUSDT, BTC/BTCB→BTCUSDT, ETH→ETHUSDT, USDT stays cash.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Optional

import httpx
import polars as pl
from tenacity import retry, stop_after_attempt, wait_exponential

from backtest.engine import Bar
from config.constants import BINANCE_BASE_URL, BINANCE_SYMBOL_PAIRS, BINANCE_INTERVAL_MAP

BINANCE_BASE  = BINANCE_BASE_URL
CACHE_DIR     = Path(__file__).parent / "parquet"
SYMBOL_PAIRS  = BINANCE_SYMBOL_PAIRS
INTERVAL_MAP  = BINANCE_INTERVAL_MAP


class BinanceClient:
    """
    Wraps Binance public REST API for historical OHLCV.
    No API key needed. Cache to parquet on first fetch.
    """

    def __init__(self):
        self._http = httpx.Client(base_url=BINANCE_BASE, timeout=30.0)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "BinanceClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def fetch_ohlcv_historical(
        self,
        symbol: str,
        days_back: int = 730,
        interval: str = "daily",
        force_refresh: bool = False,
    ) -> pl.DataFrame:
        """
        Pull OHLCV for `symbol` going back `days_back` days.
        Returns polars DataFrame with the same schema as CMCClient (10 columns).
        """
        if symbol not in SYMBOL_PAIRS:
            raise ValueError(f"No Binance pair for {symbol!r}. Add it to SYMBOL_PAIRS.")

        cache = _cache_path(symbol, days_back, interval)
        if cache.exists() and not force_refresh:
            return pl.read_parquet(cache)

        pair = SYMBOL_PAIRS[symbol]
        binance_interval = INTERVAL_MAP.get(interval, "1d")

        end_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
        start_ms = end_ms - days_back * 86_400_000

        klines = self._fetch_klines(pair, binance_interval, start_ms, end_ms)
        df = _parse_klines(klines)

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.write_parquet(cache)
        return df

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _fetch_klines(
        self, pair: str, interval: str, start_ms: int, end_ms: int
    ) -> list[list]:
        """
        Paginate Binance klines (max 1000 per request).
        Returns raw list-of-lists from Binance.
        """
        all_klines: list[list] = []
        cursor = start_ms
        while cursor < end_ms:
            r = self._http.get(
                "/api/v3/klines",
                params={
                    "symbol": pair,
                    "interval": interval,
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": 1000,
                },
            )
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            all_klines.extend(batch)
            # advance past the last kline open time + 1ms to avoid overlap
            cursor = int(batch[-1][0]) + 1
            if len(batch) < 1000:
                break
        return all_klines

    def fetch_recent_bars(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 200,
    ) -> list[Bar]:
        """
        Live feed: pull the most recent `limit` completed klines for `symbol`.
        Reuses the same Binance source + schema as the historical pull, so the
        bars the live agent sees are identical in shape to what the sim trained
        on. Drops the still-forming last candle (point-in-time, no look-ahead).
        """
        if symbol not in SYMBOL_PAIRS:
            raise ValueError(f"No Binance pair for {symbol!r}. Add it to SYMBOL_PAIRS.")
        pair = SYMBOL_PAIRS[symbol]
        binance_interval = INTERVAL_MAP.get(interval, interval)
        r = self._http.get(
            "/api/v3/klines",
            params={"symbol": pair, "interval": binance_interval, "limit": min(limit + 1, 1000)},
        )
        r.raise_for_status()
        klines = r.json()
        if klines:
            klines = klines[:-1]  # drop the in-progress candle
        return self.bars_from_df(_parse_klines(klines))

    def bars_from_df(self, df: pl.DataFrame) -> list[Bar]:
        """Convert cached OHLCV DataFrame → list[Bar] for the backtest engine."""
        return [
            Bar(
                timestamp=int(row["timestamp_ms"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                funding_rate=float(row["funding_rate"]),
                open_interest=float(row["open_interest"]),
                social_score=float(row["social_score"]),
                net_flow=float(row["net_flow"]),
            )
            for row in df.to_dicts()
        ]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _cache_path(symbol: str, days_back: int, interval: str) -> Path:
    return CACHE_DIR / f"binance_{symbol}_{days_back}d_{interval}.parquet"


def _parse_klines(klines: list[list]) -> pl.DataFrame:
    """
    Binance kline format (index → field):
    0  open_time, 1 open, 2 high, 3 low, 4 close, 5 volume,
    6  close_time, 7 quote_volume, 8 trades, 9 taker_buy_base,
    10 taker_buy_quote, 11 ignore
    """
    rows = []
    for k in klines:
        rows.append(
            {
                "timestamp_ms": int(k[0]),
                "open":  float(k[1]),
                "high":  float(k[2]),
                "low":   float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                # Extended signal fields — wired from CMC Agent Hub in Phase 6
                "funding_rate":   0.0,
                "open_interest":  0.0,
                "social_score":   0.0,
                "net_flow":       0.0,
            }
        )
    return pl.DataFrame(
        rows,
        schema={
            "timestamp_ms":   pl.Int64,
            "open":           pl.Float64,
            "high":           pl.Float64,
            "low":            pl.Float64,
            "close":          pl.Float64,
            "volume":         pl.Float64,
            "funding_rate":   pl.Float64,
            "open_interest":  pl.Float64,
            "social_score":   pl.Float64,
            "net_flow":       pl.Float64,
        },
    )
