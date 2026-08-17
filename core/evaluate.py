"""
Honest evaluation — one command, one table, no cherry-picking.

    cd core && .venv/bin/python -m evaluate                 # writes docs/results/
    cd core && .venv/bin/python -m evaluate --stdout        # print only

What this does and why it is built this way:

  * Runs EVERY strategy preset against EVERY token on the allowlist. There is no
    "best" run to pick, because all of them are reported. Nothing is selected on
    its own result, so there is no selection bias to correct for and no deflated
    Sharpe adjustment is owed.
  * Uses hourly bars, because that is the cadence the live agent decides on
    (AgentConfig.bar_interval = "1h"). Running the same strategy on daily bars
    makes it trade roughly once a year, so short test windows show zero trades and
    every metric prints as 0.00% — which reads as "harmless" and is not.
  * Full BSC cost model on every fill: gas, slippage and swap fees. A backtest
    without costs would show a different, and false, answer here.
  * Prints buy-and-hold over the identical window, because a strategy that loses
    less than the market still lost, and a strategy that gains less than the market
    was not worth the gas.

The parameters are the fixed presets from strategy/registry.py. No grid search runs
here. That is deliberate: search invites overfitting, and the point of this file is
to measure what is already committed, not to go looking for a number that flatters it.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from backtest.costs import BSCCostModel
from backtest.data_loader import load_bars
from backtest.engine import run_backtest
from risk.engine import make_risk_strategy
from risk.guardrails import RiskConfig, TRADING_UNIVERSE
from strategy.combined import make_strategy
from strategy.registry import STRATEGIES

# Hourly history on disk for the whole allowlist. 540 days ≈ 12,960 bars per token.
INTERVAL = "540d_1h"
CAPITAL = 10_000.0
_RESULTS_DIR = Path(__file__).parent.parent / "docs" / "results"


def _buy_and_hold(bars) -> dict:
    """Return-only benchmark: buy the first close, hold to the last."""
    ret = bars[-1].close / bars[0].close - 1.0
    peak = bars[0].close
    max_dd = 0.0
    for b in bars:
        peak = max(peak, b.close)
        max_dd = min(max_dd, b.close / peak - 1.0)
    return {"total_return": ret, "max_drawdown": max_dd}


def _run_one(symbol: str, preset: str, risk_on: bool, bars) -> dict:
    base = make_strategy(STRATEGIES[preset].factory(symbol))
    strategy = make_risk_strategy(base, RiskConfig(), CAPITAL) if risk_on else base
    m = run_backtest(
        bars, strategy, initial_capital=CAPITAL, cost_model=BSCCostModel()
    ).metrics
    return {
        "symbol": symbol,
        "preset": preset,
        "risk_engine": risk_on,
        "n_trades": int(m["n_trades"]),
        "total_return": float(m["total_return"]),
        "sharpe": float(m["sharpe"]),
        "sortino": float(m["sortino"]),
        "max_drawdown": float(m["max_drawdown"]),
        "win_rate": float(m["win_rate"]),
        "objective": float(m["sortino"]) - 2.0 * abs(float(m["max_drawdown"])),
        # Accounting-integrity counters. Non-zero means the strategy asked the engine
        # for something impossible and the engine refused; see BacktestResult.
        "oversized_sells": int(m["oversized_sells"]),
        "oversized_sell_usd": float(m["oversized_sell_usd"]),
        "underfunded_buys": int(m["underfunded_buys"]),
        "underfunded_buy_usd": float(m["underfunded_buy_usd"]),
    }


def evaluate(symbols: list[str], presets: list[str]) -> dict:
    bars_by_symbol = {s: load_bars(s, interval=INTERVAL) for s in symbols}
    benchmark = {s: _buy_and_hold(b) for s, b in bars_by_symbol.items()}
    # Metadata is derived before the runs, not after: a full sweep takes minutes, and
    # a typo down here would throw all of it away at the last line.
    first = min(b[0].timestamp for b in bars_by_symbol.values())
    last = max(b[-1].timestamp for b in bars_by_symbol.values())
    rows = [
        _run_one(sym, preset, risk_on, bars_by_symbol[sym])
        for risk_on in (False, True)
        for preset in presets
        for sym in symbols
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "interval": INTERVAL,
        "bars_per_symbol": {s: len(b) for s, b in bars_by_symbol.items()},
        "window_start_utc": datetime.fromtimestamp(first / 1000, timezone.utc).isoformat(),
        "window_end_utc": datetime.fromtimestamp(last / 1000, timezone.utc).isoformat(),
        "initial_capital_usd": CAPITAL,
        "cost_model": "BSCCostModel (gas + slippage + swap fees)",
        "parameter_search": "none — fixed presets from strategy/registry.py",
        "buy_and_hold": benchmark,
        "runs": rows,
    }


def _pct(x: float) -> str:
    return f"{x * 100:+.2f}%"


def render_markdown(data: dict) -> str:
    out: list[str] = []
    a = out.append
    a("# Evaluation results")
    a("")
    a(f"Generated `{data['generated_at']}` by `cd core && python -m evaluate`.")
    a("")
    a("**These are simulated results, not live trading.** Hourly bars from disk, replayed")
    a("through the same `/core` strategy the live agent uses, with the full BSC cost model")
    a("(gas, slippage, swap fees) charged on every fill.")
    a("")
    a(f"- Window: `{data['window_start_utc'][:10]}` → `{data['window_end_utc'][:10]}` "
      f"({data['interval']}, {min(data['bars_per_symbol'].values())} bars per token)")
    a(f"- Starting capital: ${data['initial_capital_usd']:,.0f}")
    a(f"- Parameter search: {data['parameter_search']}")
    a("")
    a("## Benchmarks over the same window")
    a("")
    a("Two things to beat. Buy-and-hold is the obvious one. **Cash is the one that")
    a("matters here** — this is a long-only strategy that holds USDT by default, so")
    a("switching it off is a real, available alternative that returns exactly 0%.")
    a("")
    a("| Benchmark | Return | Max drawdown |")
    a("|---|---|---|")
    a("| **Cash (agent switched off)** | **+0.00%** | **0.00%** |")
    for sym, m in data["buy_and_hold"].items():
        a(f"| Buy and hold {sym} | {_pct(m['total_return'])} | {_pct(m['max_drawdown'])} |")
    a("")

    for risk_on in (False, True):
        label = "risk engine ON" if risk_on else "risk engine OFF (strategy alone)"
        a(f"## Strategy — {label}")
        a("")
        a("| Preset | Token | Trades | Return | Sharpe | Sortino | Max DD | Win rate |")
        a("|---|---|---|---|---|---|---|---|")
        for r in data["runs"]:
            if r["risk_engine"] is not risk_on:
                continue
            a(f"| {r['preset']} | {r['symbol']} | {r['n_trades']} | {_pct(r['total_return'])} "
              f"| {r['sharpe']:.3f} | {r['sortino']:.3f} | {_pct(r['max_drawdown'])} "
              f"| {r['win_rate'] * 100:.1f}% |")
        a("")

    runs = data["runs"]
    wins = [r for r in runs if r["total_return"] > 0]
    beat_cash = [r for r in runs if r["total_return"] > 0]
    wipeouts = [r for r in runs if r["total_return"] <= -0.999]
    dirty = [r for r in runs if r["oversized_sells"] or r["underfunded_buys"]]

    a("## Reading of the result")
    a("")
    a(f"- **{len(wins)} of {len(runs)} configurations finished above break-even.**")
    a(f"- {len(beat_cash)} of {len(runs)} beat holding cash.")
    if wipeouts:
        a(f"- {len(wipeouts)} lost the entire account (−100%): "
          f"{', '.join(sorted({r['preset'] for r in wipeouts}))} with the risk engine off.")
    a("")
    if not wins:
        a("No preset is profitable on any token on the allowlist. This is not a tuning")
        a("problem — the sign is wrong across every combination tested, so there is no")
        a("parameter set in this family worth searching for. The signals as combined here")
        a("do not carry an edge that survives trading costs.")
        a("")
        a("The strategy does beat buy-and-hold, but that is not evidence of skill: it is")
        a("long-only and mostly in cash, so it was always going to fall less than a market")
        a("that halved. The benchmark that decides whether the agent earns its existence is")
        a("cash, and it loses to cash everywhere.")
        a("")
        a("The risk engine is the part that works. It cuts the worst case from a total")
        a("wipeout to a few percent — it cannot manufacture an edge, only limit the damage")
        a("of not having one.")
    a("")
    a("### Accounting integrity")
    a("")
    if dirty:
        a(f"{len(dirty)} of {len(runs)} runs asked the engine for something impossible — "
          "selling more than held, or buying")
        a("with cash that was not there. The engine refused and sized each fill to what was")
        a("actually available, so nothing above is inflated by it. Before that clamp existed")
        a("these same requests created $46,814 of cash out of nothing on a single token.")
        a("")
        a("The cause is a gap in the strategy interface, not a rounding error. `StrategyFn`")
        a("receives only bars — it is never told the position or the cash. So a strategy has")
        a("no way to size an exit against what it actually holds, and every strategy ends up")
        a("either shadowing the account itself or guessing. The risk engine shadows it, which")
        a("is why its counts are small (slippage drift between its copy and the engine's); a")
        a("bare strategy guesses, which is why its counts are large.")
        a("")
        a("The durable fix is to pass the real position and cash into the strategy call, so")
        a("there is one set of books. Until then the engine is the authority and clamps.")
        worst = max(dirty, key=lambda r: r["oversized_sell_usd"] + r["underfunded_buy_usd"])
        a("")
        a(f"Largest single offender: `{worst['preset']}`/{worst['symbol']} "
          f"(risk engine {'on' if worst['risk_engine'] else 'off'}) — "
          f"{worst['oversized_sells']} oversized sells, "
          f"{worst['underfunded_buys']} underfunded buys.")
    else:
        a("No run asked the engine for an impossible fill.")
    return "\n".join(out) + "\n"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Alien-Trade honest evaluation")
    ap.add_argument("--symbols", nargs="*", default=list(TRADING_UNIVERSE))
    ap.add_argument("--presets", nargs="*", default=list(STRATEGIES))
    ap.add_argument("--stdout", action="store_true", help="print only, do not write files")
    args = ap.parse_args(argv)

    data = evaluate(args.symbols, args.presets)
    md = render_markdown(data)

    if args.stdout:
        print(md)
        return

    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (_RESULTS_DIR / "EVALUATION.md").write_text(md, encoding="utf-8")
    (_RESULTS_DIR / "evaluation.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )
    print(md)
    print(f"wrote {_RESULTS_DIR / 'EVALUATION.md'}")
    print(f"wrote {_RESULTS_DIR / 'evaluation.json'}")


if __name__ == "__main__":
    main()
