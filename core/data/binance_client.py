"""
Binance public klines — free 2-year OHLCV history, no auth required.
Used as the primary historical source until CMC Pro / Agent Hub is confirmed.
Output schema is identical to cmc_client so the backtest engine is indifferent.

Symbol mapping: BNB→BNBUSDT, BTC/BTCB→BTCUSDT, ETH→ETHUSDT, USDT stays cash.
"""
from __future__ import annotations

import bisect
import datetime
from pathlib import Path
from typing import Optional

import httpx
import polars as pl
from tenacity import retry, stop_after_attempt, wait_exponential

from backtest.engine import Bar
from config.constants import (
    BINANCE_BASE_URL, BINANCE_FUTURES_BASE_URL, BINANCE_FUTURES_PAIRS,
    BINANCE_SYMBOL_PAIRS, BINANCE_INTERVAL_MAP,
)

BINANCE_BASE    = BINANCE_BASE_URL
FUTURES_BASE    = BINANCE_FUTURES_BASE_URL
FUTURES_PAIRS   = BINANCE_FUTURES_PAIRS
CACHE_DIR       = Path(__file__).parent / "parquet"
SYMBOL_PAIRS    = BINANCE_SYMBOL_PAIRS
INTERVAL_MAP    = BINANCE_INTERVAL_MAP


class BinanceClient:
    """
    Wraps Binance public REST API for historical OHLCV.
    No API key needed. Cache to parquet on first fetch.
    """

    def __init__(self):
        self._http    = httpx.Client(base_url=BINANCE_BASE,   timeout=30.0)
        self._futures = httpx.Client(base_url=FUTURES_BASE, timeout=30.0)

    def close(self) -> None:
        self._http.close()
        self._futures.close()

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
        enrich_derivatives: bool = True,
        enrich_sentiment: bool = True,
    ) -> pl.DataFrame:
        """Pull OHLCV for `symbol` going back `days_back` days.

        When `enrich_derivatives=True` (default) and the symbol has a Binance
        futures pair, funding_rate and open_interest are populated from the public
        fapi endpoints (free, no key). When `enrich_sentiment=True`, social_score
        is filled from the free Fear & Greed Index (alternative.me, point-in-time).
        Both fall back gracefully when their source is unreachable (the field
        stays 0.0). Returns polars DataFrame with the same 10-column schema as
        CMCClient.
        """
        if symbol not in SYMBOL_PAIRS:
            raise ValueError(f"No Binance pair for {symbol!r}. Add it to SYMBOL_PAIRS.")

        cache = _cache_path(symbol, days_back, interval)
        if cache.exists() and not force_refresh:
            df = pl.read_parquet(cache)
            dirty = False
            # Re-enrich on cache hit only if the field is still all-zero (old cache)
            if enrich_derivatives and df["funding_rate"].max() == 0.0:
                df = self.enrich_derivatives(df, symbol)
                dirty = True
            if enrich_sentiment and df["social_score"].max() == 0.0:
                df = self._enrich_sentiment(df)
                dirty = True
            if dirty:
                df.write_parquet(cache)
            return df

        pair = SYMBOL_PAIRS[symbol]
        binance_interval = INTERVAL_MAP.get(interval, "1d")

        end_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
        start_ms = end_ms - days_back * 86_400_000

        klines = self._fetch_klines(pair, binance_interval, start_ms, end_ms)
        df = _parse_klines(klines)

        if enrich_derivatives:
            df = self.enrich_derivatives(df, symbol)
        if enrich_sentiment:
            df = self._enrich_sentiment(df)

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
        df = _parse_klines(klines)
        # Inject Fear & Greed Index so fear_greed_signal works on live bars
        # (historical bars get this via _enrich_sentiment; live bars need it too)
        if df["social_score"].max() == 0.0:
            df = self._enrich_sentiment(df)
        return self.bars_from_df(df)

    # ── Derivatives enrichment (free Binance Futures API: funding + OI) ──────

    def enrich_derivatives(self, df: pl.DataFrame, symbol: str) -> pl.DataFrame:
        """Add real funding_rate + open_interest to an OHLCV dataframe using
        Binance Futures public endpoints (no key required).

        - Funding rates: 8h settlements, forward-filled to every bar.
        - Open interest: hourly snapshots, aligned by timestamp.

        Falls back gracefully: if the symbol has no futures pair or the API
        call fails, the dataframe is returned unchanged (zeros stay zeros).
        Both sources are cached to parquet to avoid redundant network calls.
        """
        futures_pair = FUTURES_PAIRS.get(symbol)
        if not futures_pair:
            return df  # no futures pair for this symbol (e.g. CAKE)

        ts_list = df["timestamp_ms"].to_list()
        if not ts_list:
            return df
        start_ms, end_ms = int(ts_list[0]), int(ts_list[-1])

        # Funding rates
        fr_data = self._load_or_fetch_funding(futures_pair, start_ms, end_ms)
        # OI history (only available for hourly and above)
        oi_data = self._load_or_fetch_oi(futures_pair, start_ms, end_ms)

        return _merge_derivatives(df, fr_data, oi_data)

    def _enrich_sentiment(self, df: pl.DataFrame) -> pl.DataFrame:
        """Fill social_score from the free Fear & Greed Index (point-in-time).
        Market-wide, so symbol-independent. Fails open (zeros stay zeros)."""
        try:
            from data.sentiment_history import enrich_sentiment as _fg_enrich
            return _fg_enrich(df)
        except Exception as e:  # noqa: BLE001
            print(f"[fear-greed] sentiment enrichment failed: {e}")
            return df

    def _load_or_fetch_funding(
        self, pair: str, start_ms: int, end_ms: int
    ) -> list[dict]:
        cache = CACHE_DIR / f"binance_futures_fr_{pair}.parquet"
        try:
            if cache.exists():
                cached = pl.read_parquet(cache).to_dicts()
                # If cache covers our window, use it; otherwise re-fetch
                cached_start = cached[0]["fundingTime"] if cached else end_ms + 1
                cached_end   = cached[-1]["fundingTime"] if cached else 0
                if int(cached_start) <= start_ms and int(cached_end) >= end_ms:
                    return cached
        except Exception:
            pass
        try:
            rows = self._fetch_funding_history(pair, start_ms, end_ms)
            if rows:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                pl.DataFrame(rows).write_parquet(cache)
            return rows
        except Exception as e:
            print(f"[binance-futures] funding rate fetch failed for {pair}: {e}")
            return []

    def _load_or_fetch_oi(
        self, pair: str, start_ms: int, end_ms: int
    ) -> list[dict]:
        cache = CACHE_DIR / f"binance_futures_oi_{pair}_1h.parquet"
        try:
            if cache.exists():
                cached = pl.read_parquet(cache).to_dicts()
                if cached:
                    cs = int(cached[0]["timestamp"])
                    ce = int(cached[-1]["timestamp"])
                    if cs <= start_ms and ce >= end_ms:
                        return cached
        except Exception:
            pass
        try:
            rows = self._fetch_oi_history(pair, start_ms, end_ms)
            if rows:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                pl.DataFrame(rows).write_parquet(cache)
            return rows
        except Exception as e:
            print(f"[binance-futures] OI history fetch failed for {pair}: {e}")
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def _fetch_funding_history(
        self, pair: str, start_ms: int, end_ms: int
    ) -> list[dict]:
        """Paginate Binance fapi fundingRate (8h settlements, up to 1000/request)."""
        all_rows: list[dict] = []
        cursor = start_ms
        while cursor <= end_ms:
            r = self._futures.get(
                "/fapi/v1/fundingRate",
                params={"symbol": pair, "startTime": cursor,
                        "endTime": end_ms, "limit": 1000},
            )
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            for row in batch:
                all_rows.append({
                    "fundingTime": int(row["fundingTime"]),
                    "fundingRate": float(row["fundingRate"]),
                })
            last_ts = int(batch[-1]["fundingTime"])
            if last_ts <= cursor or len(batch) < 1000:
                break
            cursor = last_ts + 1
        return all_rows

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def _fetch_oi_history(
        self, pair: str, start_ms: int, end_ms: int, period: str = "1h"
    ) -> list[dict]:
        """Paginate Binance futures openInterestHist (500/request, hourly)."""
        all_rows: list[dict] = []
        cursor = start_ms
        # Binance restricts each OI hist request to a limited time window
        chunk_ms = 200 * 3_600_000  # 200 hourly bars per request to stay within limits
        while cursor <= end_ms:
            chunk_end = min(cursor + chunk_ms, end_ms)
            r = self._futures.get(
                "/futures/data/openInterestHist",
                params={"symbol": pair, "period": period,
                        "startTime": cursor, "endTime": chunk_end, "limit": 500},
            )
            r.raise_for_status()
            batch = r.json()
            if not batch:
                cursor = chunk_end + 1
                continue
            for row in batch:
                all_rows.append({
                    "timestamp": int(row["timestamp"]),
                    "sumOpenInterest": float(row["sumOpenInterest"]),
                })
            last_ts = int(batch[-1]["timestamp"])
            cursor = max(last_ts + 1, chunk_end + 1)
        return all_rows

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

