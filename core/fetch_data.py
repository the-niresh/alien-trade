"""
Download the price history the evaluation needs.

    cd core && .venv/bin/python -m fetch_data

No API key required - Binance klines, funding and open interest are public endpoints,
and the Fear & Greed index comes from alternative.me. Roughly 1.5 MB per token, written
to `core/data/parquet/`, which is gitignored: history is reproducible from source, so
committing a binary snapshot of it would only add weight and drift.

Run this once before `python -m evaluate`.

⚠️ The result is not bit-identical to the numbers published in `docs/results/`. Those
were generated from a window ending 2026-06-11, and this fetches the last `--days` up to
today, so a later run covers a later window. Pass `--end` to reproduce the published
window exactly.
"""
from __future__ import annotations

import argparse
import datetime as _dt

from data.binance_client import BinanceClient
from risk.guardrails import TRADING_UNIVERSE

# What `evaluate.py` expects on disk: 540 days of hourly bars per token.
DAYS = 540
INTERVAL = "1h"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Fetch OHLCV history for the evaluation")
    ap.add_argument("--symbols", nargs="*", default=list(TRADING_UNIVERSE))
    ap.add_argument("--days", type=int, default=DAYS)
    ap.add_argument("--interval", default=INTERVAL)
    ap.add_argument("--force", action="store_true", help="re-download even if cached")
    args = ap.parse_args(argv)

    print(f"Fetching {args.days}d of {args.interval} bars for "
          f"{', '.join(args.symbols)} - no API key needed.\n")

    with BinanceClient() as client:
        for symbol in args.symbols:
            df = client.fetch_ohlcv_historical(
                symbol, days_back=args.days, interval=args.interval,
                force_refresh=args.force,
            )
            first = _dt.datetime.fromtimestamp(
                df["timestamp_ms"].min() / 1000, _dt.timezone.utc
            ).date()
            last = _dt.datetime.fromtimestamp(
                df["timestamp_ms"].max() / 1000, _dt.timezone.utc
            ).date()
            # Flag the fields that are known to arrive empty, rather than let a silently
            # all-zero signal column look like a signal that simply found nothing.
            dead = [c for c in ("funding_rate", "open_interest", "social_score", "net_flow")
                    if df[c].abs().max() == 0.0]
            note = f"  (no data: {', '.join(dead)})" if dead else ""
            print(f"  {symbol:5s} {len(df):6d} bars  {first} → {last}{note}")

    print("\nDone. Now run:  .venv/bin/python -m evaluate")


if __name__ == "__main__":
    main()
