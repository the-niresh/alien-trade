"""
Runtime wiring — assemble feed + core strategy + executor + Convex bridge into a
DecisionLoop from an AgentConfig. Factory functions keep the loop testable and
keep the sim/live parity invariant front-and-centre: the live strategy is built
by the SAME `make_strategy` + `RiskEngine` the backtest uses.

CLI:
    python -m agent.runtime --mode paper --cycles 50      # replay last N live bars
    python -m agent.runtime --mode paper                  # live cadence loop
    python -m agent.runtime --mode testnet --dry-run      # simulate-before-send only
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from typing import Optional

from backtest.costs import BSCCostModel
from backtest.engine import StrategyFn
from risk.engine import make_risk_strategy
from strategy.combined import make_strategy

from agent.config import AgentConfig
from agent.convex_bridge import ConvexBridge
from agent.executor import Executor, OnchainExecutor, PaperExecutor, TwakSwapExecutor
from agent.feed import BinanceLiveFeed, ReplayFeed
from agent.loop import DecisionLoop
from agent.qr import print_qr


def build_strategy(cfg: AgentConfig) -> StrategyFn:
    """The live strategy IS the sim strategy: core signals → RiskEngine wrapper."""
    inner = make_strategy(cfg.strategy)
    return make_risk_strategy(inner, cfg.risk, initial_capital=cfg.initial_capital)


def build_executor(cfg: AgentConfig, *, dry_run: bool = False) -> Executor:
    cost = BSCCostModel()
    if cfg.mode == "paper":
        return PaperExecutor(cost_model=cost)

    from exec.bnb import BNBExec

    # Default live path: self-custody via the twak CLI (keys stay on-device).
    if cfg.execution_backend == "twak":
        from agent.twak_cli import TwakCli

        # twak swap is mainnet; BNB SDK confirms the receipt on mainnet RPC.
        bnb = BNBExec(testnet=False)
        return TwakSwapExecutor(
            twak=TwakCli(chain=cfg.chain), risk_config=cfg.risk, cost_model=cost,
            bnb_exec=bnb, chain=cfg.chain, dry_run=dry_run,
        )

    # Alternate path: raw BNB SDK build/sign/broadcast (needs a key/signer).
    from exec.twak import TWAKClient

    bnb = BNBExec(testnet=(cfg.mode == "testnet"))
    signer = TWAKClient()
    return OnchainExecutor(
        bnb_exec=bnb, signer=signer, wallet_address=cfg.wallet_address,
        risk_config=cfg.risk, cost_model=cost, dry_run=dry_run,
    )


def build_bridge(cfg: AgentConfig) -> ConvexBridge:
    bridge = ConvexBridge(url=cfg.convex_url)
    if bridge.enabled:
        bridge.ensure_config(trading_mode=cfg.mode)
    return bridge


def build_second_brain(cfg: AgentConfig, bridge):
    """Step-6 Hermes + memory layer. Returns None when disabled or fully offline
    (no keys) so the loop keeps its Step-5 defaults (AllowAll, no reflection)."""
    if not cfg.second_brain_enabled:
        return None
    from agent.secondbrain import build_second_brain as _build
    sb = _build(params=cfg.strategy, bridge=bridge)
    return sb if sb.enabled else None


def build_loop(cfg: AgentConfig, *, feed=None, dry_run: bool = False,
               recover: bool = False) -> DecisionLoop:
    if feed is None:
        feed = BinanceLiveFeed(cfg.symbol, interval=cfg.bar_interval, history_bars=cfg.history_bars)
    bridge = build_bridge(cfg)
    sb = build_second_brain(cfg, bridge)
    # Lets the loop swap executors live when the UI toggles config.trading_mode
    # (only while flat — see DecisionLoop._sync_trading_mode). Same builder used
    # at boot, so a toggled mode is wired exactly like a launched one.
    from agent.notify import TelegramBot
    notifier = TelegramBot(bridge=bridge)
    notifier.start()   # launches daemon polling thread; no-op when token absent
    executor_factory = lambda m: build_executor(replace(cfg, mode=m), dry_run=dry_run)  # noqa: E731
    loop = DecisionLoop(
        feed=feed,
        strategy=build_strategy(cfg),
        executor=build_executor(cfg, dry_run=dry_run),
        bridge=bridge,
        params=cfg.strategy,
        symbol=cfg.symbol,
        mode=cfg.mode,
        initial_capital=cfg.initial_capital,
        base_position_usd=cfg.risk.base_position_usd,
        max_consecutive_losses=cfg.risk.max_consecutive_losses,
        mistake_avoidance=sb.avoidance if sb else None,
        reflection_writer=sb.reflection_writer if sb else None,
        executor_factory=executor_factory,
        enforce_activity_floor=cfg.enforce_activity_floor,
        notifier=notifier,
        autopilot_config=cfg.autopilot,
    )
    loop.second_brain = sb   # co-pilot / research / telemetry access (may be None)
    if recover:
        from agent.recovery import recover as _recover
        rep = _recover(loop)
        if rep.recovered:
            print(f"  [recovery] {rep.n_trades} trades, {rep.n_seen_cycles} executed cycles, "
                  f"units={rep.expected_units:.4f}, realized=${rep.realized_pnl:,.2f} :: {rep.note}")
        else:
            print(f"  [recovery] {rep.note}")
    return loop


def build_replay_loop(cfg: AgentConfig, bars, *, warmup: int = 0, dry_run: bool = False,
                      recover: bool = False) -> DecisionLoop:
    """Deterministic loop over a fixed bar list — paper rehearsal & parity checks."""
    return build_loop(cfg, feed=ReplayFeed(bars, warmup=warmup), dry_run=dry_run, recover=recover)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: Optional[list[str]] = None) -> None:
    ap = argparse.ArgumentParser(description="Alien-Trade live runtime")
    ap.add_argument("--mode", choices=["paper", "testnet", "mainnet"], default=None)
    ap.add_argument("--symbol", default="ETH")
    ap.add_argument("--cycles", type=int, default=None, help="run N cycles then stop")
    ap.add_argument("--dry-run", action="store_true", help="simulate-before-send only")
    ap.add_argument("--replay", action="store_true", help="replay recent live bars deterministically")
    ap.add_argument("--recover", action="store_true", help="rebuild state from Convex on startup")
    ap.add_argument("--activity-floor", action="store_true",
                    help="force >= 1 trade/day (Track-1 qualification; live window only)")
    args = ap.parse_args(argv)

    cfg = AgentConfig(symbol=args.symbol)
    if args.mode:
        cfg.mode = args.mode
    if args.activity_floor:
        cfg.enforce_activity_floor = True

    print(f"\n  ALIEN-TRADE runtime  ·  mode={cfg.mode}  symbol={cfg.symbol}  "
          f"convex={'on' if cfg.convex_url else 'offline'}")
    print_qr(cfg.pwa_url)

    if args.replay:
        from data.binance_client import BinanceClient
        bars = BinanceClient().fetch_recent_bars(cfg.symbol, cfg.bar_interval, cfg.history_bars)
        loop = build_replay_loop(cfg, bars, dry_run=args.dry_run)
        results = loop.run(max_cycles=args.cycles)
        _print_summary(results, loop)
        return

    loop = build_loop(cfg, dry_run=args.dry_run, recover=args.recover)
    if args.cycles:
        results = loop.run(max_cycles=args.cycles)
        _print_summary(results, loop)
    else:
        loop.run_forever(cfg.cycle_seconds)


def _print_summary(results, loop: DecisionLoop) -> None:
    fills = sum(1 for r in results if r.execution and r.execution.is_fill)
    last = results[-1] if results else None
    print("\n  -- run summary -----------------------------")
    print(f"  cycles    : {len(results)}")
    print(f"  fills     : {fills}")
    if last:
        print(f"  equity    : ${last.equity:,.2f}")
        print(f"  drawdown  : {last.drawdown_pct:.2%}")
        print(f"  realized  : ${loop.ledger.realized_pnl_total:,.2f}")
        print(f"  fees+gas  : ${loop.ledger.cumulative_fees + loop.ledger.cumulative_gas:,.2f}")
    print("  --------------------------------------------\n")


if __name__ == "__main__":
    main()