def _merge_derivatives(
    df: pl.DataFrame,
    funding_rows: list[dict],
    oi_rows: list[dict],
) -> pl.DataFrame:
    """Merge futures derivatives signals (funding + OI) into an OHLCV dataframe.

    Funding rate: forward-filled from each 8h settlement.
    Open interest: aligned by nearest hourly snapshot (within ±1h).
    """
    timestamps = df["timestamp_ms"].to_list()

    # ── Funding rate (forward-fill) ──────────────────────────────────────────
    fr_sorted = sorted(funding_rows, key=lambda r: int(r["fundingTime"]))
    fr_ts  = [int(r["fundingTime"]) for r in fr_sorted]
    fr_val = [float(r["fundingRate"]) for r in fr_sorted]

    new_fr: list[float] = []
    fr_idx = 0
    current_fr = 0.0
    for ts in timestamps:
        # Advance while the next settlement is at or before this bar's timestamp
        while fr_idx < len(fr_ts) and fr_ts[fr_idx] <= ts:
            current_fr = fr_val[fr_idx]
            fr_idx += 1
        new_fr.append(current_fr)

    # ── Open interest (nearest snapshot) ────────────────────────────────────
    oi_sorted = sorted(oi_rows, key=lambda r: int(r["timestamp"]))
    oi_ts  = [int(r["timestamp"]) for r in oi_sorted]
    oi_val = [float(r["sumOpenInterest"]) for r in oi_sorted]

    new_oi: list[float] = []
    for ts in timestamps:
        idx = bisect.bisect_right(oi_ts, ts) - 1
        if idx >= 0 and ts - oi_ts[idx] <= 3_600_000:  # within 1h
            new_oi.append(oi_val[idx])
        else:
            new_oi.append(0.0)

    if not any(new_fr) and not any(new_oi):
        return df  # nothing to merge (empty futures data)

    return df.with_columns([
        pl.Series("funding_rate",  new_fr, dtype=pl.Float64),
        pl.Series("open_interest", new_oi, dtype=pl.Float64),
    ])


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
