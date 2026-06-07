"""
Load historical OHLCV parquet files from core/data/parquet/ into typed Bar lists.
Sorted by timestamp ascending. CMC extended fields default to 0.0 when absent.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import polars as pl

from backtest.engine import Bar

_PARQUET_DIR = Path(__file__).parent.parent / "data" / "parquet"

_REQUIRED_COLS = {"timestamp_ms", "open", "high", "low", "close", "volume"}
_EXTENDED_COLS = {
    "funding_rate": 0.0,
    "open_interest": 0.0,
    "social_score": 0.0,
    "net_flow": 0.0,
}


def load_bars(
    symbol: str,
    interval: str = "730d_daily",
    parquet_dir: Path = _PARQUET_DIR,
    start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
) -> list[Bar]:
    """
    Load bars for one symbol from disk.
    symbol: 'BNB', 'BTC', 'ETH'
    interval: suffix of the parquet filename, e.g. '730d_daily'
    Returns bars sorted ascending by timestamp.
    """
    path = parquet_dir / f"binance_{symbol}_{interval}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No parquet file at {path}. Run data pipeline first.")

    df = pl.read_parquet(path)
    df = _normalise_columns(df)

    if start_ms is not None:
        df = df.filter(pl.col("timestamp_ms") >= start_ms)
    if end_ms is not None:
        df = df.filter(pl.col("timestamp_ms") <= end_ms)

    df = df.sort("timestamp_ms")
    return _df_to_bars(df)


def load_multi(
    symbols: list[str] = ("BNB", "BTC", "ETH"),
    interval: str = "730d_daily",
    parquet_dir: Path = _PARQUET_DIR,
) -> dict[str, list[Bar]]:
    """Load bars for multiple symbols. Returns {symbol: bars}."""
    return {sym: load_bars(sym, interval, parquet_dir) for sym in symbols}


def _normalise_columns(df: pl.DataFrame) -> pl.DataFrame:
    """
    Rename columns to the canonical schema expected by Bar.
    Parquet files written by BinanceClient use 'open_time' or 'timestamp_ms'.
    """
    rename: dict[str, str] = {}
    cols = set(df.columns)

    if "open_time" in cols and "timestamp_ms" not in cols:
        rename["open_time"] = "timestamp_ms"

    if rename:
        df = df.rename(rename)

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Parquet missing required columns: {missing}")

    for col, default in _EXTENDED_COLS.items():
        if col not in df.columns:
            df = df.with_columns(pl.lit(default).alias(col))

    return df.select([
        "timestamp_ms", "open", "high", "low", "close", "volume",
        "funding_rate", "open_interest", "social_score", "net_flow",
    ])


def _df_to_bars(df: pl.DataFrame) -> list[Bar]:
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
        for row in df.iter_rows(named=True)
    ]
