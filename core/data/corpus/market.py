"""Market-data corpus fetchers (AWAKE_SPRINT §4.1).

TradFi daily history (SPX/NDX/gold/DXY/VIX) via stooq, normalized to the canonical
OHLCV columns the rest of /core uses. The network loader is injectable (`fetch=`) so
tests stay offline. Crypto history reuses the existing binance_client / cmc_client.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Callable

import pandas as pd

CANON_COLUMNS = ["timestamp_ms", "open", "high", "low", "close", "volume"]

# stooq symbol aliases for the TradFi macro set we care about.
STOOQ_SYMBOLS = {
    "SPX": "^spx", "NDX": "^ndx", "GOLD": "xauusd", "DXY": "^dxy", "VIX": "^vix",
}


def _stooq_fetch(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Daily OHLCV from stooq as canonical columns. Real network call."""
    import httpx

    s = STOOQ_SYMBOLS.get(symbol.upper(), symbol.lower())
    d1 = start.replace("-", "")
    d2 = end.replace("-", "")
    url = f"https://stooq.com/q/d/l/?s={s}&d1={d1}&d2={d2}&i=d"
    raw = httpx.get(url, timeout=15).text
    df = pd.read_csv(io.StringIO(raw))
    df.columns = [c.lower() for c in df.columns]
    df["timestamp_ms"] = (
        pd.to_datetime(df["date"]).astype("int64") // 1_000_000
    )
    df["volume"] = df.get("volume", 0.0)
    return df[CANON_COLUMNS]


def fetch_tradfi(
    symbols: list[str], start: str, end: str, *,
    fetch: Callable[[str, str, str], pd.DataFrame] = _stooq_fetch,
) -> pd.DataFrame:
    """Fetch daily bars for `symbols`, tagged with a `symbol` column and concatenated.
    Returns the canonical OHLCV columns (+ `symbol`)."""
    frames = []
    for sym in symbols:
        df = fetch(sym, start, end).copy()
        df["symbol"] = sym
        frames.append(df[CANON_COLUMNS + ["symbol"]])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=CANON_COLUMNS + ["symbol"]
    )


def _utcms(dt: str) -> int:
    return int(datetime.fromisoformat(dt).timestamp() * 1000)
