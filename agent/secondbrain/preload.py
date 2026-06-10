"""
2-year historical pre-load → institutional memory (run once, before go-live).

The agent must not be blank at launch. This walks the 2-year dataset and, at
each point-in-time slice, labels the period with {regime, dominant_signal,
outcome} and stores it in Upstash Vector (kind="institutional"). The label's
*outcome* uses the forward return over the next `horizon` bars — look-ahead is
fine here because we are labelling the **past** for memory, not making a live
decision. The regime and signals at each slice are strictly point-in-time.

Both the regime detector's co-pilot narrative and the co-pilot chat can later
query this memory: "what did the last 2 years teach us about buying in a trend
regime driven by momentum?"

Run:  core/.venv/Scripts/python.exe -m agent.secondbrain.preload
      core/.venv/Scripts/python.exe -m agent.secondbrain.preload --symbols BNB,BTC,ETH --horizon 10
"""
from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from backtest.engine import Bar
from backtest.regime import detect_regime
from data.binance_client import BinanceClient
from strategy.combined import StrategyParams, score_breakdown

from agent.secondbrain.schema import KIND_INSTITUTIONAL, dominant_signal, setup_key
from agent.secondbrain.vector import VectorStore

load_dotenv(Path(__file__).resolve().parents[2] / ".env.local")

WARMUP = 60   # bars before the first label (≥ s1_slow + buffer)


def preload_dataset(
    vector: VectorStore,
    *,
    symbols: list[str],
    params: StrategyParams | None = None,
    days_back: int = 730,
    horizon: int = 10,
    stride: int = 5,
) -> int:
    """Label point-in-time slices across the dataset → upsert institutional memory.
    Returns the number of records written. Idempotent (id keyed on symbol+ts)."""
    params = params or StrategyParams()
    client = BinanceClient()
    written = 0
    try:
        for symbol in symbols:
            df = client.fetch_ohlcv_historical(symbol, days_back=days_back, interval="daily")
            bars = client.bars_from_df(df)
            written += _label_symbol(vector, symbol, bars, params, horizon, stride)
    finally:
        client.close()
    return written


def _label_symbol(vector, symbol, bars: list[Bar], params, horizon, stride) -> int:
    n = len(bars)
    written = 0
    for i in range(WARMUP, n - horizon, stride):
        history = bars[: i + 1]
        regime = detect_regime(history).value
        breakdown = score_breakdown(history, params)
        signals = {k: breakdown.get(k) for k in ("momentum", "derivatives", "sentiment", "flow")}
        target = breakdown.get("target", 0.0)
        side = "buy" if target >= 0 else "sell"

        entry, exit_ = bars[i].close, bars[i + horizon].close
        fwd = (exit_ - entry) / entry if entry > 0 else 0.0
        win = (side == "buy" and fwd > 0) or (side == "sell" and fwd < 0)
        outcome_pnl = fwd if side == "buy" else -fwd     # signed to the side taken

        key = setup_key(regime, signals, side)
        ok = vector.upsert(
            id=f"inst-{symbol}-{bars[i].timestamp}",
            text=f"{symbol}: {key}",
            metadata={
                "kind": KIND_INSTITUTIONAL,
                "symbol": symbol,
                "regime": regime,
                "dominant_signal": dominant_signal(signals),
                "side": side,
                "setup_key": key,
                "fwd_return": round(fwd, 6),
                "outcome_pnl_usd": round(outcome_pnl * 1000.0, 4),  # ~$ on a $1k clip
                "outcome_label": "win" if win else "loss",
                "timestamp_ms": bars[i].timestamp,
            },
        )
        written += 1 if ok else 0
    return written


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="2-year institutional-memory pre-load")
    ap.add_argument("--symbols", default="BNB,BTC,ETH")
    ap.add_argument("--days-back", type=int, default=730)
    ap.add_argument("--horizon", type=int, default=10)
    ap.add_argument("--stride", type=int, default=5)
    args = ap.parse_args(argv)

    import os
    vector = VectorStore(
        url=os.environ.get("UPSTASH_VECTOR_REST_URL", ""),
        token=os.environ.get("UPSTASH_VECTOR_REST_TOKEN", ""),
    )
    mode = "Upstash Vector" if vector.enabled else "OFFLINE (in-memory — set UPSTASH_VECTOR_* to persist)"
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    print(f"\n  2-year pre-load -> {mode}\n  symbols={symbols} horizon={args.horizon} stride={args.stride}")

    n = preload_dataset(vector, symbols=symbols, days_back=args.days_back,
                        horizon=args.horizon, stride=args.stride)
    print(f"  institutional memories written: {n}")
    if not vector.enabled:
        print(f"  (offline index holds {n} records in this process only)")
    vector.close()


if __name__ == "__main__":
    main()
