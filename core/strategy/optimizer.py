"""
Walk-forward parameter optimizer for the combined strategy.
Objective: Sortino_train  −  λ * abs(max_drawdown_train)
Select for a robust plateau, not a fragile peak.

Grid is intentionally small (< 20 combos) — Step 3 principle: fewer knobs.
"""
from __future__ import annotations

from dataclasses import asdict
from itertools import product

from backtest.engine import Bar, run_backtest
from backtest.costs import BSCCostModel
from strategy.combined import StrategyParams, make_strategy

# ── Parameter grid ────────────────────────────────────────────────────────────

PARAM_GRID: dict[str, list] = {
    "ema_fast":         [5, 8, 13],
    "ema_slow":         [21, 34],
    "entry_threshold":  [0.20, 0.30, 0.40],
}

# Objective weighting: λ penalises drawdown
_LAMBDA = 2.0
_DEFAULT_COST = BSCCostModel()


# ── Public API ────────────────────────────────────────────────────────────────

def optimize(
    train_bars: list[Bar],
    cost_model=_DEFAULT_COST,
    initial_capital: float = 10_000.0,
    stability_bonus: bool = True,
) -> dict:
    """
    Grid-search over PARAM_GRID on `train_bars`.
    Returns the best param dict. Falls back to defaults if all combos fail.

    stability_bonus=True adds a small bonus for params whose objective is
    within 20% of the best across multiple nearby combinations —
    selects the robust plateau, not a fragile spike.
    """
    results: list[tuple[dict, float]] = []

    for fast, slow, entry in product(
        PARAM_GRID["ema_fast"],
        PARAM_GRID["ema_slow"],
        PARAM_GRID["entry_threshold"],
    ):
        if fast >= slow:
            continue   # invalid pair

        params = StrategyParams(ema_fast=fast, ema_slow=slow, entry_threshold=entry)
        strategy = make_strategy(params)
        result = run_backtest(
            train_bars, strategy,
            initial_capital=initial_capital,
            cost_model=cost_model,
        )
        m = result.metrics
        sortino = m.get("sortino", 0.0)
        max_dd = abs(m.get("max_drawdown", 0.0))
        obj = sortino - _LAMBDA * max_dd
        results.append((asdict(params), obj))

    if not results:
        return asdict(StrategyParams())

    best_obj = max(obj for _, obj in results)

    if stability_bonus:
        # Count how many combos are within 20% of best — more neighbours = more robust
        threshold = best_obj * 0.8 if best_obj > 0 else best_obj * 1.2
        stability_counts = {
            i: sum(1 for _, obj in results if obj >= threshold)
            for i in range(len(results))
        }
        # Re-rank: objective + tiny stability bonus (0.01 per neighbour)
        ranked = sorted(
            range(len(results)),
            key=lambda i: results[i][1] + 0.01 * stability_counts[i],
            reverse=True,
        )
        best_params = results[ranked[0]][0]
    else:
        best_params = max(results, key=lambda x: x[1])[0]

    # Return only the optimised keys (don't override weights/sizing)
    return {
        "ema_fast":        best_params["ema_fast"],
        "ema_slow":        best_params["ema_slow"],
        "entry_threshold": best_params["entry_threshold"],
    }


def make_strategy_from_dict(params: dict) -> "StrategyFn":
    """
    Build a StrategyFn from an optimizer output dict.
    Unknown keys are ignored; missing keys fall back to StrategyParams defaults.
    """
    from backtest.engine import StrategyFn  # noqa: F401 — re-exported for callers
    known = {f.name for f in StrategyParams.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    filtered = {k: v for k, v in params.items() if k in known}
    return make_strategy(StrategyParams(**filtered))


# ── Convenience: plug-in functions for run_walk_forward ──────────────────────

def walk_forward_optimize_fn(train_bars: list[Bar]) -> dict:
    """Drop-in optimize_fn for run_walk_forward."""
    return optimize(train_bars)


def walk_forward_strategy_factory(params: dict):
    """Drop-in strategy_factory for run_walk_forward."""
    return make_strategy_from_dict(params)
