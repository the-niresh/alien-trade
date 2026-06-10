"""
Walk-forward re-tune for one eligible symbol. Reusable for the live window:

    python retune.py --symbol ETH --interval 1h --days 365            # CMC (default)
    python retune.py --symbol ETH --source binance --interval 1h      # keyless fallback

Two honest, out-of-sample views (never selects on in-sample — locked decision #7):
  1. Walk-forward OOS report — is the edge robust across rolling windows?
  2. A single 70/30 optimise -> hold-out split — yields ONE shippable param set
     plus its OOS scorecard (the same core/scorecard.py the live agent reports).

DATA SOURCES:
  cmc      — CMCClient (needs CMC_API_KEY); the competition-aligned source. NOTE:
             the historical extended fields (funding_rate/open_interest/social_score/
             net_flow) are currently STUBBED to 0.0 in cmc_client._parse_ohlcv until
             the Agent Hub derivatives/social/flow endpoints are wired.
  binance  — public Binance spot klines (no key) enriched with real funding_rate
             and open_interest from the Binance Futures API (fapi, also free/public).
             This gives a live S1+S2 tune. social_score/net_flow remain 0.0 until
             the CMC Pro plan is available.

The script DETECTS whether the orthogonal signals are present and prints the caveat
when they're all zero, so the report never overstates what was actually tuned.
"""
from __future__ import annotations

import argparse

from backtest.costs import BSCCostModel
from backtest.engine import run_backtest
from backtest.walk_forward import WalkForwardConfig, print_oos_report, run_walk_forward
from scorecard import scorecard_from_result
from strategy.combined import StrategyParams, make_strategy
from strategy.optimizer import (
    optimize,
    walk_forward_optimize_fn,
    walk_forward_strategy_factory,
)


def _load_bars(source: str, symbol: str, interval: str, days: int):
    if source == "cmc":
        from data.cmc_client import CMCClient
        with CMCClient() as c:
            df = c.fetch_ohlcv_historical(symbol, days_back=days, interval=interval)
            return c.bars_from_df(df)
    if source == "binance":
        from data.binance_client import BinanceClient
        with BinanceClient() as c:
            # enrich_s2=True populates funding_rate + open_interest from Binance Futures
            # public endpoints (fapi, no key). Falls back gracefully on failure.
            df = c.fetch_ohlcv_historical(symbol, days_back=days, interval=interval,
                                           enrich_s2=True)
            return c.bars_from_df(df)
    raise ValueError(f"unknown --source {source!r} (use 'cmc' or 'binance')")


def _has_orthogonal_signals(bars) -> bool:
    """True if any bar carries non-zero funding/OI/social/flow — i.e. S2/S3/S4 have
    real data to work with (vs. an OHLCV-only feed where they're flat zeros)."""
    return any(
        b.funding_rate or b.open_interest or b.social_score or b.net_flow
        for b in bars
    )


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Walk-forward re-tune for one symbol")
    ap.add_argument("--symbol", default="ETH")
    ap.add_argument("--source", default="cmc", choices=["cmc", "binance"],
                    help="historical data source (cmc needs CMC_API_KEY)")
    ap.add_argument("--interval", default="1h", help="daily | 4h | 1h | 15m")
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--train", type=int, default=720, help="train bars per WF window")
    ap.add_argument("--test", type=int, default=168, help="test (OOS) bars per WF window")
    ap.add_argument("--capital", type=float, default=10_000.0)
    args = ap.parse_args(argv)

    try:
        bars = _load_bars(args.source, args.symbol, args.interval, args.days)
    except Exception as e:  # noqa: BLE001 — a CLI tool should explain, not stack-trace
        print(f"\n  data load failed (source={args.source}, symbol={args.symbol}): "
              f"{type(e).__name__}")
        if args.source == "cmc":
            print("  CMC historical OHLCV requires a paid plan — a free/basic key returns")
            print("  403 on /v2/cryptocurrency/ohlcv/historical (quotes/latest still works).")
            print("  Re-run with `--source binance` for a keyless OHLCV tune, or upgrade the")
            print("  CMC plan + wire the Agent Hub funding/OI/social/flow endpoints.\n")
        return
    full_signals = _has_orthogonal_signals(bars)
    sigset = "FULL (S1-S4)" if full_signals else \
        "S1 ONLY (funding/OI/social/flow flat — extended feed not wired)"
    print(f"\n  RE-TUNE  symbol={args.symbol}  source={args.source}  "
          f"interval={args.interval}  bars={len(bars)}  (~{args.days}d)")
    print(f"  signal set    : {sigset}")
    if len(bars) < args.train + args.test:
        print(f"  not enough bars ({len(bars)}) for train+test "
              f"({args.train}+{args.test}); fetch more --days.")
        return

    cost = BSCCostModel()

    # 1) Walk-forward robustness (re-optimises each window; OOS aggregate only)
    wf = run_walk_forward(
        bars, walk_forward_strategy_factory, walk_forward_optimize_fn,
        WalkForwardConfig(train_bars=args.train, test_bars=args.test),
        cost_model=cost, initial_capital=args.capital,
    )
    print_oos_report(wf)

    # 2) Single 70/30 optimise -> hold-out: one shippable param set + its OOS card
    split = int(len(bars) * 0.7)
    train, test = bars[:split], bars[split:]
    best = optimize(train, cost_model=cost, initial_capital=args.capital)
    params = StrategyParams(**{**best, "symbol": args.symbol})
    oos = run_backtest(test, make_strategy(params), initial_capital=args.capital, cost_model=cost)
    card = scorecard_from_result(
        oos, initial_capital=args.capital, timestamps=[b.timestamp for b in test])

    print("  -- 70/30 OPTIMISE -> HOLD-OUT (out-of-sample) --------------")
    print(f"  chosen params : ema_fast={best['ema_fast']}  ema_slow={best['ema_slow']}  "
          f"entry_threshold={best['entry_threshold']}")
    print(f"  objective     : {card.objective:.4f}   (sortino - 2*|maxDD|)")
    print(f"  sortino       : {card.sortino:.3f}")
    print(f"  total_return  : {card.total_return:.2%}")
    print(f"  max_drawdown  : {card.max_drawdown:.2%}")
    print(f"  calmar        : {card.calmar:.3f}")
    print(f"  n_trades      : {card.n_trades}   win_rate={card.win_rate:.0%}   "
          f"profit_factor={card.profit_factor}")
    print("  ------------------------------------------------------------")
    if not full_signals:
        print("  WARNING: S2/S3/S4 had no data (OHLCV-only feed) — this tuned S1 "
              "alone.\n  Wire the CMC Agent Hub funding/OI/social/flow endpoints into "
              "cmc_client\n  (_parse_ohlcv) and re-run for the full-signal tune.\n")
    else:
        print("  Full signal set (S1-S4) used.\n")


if __name__ == "__main__":
    main()
