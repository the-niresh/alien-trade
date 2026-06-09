"""
Paper smoke run — drive the live DecisionLoop over real historical bars to prove
the whole stack is alive: /core strategy + RiskEngine + executor + ledger + the
Convex bus. Deterministic (ReplayFeed), so it's also the Step 7 paper-rehearsal
entry point.

    # offline (no Convex writes)
    core/.venv/Scripts/python.exe -m agent.smoke

    # write live rows to a Convex deployment
    $env:CONVEX_URL="https://<deployment>.convex.cloud"; core/.venv/Scripts/python.exe -m agent.smoke
"""
from __future__ import annotations

import argparse

from backtest.data_loader import load_bars

from agent.config import AgentConfig
from agent.runtime import build_replay_loop, _print_summary


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Alien-Trade paper smoke run")
    ap.add_argument("--symbol", default="ETH")
    ap.add_argument("--bars", type=int, default=250, help="use the last N historical bars")
    args = ap.parse_args(argv)

    cfg = AgentConfig(symbol=args.symbol)
    cfg.mode = "paper"

    bars = load_bars(args.symbol)
    bars = bars[-args.bars:] if args.bars and len(bars) > args.bars else bars

    print(f"\n  paper smoke · {args.symbol} · {len(bars)} bars · "
          f"convex={'on' if cfg.convex_url else 'offline'}")

    loop = build_replay_loop(cfg, bars)
    results = loop.run()

    fills = sum(1 for r in results if r.execution and r.execution.is_fill)
    blocks = sum(1 for r in results if r.verdict == "block")
    print(f"  cycles={len(results)} fills={fills} blocked={blocks}")
    _print_summary(results, loop)


if __name__ == "__main__":
    main()
