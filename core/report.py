"""
One-command walk-forward report (closes the Step 2 'deterministic + seeded, one
command reproduces a full report from a clean clone' item).

Honest by construction: out-of-sample only, full BSC cost model, regime-sliced.
Deterministic - fixed parquet history + a deterministic grid optimiser, so the
same clone always prints the same numbers.

    cd core && .venv/Scripts/python.exe -m report                  # BNB, risk engine on
    cd core && .venv/Scripts/python.exe -m report --symbol ETH
    cd core && .venv/Scripts/python.exe -m report --no-risk        # strategy only
"""
from __future__ import annotations

import argparse

from backtest.costs import BSCCostModel
from backtest.data_loader import load_bars
from backtest.walk_forward import WalkForwardConfig, print_oos_report, run_walk_forward
from risk.engine import make_risk_strategy
from risk.guardrails import RiskConfig
from strategy.optimizer import walk_forward_optimize_fn, walk_forward_strategy_factory


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Alien-Trade walk-forward OOS report")
    ap.add_argument("--symbol", default="BNB")
    ap.add_argument("--train", type=int, default=180, help="train bars per window")
    ap.add_argument("--test", type=int, default=90, help="OOS bars per window")
    ap.add_argument("--capital", type=float, default=10_000.0)
    ap.add_argument("--no-risk", action="store_true", help="disable the risk-engine wrapper")
    args = ap.parse_args(argv)

    bars = load_bars(args.symbol)
    cost = BSCCostModel()
    wf_cfg = WalkForwardConfig(train_bars=args.train, test_bars=args.test)

    if args.no_risk:
        factory = walk_forward_strategy_factory
    else:
        risk = RiskConfig()

        def factory(params):
            return make_risk_strategy(
                walk_forward_strategy_factory(params), risk, args.capital
            )

    result = run_walk_forward(
        bars, factory, walk_forward_optimize_fn, wf_cfg,
        cost_model=cost, initial_capital=args.capital,
    )

    print(f"\n  ALIEN-TRADE walk-forward report · {args.symbol} · "
          f"risk={'OFF' if args.no_risk else 'ON'} · costs=ON · {len(bars)} bars")
    print_oos_report(result)


if __name__ == "__main__":
    main()
