"""Quick OOS sweep across eligible tokens + timeframes to see where (if anywhere)
the current strategy has a positive walk-forward edge. Honest OOS only."""
from __future__ import annotations
import sys
from backtest.costs import BSCCostModel
from backtest.walk_forward import WalkForwardConfig, run_walk_forward
from backtest.engine import run_backtest
from scorecard import scorecard_from_result
from strategy.combined import StrategyParams, make_strategy
from strategy.optimizer import optimize, walk_forward_optimize_fn, walk_forward_strategy_factory
from data.binance_client import BinanceClient

ELIGIBLE = ["ETH", "CAKE", "UNI", "LINK", "AAVE"]
COST = BSCCostModel()


def run(symbol, interval, days, train, test):
    try:
        with BinanceClient() as c:
            bars = c.bars_from_df(
                c.fetch_ohlcv_historical(symbol, days_back=days, interval=interval,
                                         enrich_derivatives=True, enrich_sentiment=True))
    except Exception as e:
        return f"{symbol:5} {interval:5} LOAD-FAIL {type(e).__name__}"
    if len(bars) < train + test:
        return f"{symbol:5} {interval:5} too-few-bars({len(bars)})"
    wf = run_walk_forward(bars, walk_forward_strategy_factory, walk_forward_optimize_fn,
                          WalkForwardConfig(train_bars=train, test_bars=test),
                          cost_model=COST, initial_capital=10_000.0)
    m = wf.oos_metrics
    # single holdout for the shippable card + which weights won
    split = int(len(bars) * 0.7)
    best = optimize(bars[:split], cost_model=COST)
    s3 = "S3" if best.get("w_sentiment", 0) > 0 else "--"
    return (f"{symbol:5} {interval:5} bars={len(bars):5} "
            f"ret={m.get('total_return',0):+.2%} sortino={m.get('sortino',0):+.3f} "
            f"maxDD={m.get('max_drawdown',0):+.2%} fills={int(m.get('n_trades',0) or 0)} "
            f"win={m.get('win_rate',0):.0%} [{s3}]")


if __name__ == "__main__":
    tf = sys.argv[1] if len(sys.argv) > 1 else "daily"
    if tf == "daily":
        cfg = dict(interval="daily", days=730, train=365, test=90)
    else:
        cfg = dict(interval="1h", days=365, train=720, test=168)
    print(f"\n  OOS SWEEP  timeframe={tf}  (walk-forward, costs on, long-only)\n")
    for sym in ELIGIBLE:
        print("  " + run(sym, **cfg))
    print()
