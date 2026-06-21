"""Thesis evaluation harness (AWAKE_SPRINT §4.3/§4.4) — the throughput lever.

Turns a distilled thesis card's `proposed_rule` (a DSL dict) into a per-asset
out-of-sample scorecard across the eligible universe `{ETH,CAKE,UNI,LINK,AAVE}`,
using the SHARED /core engine + the real BSC cost model. No separate sim path
(locked decision #2): a DSL rule is compiled to a long/flat position series, that
series drives a `StrategyFn`, and the SAME `run_backtest` + `scorecard_from_result`
the live agent uses scores it. The objective is the locked rubric `sortino - 2·|maxDD|`.

Methodology (anti-data-snooping, §4.4):
  - The DSL rules are PARAMETER-FREE (no per-window fitting → nothing to overfit at the
    rule level; the ≤1-knob-per-iteration discipline lives in how rules are authored).
    A single forward pass over the development series is therefore genuine OOS for the
    rule's behaviour; indicators warm up causally (proven by test_positions_are_causal).
  - The meta-level snooping risk (trying many rules, keeping winners) is handled by the
    trial registry (THESIS_LEDGER) + the Deflated Sharpe gate (n_trials) + a final
    untouched holdout scored EXACTLY ONCE on survivors (holdout.use_once()).
  - Keep gate: a thesis is VALIDATED only if its dev objective beats `threshold`
    (default 0.0 — "beat sitting in cash", the bar established 2026-06-11) on
    >= `min_beat` of 5 assets.

Sizing is fixed-notional (default $1000 on $10k capital), identical to the committed
baseline strategy (core/strategy/combined.py) and faithful to the agent's real
fixed-size `twak swap` execution — so dev objectives are directly comparable to the
documented v2 numbers AND to the 0.0 cash bar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd

from backtest.costs import DEFAULT_BSC_COST
from backtest.deflated_sharpe import deflated_sharpe
from backtest.engine import Bar, Order, StrategyFn, run_backtest
from backtest.holdout import holdout_split
from scorecard import scorecard_from_result
from strategy.dsl import compile_rule

ELIGIBLE = ("ETH", "CAKE", "UNI", "LINK", "AAVE")
LAMBDA = 2.0  # rubric drawdown weight (locked decision #6)

_DEFAULT_SIZE_USD = 1_000.0
_DEFAULT_CAPITAL = 10_000.0
_DEFAULT_HOLDOUT_DAYS = 50
_BARS_PER_DAY_1H = 24


def objective(sortino: float, max_drawdown: float) -> float:
    """The locked Track-1 rubric objective: sortino − 2·|maxDD|."""
    return float(sortino) - LAMBDA * abs(float(max_drawdown))


# ── DSL rule → position series → StrategyFn ───────────────────────────────────

def _bars_to_df(bars: list[Bar]) -> pd.DataFrame:
    return pd.DataFrame({
        "open": [b.open for b in bars],
        "high": [b.high for b in bars],
        "low": [b.low for b in bars],
        "close": [b.close for b in bars],
        "volume": [b.volume for b in bars],
        "funding": [b.funding_rate for b in bars],
        "sentiment": [b.social_score for b in bars],
    })


def _positions(rule: dict, bars: list[Bar]) -> np.ndarray:
    """Compile the DSL rule and return its 0/1 long/flat position series over `bars`.
    Causal by construction (the DSL only uses past-looking indicators) — see the
    no-lookahead test."""
    if not bars:
        return np.zeros(0, dtype=int)
    run = compile_rule(rule)
    pos = run(_bars_to_df(bars))
    return np.asarray(pos).astype(int)


def rule_to_strategy(positions: np.ndarray, *, size_usd: float = _DEFAULT_SIZE_USD,
                     symbol: str = "ASSET") -> StrategyFn:
    """Adapt a precomputed long/flat position series into a `StrategyFn` for the shared
    engine. Emits a fixed-notional buy on a flat→long transition and a sell on
    long→flat. The engine starts flat, so a series that opens at 1 buys on bar 0."""
    pos = np.asarray(positions).astype(int)
    held = {"v": 0}

    def strat(history: list[Bar]) -> Optional[Order]:
        i = len(history) - 1
        bar = history[-1]
        want = int(pos[i]) if 0 <= i < len(pos) else 0
        if want == 1 and held["v"] == 0:
            held["v"] = 1
            return Order(side="buy", size_usd=size_usd, symbol=symbol,
                         timestamp=bar.timestamp)
        if want == 0 and held["v"] == 1:
            held["v"] = 0
            return Order(side="sell", size_usd=size_usd, symbol=symbol,
                         timestamp=bar.timestamp)
        return None

    return strat


# ── Per-asset evaluation ──────────────────────────────────────────────────────

@dataclass
class AssetResult:
    asset: str
    objective: float
    sortino: float
    total_return: float
    max_drawdown: float
    n_fills: int
    sharpe_per_bar: float  # un-annualised, for the Deflated Sharpe gate
    n_obs: int             # number of return observations (for DSR)


def _per_bar_sharpe(equity: list[float]) -> float:
    arr = np.asarray(equity, dtype=float)
    if len(arr) < 2:
        return 0.0
    rets = np.diff(arr) / np.where(arr[:-1] == 0, 1, arr[:-1])
    sd = rets.std()
    return float(rets.mean() / sd) if sd > 0 else 0.0


def evaluate_on_bars(rule: dict, bars: list[Bar], *, asset: str = "ASSET",
                     size_usd: float = _DEFAULT_SIZE_USD,
                     initial_capital: float = _DEFAULT_CAPITAL,
                     positions: Optional[np.ndarray] = None) -> AssetResult:
    """Score a rule on one contiguous bar series with the real BSC cost model.

    `positions`, if given, is used instead of recomputing — this lets a holdout slice
    inherit the warmed-up indicator state from the full series."""
    pos = _positions(rule, bars) if positions is None else np.asarray(positions).astype(int)
    strat = rule_to_strategy(pos, size_usd=size_usd, symbol=asset)
    result = run_backtest(bars, strat, initial_capital=initial_capital,
                          cost_model=DEFAULT_BSC_COST)
    card = scorecard_from_result(result, initial_capital)
    return AssetResult(
        asset=asset,
        objective=card.objective,
        sortino=card.sortino,
        total_return=card.total_return,
        max_drawdown=card.max_drawdown,
        n_fills=len(result.fills),
        sharpe_per_bar=_per_bar_sharpe(result.equity_curve),
        n_obs=max(len(result.equity_curve) - 1, 0),
    )


# ── Full-universe thesis evaluation ───────────────────────────────────────────

@dataclass
class ThesisEval:
    rule: dict
    per_asset: list[AssetResult]
    n_assets: int
    n_beat: int
    threshold: float
    verdict: str                       # "VALIDATED" | "FALSIFIED"
    holdout: Optional[dict] = None     # populated ONCE for survivors
    deflated_sharpe: Optional[float] = None


def _load_eligible_bars(interval: str = "540d_1h") -> dict[str, list[Bar]]:
    from backtest.data_loader import load_bars
    return {sym: load_bars(sym, interval) for sym in ELIGIBLE}


def evaluate_thesis(rule: dict, *, bars_by_asset: Optional[dict[str, list[Bar]]] = None,
                    interval: str = "540d_1h", threshold: float = 0.0, min_beat: int = 4,
                    n_trials: int = 1, size_usd: float = _DEFAULT_SIZE_USD,
                    initial_capital: float = _DEFAULT_CAPITAL,
                    holdout_days: int = _DEFAULT_HOLDOUT_DAYS,
                    bars_per_day: int = _BARS_PER_DAY_1H) -> ThesisEval:
    """Evaluate a DSL rule across the eligible universe at OOS, then — only if it clears
    the keep gate — score the untouched holdout once and compute the Deflated Sharpe.

    bars_by_asset: inject bars for offline tests; otherwise load from parquet.
    """
    bars_by_asset = bars_by_asset if bars_by_asset is not None else _load_eligible_bars(interval)

    # Reserve the final holdout per asset; develop (select) only on the train portion.
    splits = {a: holdout_split(_to_df(bars), holdout_days=holdout_days,
                               bars_per_day=bars_per_day)
              for a, bars in bars_by_asset.items()}

    per_asset: list[AssetResult] = []
    for asset, bars in bars_by_asset.items():
        n_hold = min(holdout_days * bars_per_day, len(bars))
        dev_bars = bars[: len(bars) - n_hold]
        per_asset.append(evaluate_on_bars(rule, dev_bars, asset=asset,
                                          size_usd=size_usd,
                                          initial_capital=initial_capital))

    n_beat = sum(1 for r in per_asset if r.objective > threshold)
    verdict = "VALIDATED" if n_beat >= min_beat else "FALSIFIED"

    ev = ThesisEval(rule=rule, per_asset=per_asset, n_assets=len(per_asset),
                    n_beat=n_beat, threshold=threshold, verdict=verdict)

    if verdict == "VALIDATED":
        ev.holdout = _score_holdout(rule, bars_by_asset, size_usd, initial_capital,
                                    holdout_days, bars_per_day, splits)
        ev.deflated_sharpe = _holdout_dsr(ev.holdout, n_trials)
    return ev


def _to_df(bars: list[Bar]) -> pd.DataFrame:
    # holdout_split only needs len(); a thin frame keeps it cheap and use_once() intact.
    return pd.DataFrame({"close": [b.close for b in bars]})


def _score_holdout(rule, bars_by_asset, size_usd, initial_capital, holdout_days,
                   bars_per_day, splits) -> dict:
    """Score the reserved tail of each asset ONCE. The holdout indicators inherit
    warm-up from the full series (we precompute positions over all bars, then slice)."""
    results: list[AssetResult] = []
    for asset, bars in bars_by_asset.items():
        splits[asset].use_once()  # mechanical single-use guard (raises on re-use)
        n_hold = min(holdout_days * bars_per_day, len(bars))
        cut = len(bars) - n_hold
        full_pos = _positions(rule, bars)
        hold_bars = bars[cut:]
        hold_pos = full_pos[cut:]
        results.append(evaluate_on_bars(rule, hold_bars, asset=asset, size_usd=size_usd,
                                        initial_capital=initial_capital,
                                        positions=hold_pos))
    n_beat = sum(1 for r in results if r.objective > 0.0)
    mean_obj = float(np.mean([r.objective for r in results])) if results else 0.0
    return {
        "objective": round(mean_obj, 4),
        "n_beat_cash": n_beat,
        "per_asset": {r.asset: {"objective": r.objective, "sortino": r.sortino,
                                "max_drawdown": r.max_drawdown,
                                "total_return": r.total_return, "n_fills": r.n_fills}
                      for r in results},
        "_results": results,
    }


LEDGER_HEADER = (
    "| thesis | claim | source | verdict | n_beat | dev_obj (ETH/CAKE/UNI/LINK/AAVE) "
    "| holdout_obj | DSR |\n"
    "|--------|-------|--------|---------|--------|------------------------------------"
    "|-------------|-----|"
)


def format_ledger_row(thesis_id: str, claim: str, source: str, ev: ThesisEval) -> str:
    """Render one Markdown trial-registry row for docs/THESIS_LEDGER.md (§4.4
    multiplicity accounting). One line, pipe-delimited, matching LEDGER_HEADER."""
    objs = "/".join(f"{r.objective:+.3f}" for r in ev.per_asset)
    hold = f"{ev.holdout['objective']:+.3f}" if ev.holdout else "—"
    dsr = f"{ev.deflated_sharpe:.3f}" if ev.deflated_sharpe is not None else "—"
    claim = claim.replace("|", "/").replace("\n", " ")
    source = source.replace("|", "/").replace("\n", " ")
    return (f"| {thesis_id} | {claim} | {source} | {ev.verdict} | "
            f"{ev.n_beat}/{ev.n_assets} | {objs} | {hold} | {dsr} |")


def _holdout_dsr(holdout: dict, n_trials: int) -> float:
    """Deflated Sharpe over the pooled holdout: deflates the survivor's Sharpe by the
    number of theses tried (multiplicity). Uses the mean per-bar Sharpe across assets."""
    results: list[AssetResult] = holdout.get("_results", [])
    if not results:
        return 0.0
    sr = float(np.mean([r.sharpe_per_bar for r in results]))
    n_obs = int(np.median([r.n_obs for r in results])) or 2
    return deflated_sharpe(sr, n_trials=n_trials, n_obs=n_obs)
