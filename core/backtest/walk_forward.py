"""
Walk-forward validation harness.

Flow per window:
  train bars  →  optimize_fn(train)  →  best_params
  test bars   →  strategy_factory(best_params)  →  BacktestResult  (OOS only)

Roll by `test_bars` each iteration. Aggregate all OOS windows into one metric dict.
Never return or expose in-sample metrics - only oos_* keys are published.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from backtest.engine import Bar, BacktestResult, CostModelFn, StrategyFn, run_backtest
from backtest.regime import Regime, detect_regime, regime_slice_metrics

# ── Type aliases ──────────────────────────────────────────────────────────────

StrategyFactory = Callable[[dict], StrategyFn]   # params → strategy callable
OptimizeFn = Callable[[list[Bar]], dict]          # train bars → best params dict


# ── Config ────────────────────────────────────────────────────────────────────

@dataclass
class WalkForwardConfig:
    train_bars: int = 365    # ~1 year of daily bars per train window
    test_bars: int = 90      # ~3 months per OOS window
    min_train_bars: int = 60 # skip window if train set too short
    # OOS fills at the NEXT bar's open (realistic 1-bar execution latency) rather than
    # at the signal bar's close. Defaults True so out-of-sample numbers are honest -
    # filling at the same close that triggered the signal overstates performance.
    realistic_fill: bool = True


# ── Result ─────────────────────────────────────────────────────────────────────

@dataclass
class WalkForwardResult:
    oos_windows: list[BacktestResult] = field(default_factory=list)
    oos_metrics: dict = field(default_factory=dict)
    regime_metrics: dict[str, dict] = field(default_factory=dict)
    window_params: list[dict] = field(default_factory=list)  # params chosen per window


# ── Main harness ──────────────────────────────────────────────────────────────

def run_walk_forward(
    bars: list[Bar],
    strategy_factory: StrategyFactory,
    optimize_fn: OptimizeFn,
    config: WalkForwardConfig = WalkForwardConfig(),
    cost_model: CostModelFn | None = None,
    initial_capital: float = 10_000.0,
) -> WalkForwardResult:
    """
    Walk-forward loop. Returns only OOS (out-of-sample) results.
    In-sample optimization runs on `train_bars`; results are discarded.
    """
    result = WalkForwardResult()
    n = len(bars)
    window_start = 0

    while True:
        train_end = window_start + config.train_bars
        test_end = train_end + config.test_bars

        if train_end > n:
            break
        if (train_end - window_start) < config.min_train_bars:
            break

        train = bars[window_start:train_end]
        test = bars[train_end:test_end] if test_end <= n else bars[train_end:]

        if not test:
            break

        # Optimize on train - results intentionally thrown away after extracting params
        best_params = optimize_fn(train)
        result.window_params.append(best_params)

        strategy = strategy_factory(best_params)

        kwargs: dict = {
            "initial_capital": initial_capital,
            "next_bar_open_fill": config.realistic_fill,
        }
        if cost_model is not None:
            kwargs["cost_model"] = cost_model

        oos = run_backtest(test, strategy, **kwargs)
        result.oos_windows.append(oos)

        window_start += config.test_bars

    if result.oos_windows:
        result.oos_metrics = _aggregate_oos_metrics(result.oos_windows, initial_capital)
        result.regime_metrics = _aggregate_regime_metrics(result.oos_windows, bars)

    return result


# ── Aggregation ───────────────────────────────────────────────────────────────

def _aggregate_oos_metrics(windows: list[BacktestResult], initial_capital: float) -> dict:
    """
    Concatenate OOS equity curves across all windows, compute aggregate metrics.
    All keys are prefixed oos_ to make it impossible to confuse with in-sample.
    """
    all_returns: list[float] = []
    total_fills = 0
    winning_trades = 0
    total_trades = 0
    total_volume = 0.0

    for w in windows:
        curve = np.array(w.equity_curve, dtype=float)
        if len(curve) > 1:
            rets = np.diff(curve) / curve[:-1]
            all_returns.extend(rets.tolist())
        total_fills += len(w.fills)
        for f in w.fills:
            total_volume += f.order.size_usd
        # Win rate is over completed round-trip TRADES, not fills. (Previously
        # winning_fills was declared but never incremented → oos_win_rate always 0.)
        total_trades += len(w.trades)
        winning_trades += sum(1 for t in w.trades if t.pnl_usd > 0)

    if not all_returns:
        return {"oos_n_windows": len(windows), "oos_n_fills": 0}

    arr = np.array(all_returns, dtype=float)

    # Rebuild equity from concatenated returns for drawdown
    equity = np.cumprod(1 + arr) * initial_capital
    rolling_max = np.maximum.accumulate(equity)
    drawdowns = (equity - rolling_max) / rolling_max

    total_return = float(np.prod(1 + arr) - 1)
    mean_ret = float(arr.mean())
    std_ret = float(arr.std())
    sharpe = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0
    downside = arr[arr < 0]
    sortino = (mean_ret / downside.std() * np.sqrt(252)) if len(downside) > 0 and downside.std() > 0 else 0.0
    max_dd = float(drawdowns.min())
    calmar = total_return / abs(max_dd) if max_dd != 0 else 0.0
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
    avg_equity = float(equity.mean())
    turnover = (total_volume / avg_equity) if avg_equity > 0 else 0.0

    return {
        "oos_total_return": round(total_return, 6),
        "oos_sharpe": round(sharpe, 4),
        "oos_sortino": round(sortino, 4),
        "oos_max_drawdown": round(max_dd, 6),
        "oos_calmar": round(calmar, 4),
        "oos_win_rate": round(win_rate, 4),
        "oos_turnover": round(turnover, 4),
        "oos_n_fills": total_fills,
        "oos_n_trades": total_trades,
        "oos_n_windows": len(windows),
    }


def _aggregate_regime_metrics(
    windows: list[BacktestResult],
    bars: list[Bar],
) -> dict[str, dict]:
    """Compute per-regime breakdown across all OOS windows combined."""
    all_regimes: list[Regime] = []
    all_equity: list[float] = []
    all_bars: list[Bar] = []

    for w in windows:
        n = len(w.equity_curve)
        if n == 0:
            continue
        # We don't have exact bar slices per window stored, so approximate
        # by detecting regimes for each equity point using available bars
        all_equity.extend(w.equity_curve)
        all_bars.extend(bars[:n])  # best-effort - Step 3 wires this properly

    if not all_equity:
        return {}

    all_regimes = [
        detect_regime(all_bars[: i + 1])
        for i in range(len(all_equity))
    ]

    return regime_slice_metrics(all_bars, all_regimes, all_equity)


# ── Reporting helper ─────────────────────────────────────────────────────────

def print_oos_report(result: WalkForwardResult) -> None:
    """Print a human-readable OOS summary to stdout."""
    m = result.oos_metrics
    if not m:
        print("No OOS windows completed.")
        return

    print("\n" + "=" * 55)
    print("  WALK-FORWARD OUT-OF-SAMPLE REPORT")
    print("=" * 55)
    print(f"  Windows : {m.get('oos_n_windows', 0)}")
    print(f"  Fills   : {m.get('oos_n_fills', 0)}")
    print(f"  Return  : {m.get('oos_total_return', 0):.2%}")
    print(f"  Sharpe  : {m.get('oos_sharpe', 0):.3f}")
    print(f"  Sortino : {m.get('oos_sortino', 0):.3f}")
    print(f"  MaxDD   : {m.get('oos_max_drawdown', 0):.2%}")
    print(f"  Calmar  : {m.get('oos_calmar', 0):.3f}")
    print(f"  Win rate: {m.get('oos_win_rate', 0):.1%}")
    print(f"  Turnover: {m.get('oos_turnover', 0):.2f}x")
    print("=" * 55)
    if result.regime_metrics:
        print("  REGIME BREAKDOWN")
        for regime, rm in result.regime_metrics.items():
            if rm.get("n_bars", 0) == 0:
                continue
            print(f"  {regime:<10} bars={rm['n_bars']:>4}  "
                  f"sharpe={rm.get('sharpe', 0):>7.3f}  "
                  f"sortino={rm.get('sortino', 0):>7.3f}")
    print("=" * 55 + "\n")
