"""
Free historical market sentiment - the Fear & Greed Index (alternative.me).

No API key, no paid plan: full daily history back to 2018. This is the free
historical S3 source that stands in for CMC Agent Hub social data until a paid
CMC plan is available. The index is market-wide (one value per day for the whole
crypto market), so the same series enriches every symbol's bars.

Output column: `social_score` carries the raw F&G index value in [0, 100]
(0 = Extreme Fear, 100 = Extreme Greed). The contrarian transform into a
[-1, 1] trading signal lives in `signals/sentiment.py` (fear_greed_signal),
never here - this module only sources and aligns the data, point-in-time.
"""
from __future__ import annotations

from pathlib import Path

import httpx
import polars as pl
from tenacity import retry, stop_after_attempt, wait_exponential

from config.constants import FEAR_GREED_BASE_URL

CACHE_DIR = Path(__file__).parent / "parquet"
FG_CACHE = CACHE_DIR / "feargreed_history.parquet"


class FearGreedClient:
    """Wraps the free alternative.me Fear & Greed Index endpoint."""

    def __init__(self):
        self._http = httpx.Client(base_url=FEAR_GREED_BASE_URL, timeout=30.0)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "FearGreedClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def fetch_history(self, force_refresh: bool = False) -> pl.DataFrame:
        """Full daily F&G history as a 2-column frame: timestamp_ms, social_score.

        Cached to parquet on first fetch. `force_refresh=True` re-pulls (the live
        loop refreshes daily to append the newest reading).
        Sorted ascending by timestamp.
        """
        if FG_CACHE.exists() and not force_refresh:
            return pl.read_parquet(FG_CACHE)
        df = self._fetch()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.write_parquet(FG_CACHE)
        return df

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _fetch(self) -> pl.DataFrame:
        # limit=0 returns the entire history (one reading per day).
        r = self._http.get("/fng/", params={"limit": 0, "format": "json"})
        r.raise_for_status()
        data = r.json().get("data", [])
        rows = [
            {
                "timestamp_ms": int(d["timestamp"]) * 1000,  # seconds -> ms
                "social_score": float(d["value"]),           # 0..100
            }
            for d in data
            if d.get("timestamp") and d.get("value") is not None
        ]
        rows.sort(key=lambda r: r["timestamp_ms"])
        return pl.DataFrame(
            rows,
            schema={"timestamp_ms": pl.Int64, "social_score": pl.Float64},
        )


def enrich_sentiment(df: pl.DataFrame, fg: pl.DataFrame | None = None) -> pl.DataFrame:
    """Merge the F&G index into an OHLCV frame's `social_score` column.

    Point-in-time forward-fill: each bar gets the most recent F&G reading whose
    timestamp is at or before the bar's timestamp (no look-ahead). Bars earlier
    than the first F&G reading keep social_score=0.0 (graceful - the signal
    degrades to neutral, see sentiment_signal).

    `fg` may be passed in (already fetched) to avoid a network call; otherwise it
    is loaded from cache / fetched.
    """
    if fg is None:
        with FearGreedClient() as c:
            fg = c.fetch_history()
    if fg.is_empty() or df.is_empty():
        return df

    fg = fg.sort("timestamp_ms")
    fg_ts = fg["timestamp_ms"].to_list()
    fg_val = fg["social_score"].to_list()

    import bisect

    new_scores: list[float] = []
    for ts in df["timestamp_ms"].to_list():
        idx = bisect.bisect_right(fg_ts, ts) - 1
        new_scores.append(fg_val[idx] if idx >= 0 else 0.0)

    return df.with_columns(pl.Series("social_score", new_scores, dtype=pl.Float64))
