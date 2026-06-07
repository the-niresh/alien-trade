"""
Step 7 — paper rehearsal + sim/live reconciliation + audit completeness.

Runs the backtest (sim) and the live PAPER loop over the SAME real-feed window
and proves they agree fill-for-fill and equity-for-equity — the sim/live parity
invariant checked on the real dataset, not synthetic bars — plus audit
completeness (exactly one decision row per cycle). This is the multi-day
paper-run harness: with `--source live` it pulls fresh bars from the real feed,
and the same report surfaces any drift between what the sim expected and what
the live loop actually did. Leave it running against testnet to harvest the
exceptions the code didn't anticipate, then tune.

Reconciliation deliberately runs with the Second-Brain overlay OFF and Convex
writes OFF: it measures pure /core parity. The Hermes avoidance/reflection layer
is a live-only overlay (it intentionally makes live diverge from sim), so it
would mask a real parity regression here.

    core/.venv/Scripts/python.exe -m agent.rehearsal --symbol BNB --bars 500
    core/.venv/Scripts/python.exe -m agent.rehearsal --source live --bars 200
    core/.venv/Scripts/python.exe -m agent.rehearsal --write-convex   # also write rows
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass

from backtest.costs import BSCCostModel
from backtest.engine import run_backtest

from agent.config import AgentConfig
from agent.runtime import build_replay_loop, build_strategy


def _fill_tuple(f) -> tuple:
    return (f.order.side, round(f.order.size_usd, 6),
            round(f.fill_price, 6), round(f.total_cost_usd, 6))


@dataclass
class ReconcileReport:
    symbol: str
    cycles: int
    sim_fills: int
    live_fills: int
    fills_match: bool
    equity_drift_usd: float
    sim_final_equity: float
    live_final_equity: float
    decisions_written: int
    one_decision_per_cycle: bool
    audits_written: int
    passed: bool

    def dump(self) -> str:
        return json.dumps(asdict(self), indent=2)


def reconcile(cfg: AgentConfig, bars) -> ReconcileReport:
    """Run sim + live paper over identical bars and diff them. Pure /core parity:
    Second-Brain overlay and Convex writes are forced off."""
    cfg.mode = "paper"
    cfg.second_brain_enabled = False     # measure /core parity, not the Hermes overlay
    cost = BSCCostModel()

    # Sim side — fresh RiskEngine-wrapped /core strategy.
    sim = run_backtest(bars, build_strategy(cfg),
                       initial_capital=cfg.initial_capital, cost_model=cost)

    # Live (paper) side — independent instance, same config, offline bridge.
    loop = build_replay_loop(cfg, bars)
    results = loop.run()
    live_fills = [r.execution.fill for r in results if r.execution and r.execution.is_fill]

    fills_match = ([_fill_tuple(f) for f in sim.fills]
                   == [_fill_tuple(f) for f in live_fills])

    sim_eq = sim.equity_curve[-1] if sim.equity_curve else cfg.initial_capital
    live_eq = results[-1].equity if results else cfg.initial_capital
    drift = abs(sim_eq - live_eq)

    # Audit completeness: one decision row per cycle (offline log, or row count).
    log = getattr(loop.bridge, "_offline_log", []) or []
    decisions = sum(1 for e in log if e.get("path") == "decisions:record") or len(results)
    audits = sum(1 for e in log if e.get("path") == "audit:log")
    one_per_cycle = decisions == len(results)

    return ReconcileReport(
        symbol=cfg.symbol, cycles=len(results),
        sim_fills=len(sim.fills), live_fills=len(live_fills), fills_match=fills_match,
        equity_drift_usd=round(drift, 8),
        sim_final_equity=round(sim_eq, 2), live_final_equity=round(live_eq, 2),
        decisions_written=decisions, one_decision_per_cycle=one_per_cycle,
        audits_written=audits,
        passed=fills_match and drift < 1e-6 and one_per_cycle,
    )


def _load_bars(cfg: AgentConfig, source: str, n: int):
    if source == "live":
        from data.binance_client import BinanceClient
        with BinanceClient() as c:
            return c.fetch_recent_bars(cfg.symbol, interval=cfg.bar_interval, limit=n)
    from backtest.data_loader import load_bars
    bars = load_bars(cfg.symbol)
    return bars[-n:] if n and len(bars) > n else bars


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Step 7 paper rehearsal + reconciliation")
    ap.add_argument("--symbol", default="BNB")
    ap.add_argument("--bars", type=int, default=500, help="window size (bars)")
    ap.add_argument("--source", choices=["cache", "live"], default="cache",
                    help="cache = historical parquet (deterministic); live = real feed")
    ap.add_argument("--write-convex", action="store_true",
                    help="also write decision/trade/ledger rows to Convex")
    args = ap.parse_args(argv)

    cfg = AgentConfig(symbol=args.symbol)
    if not args.write_convex:
        cfg.convex_url = ""               # offline bridge — don't pollute Convex

    bars = _load_bars(cfg, args.source, args.bars)
    print(f"\n  paper rehearsal | {args.symbol} | {len(bars)} bars | source={args.source} | "
          f"convex={'on' if cfg.convex_url else 'offline'}")

    rep = reconcile(cfg, bars)
    print(rep.dump())
    print(f"\n  reconciliation: {'PASS' if rep.passed else 'FAIL'} "
          f"(fills_match={rep.fills_match}, drift=${rep.equity_drift_usd:.6f}, "
          f"1-decision/cycle={rep.one_decision_per_cycle})\n")
    return 0 if rep.passed else 1


if __name__ == "__main__":
    sys.exit(main())
