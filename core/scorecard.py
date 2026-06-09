"""
The agent's goal, made measurable — the single scorecard that says how well the
agent met its objective. Sim and live share this module (locked decision #2): the
backtest scores a BacktestResult, the live runtime scores the same shapes built
from real fills, so "how we're judged in sim" and "how we're judged live" can
never drift.

The objective is NOT raw profit. It is the Track-1 judging objective (CLAUDE.md
decision #6, mirrored in core/strategy/optimizer.py):

    objective  =  sortino  -  LAMBDA * |max_drawdown|        (LAMBDA = 2.0)

Everything else on the card is either an INPUT to that objective, a SCORECARD
line the judges read, or a RULE-ADHERENCE fact (the agent respected its hard
constraints). The doc that defines all of this is docs/GOAL.md.

This module only COMPUTES the market-performance lines from an equity curve +
trades + fills. The operational lines (uptime, unattended cycles, recoveries)
and the rule-adherence lines (violations, halts fired) are facts the runtime
KNOWS, not things a curve can reveal — they are passed through unchanged so the
one card carries the whole goal in one place.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

# Objective weighting — drawdown penalty. Kept in lockstep with
# core/strategy/optimizer.py (_LAMBDA); the optimizer selects params on the
# train objective, this scores the realised one. Same lambda, same goal.
LAMBDA = 2.0

_MS_PER_DAY = 86_400_000
_EPS = 1e-9


@dataclass
class OperationalStats:
    """Autonomy facts the RUNTIME knows — it is an *autonomous* agent, so staying
    alive unattended is part of the goal, not incidental. All zero/None in sim."""
    cycles_total: int = 0
    cycles_unattended: int = 0          # ran with no manual intervention
    uptime_pct: Optional[float] = None  # fraction of the live window the loop was alive
    n_recoveries: int = 0               # crash-recovery resumes (recovery.py)

    def as_dict(self) -> dict:
        return {
            "cycles_total": self.cycles_total,
            "cycles_unattended": self.cycles_unattended,
            "uptime_pct": self.uptime_pct,
            "n_recoveries": self.n_recoveries,
        }


@dataclass
class RuleAdherence:
    """Rule adherence as a binary fact + counts, against the hard guardrails in
    core/risk/guardrails.py. The agent already ENFORCES these; this RECORDS that
    it did. `violations` must be 0 — a breach that reached execution is a failure;
    a guardrail that correctly BLOCKED a trade is a `blocks_fired`, not a violation."""
    violations: int = 0                 # hard limits breached at execution (target: 0)
    blocks_fired: int = 0               # trades correctly blocked by a guardrail
    kill_switch_activations: int = 0    # daily-loss / manual kill fired (and honoured)
    circuit_breaker_activations: int = 0
    max_open_exposure_pct: float = 0.0  # peak cumulative exposure actually reached

    @property
    def clean(self) -> bool:
        return self.violations == 0

    def as_dict(self) -> dict:
        return {
            "violations": self.violations,
            "blocks_fired": self.blocks_fired,
            "kill_switch_activations": self.kill_switch_activations,
            "circuit_breaker_activations": self.circuit_breaker_activations,
            "max_open_exposure_pct": round(self.max_open_exposure_pct, 4),
            "clean": self.clean,
        }


@dataclass
class Scorecard:
    """The whole goal on one card. Group order matches docs/GOAL.md."""
    # ── Objective (the one number we optimise) ──────────────────────────────
    objective: float
    # ── Returns ──────────────────────────────────────────────────────────────
    total_return: float
    net_pnl_usd: float
    # ── Drawdown (depth AND duration) ─────────────────────────────────────────
    max_drawdown: float
    max_drawdown_duration_days: Optional[float]
    # ── Risk-adjusted ──────────────────────────────────────────────────────────
    sortino: float
    sharpe: float
    calmar: float
    # ── Consistency ──────────────────────────────────────────────────────────
    pct_positive_days: Optional[float]
    daily_pnl_vol: Optional[float]
    # ── Trade quality ──────────────────────────────────────────────────────────
    n_trades: int
    win_rate: float
    profit_factor: float
    expectancy_usd: float
    avg_win_usd: float
    avg_loss_usd: float
    worst_trade_usd: float
    # ── Cost efficiency (proves the edge survives BSC costs) ─────────────────
    total_cost_usd: float
    cost_ratio: float                       # costs / gross trading PnL
    # ── Exposure efficiency ─────────────────────────────────────────────────
    turnover: float
    avg_exposure_pct: Optional[float]
    peak_exposure_pct: Optional[float]
    # ── Autonomy + rule adherence (passthrough facts) ─────────────────────────
    operational: dict = field(default_factory=dict)
    rule_adherence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "objective": self.objective,
            "total_return": self.total_return,
            "net_pnl_usd": self.net_pnl_usd,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_duration_days": self.max_drawdown_duration_days,
            "sortino": self.sortino,
            "sharpe": self.sharpe,
            "calmar": self.calmar,
            "pct_positive_days": self.pct_positive_days,
            "daily_pnl_vol": self.daily_pnl_vol,
            "n_trades": self.n_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "expectancy_usd": self.expectancy_usd,
            "avg_win_usd": self.avg_win_usd,
            "avg_loss_usd": self.avg_loss_usd,
            "worst_trade_usd": self.worst_trade_usd,
            "total_cost_usd": self.total_cost_usd,
            "cost_ratio": self.cost_ratio,
            "turnover": self.turnover,
            "avg_exposure_pct": self.avg_exposure_pct,
            "peak_exposure_pct": self.peak_exposure_pct,
            "operational": dict(self.operational),
            "rule_adherence": dict(self.rule_adherence),
        }

    def as_convex_row(self) -> dict:
        """Flat shape for the Convex `scorecard` singleton (keys match schema.ts).
        Nested operational/adherence are JSON-serialised, like `audit.payload`."""
        import json
        return {
            "objective": self.objective,
            "total_return": self.total_return,
            "net_pnl_usd": self.net_pnl_usd,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_duration_days": self.max_drawdown_duration_days,
            "sortino": self.sortino,
            "sharpe": self.sharpe,
            "calmar": self.calmar,
            "pct_positive_days": self.pct_positive_days,
            "daily_pnl_vol": self.daily_pnl_vol,
            "n_trades": self.n_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "expectancy_usd": self.expectancy_usd,
            "worst_trade_usd": self.worst_trade_usd,
            "total_cost_usd": self.total_cost_usd,
            "cost_ratio": self.cost_ratio,
            "turnover": self.turnover,
            "avg_exposure_pct": self.avg_exposure_pct,
            "peak_exposure_pct": self.peak_exposure_pct,
            "rule_adherence_clean": bool(self.rule_adherence.get("clean", True)),
            "rule_violations": int(self.rule_adherence.get("violations", 0)),
            "operational": json.dumps(self.operational, default=str),
            "rule_adherence": json.dumps(self.rule_adherence, default=str),
        }


# ── Helpers ─────────────────────────────────────────────────────────────────


def _max_drawdown_duration_days(
    arr: np.ndarray, timestamps: Optional[Sequence[int]]
) -> Optional[float]:
    """Longest time the equity spent below a prior peak before recovering it.
    Depth (max_drawdown) says how bad; duration says how long underwater — both
    are scored over a short live window. Returns days if timestamps are given,
    else None (step counts are not comparable across runs)."""
    if timestamps is None or len(timestamps) != len(arr) or len(arr) < 2:
        return None
    ts = np.asarray(timestamps, dtype=float)
    peak = arr[0]
    peak_ts = ts[0]
    longest_ms = 0.0
    for i in range(1, len(arr)):
        if arr[i] >= peak:                      # recovered to (or above) prior peak
            longest_ms = max(longest_ms, ts[i] - peak_ts)
            peak = arr[i]
            peak_ts = ts[i]
    # Still underwater at the end — count the open episode too.
    if arr[-1] < peak:
        longest_ms = max(longest_ms, ts[-1] - peak_ts)
    return round(longest_ms / _MS_PER_DAY, 4)


def _daily_consistency(
    arr: np.ndarray, timestamps: Optional[Sequence[int]]
) -> tuple[Optional[float], Optional[float]]:
    """(% positive days, daily-PnL volatility) from end-of-day equity. Needs
    timestamps to bucket into days; without them steadiness isn't well-defined."""
    if timestamps is None or len(timestamps) != len(arr) or len(arr) < 2:
        return None, None
    days = (np.asarray(timestamps, dtype=np.int64) // _MS_PER_DAY)
    # last equity of each day, in day order
    eod: dict[int, float] = {}
    for d, eq in zip(days.tolist(), arr.tolist()):
        eod[d] = eq  # later entries overwrite → end-of-day value
    ordered = [eod[d] for d in sorted(eod)]
    if len(ordered) < 2:
        return None, None
    daily = np.diff(np.asarray(ordered, dtype=float))
    pct_positive = float((daily > 0).mean())
    daily_ret = daily / np.asarray(ordered[:-1], dtype=float)
    vol = float(daily_ret.std())
    return round(pct_positive, 4), round(vol, 6)


def _trade_quality(trades) -> dict:
    pnls = [float(t.pnl_usd) for t in trades]
    n = len(pnls)
    if n == 0:
        return {
            "n_trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
            "expectancy_usd": 0.0, "avg_win_usd": 0.0, "avg_loss_usd": 0.0,
            "worst_trade_usd": 0.0,
        }
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_win / gross_loss) if gross_loss > _EPS else (
        float("inf") if gross_win > 0 else 0.0
    )
    return {
        "n_trades": n,
        "win_rate": round(len(wins) / n, 4),
        # cap inf at construction so it serialises to Convex; report large but finite
        "profit_factor": round(profit_factor, 4) if math.isfinite(profit_factor) else 999.0,
        "expectancy_usd": round(sum(pnls) / n, 2),
        "avg_win_usd": round(gross_win / len(wins), 2) if wins else 0.0,
        "avg_loss_usd": round(sum(losses) / len(losses), 2) if losses else 0.0,
        "worst_trade_usd": round(min(pnls), 2),
    }


def _cost_lines(trades, fills) -> tuple[float, float]:
    """(total_cost_usd, cost_ratio). cost_ratio = total costs / gross trading PnL,
    where gross = realised net PnL with both legs' costs added back. A ratio near
    1.0 means costs ate the whole edge; this is the line that proves the alpha
    survives real BSC gas + slippage + fees (the BNB/PancakeSwap real-fill story)."""
    total_cost = round(sum(float(f.total_cost_usd) for f in fills), 2)
    gross = 0.0
    for t in trades:
        leg_costs = float(t.entry.total_cost_usd) + float(t.exit.total_cost_usd)
        gross += abs(float(t.pnl_usd) + leg_costs)
    cost_ratio = round(total_cost / gross, 4) if gross > _EPS else 0.0
    return total_cost, cost_ratio


# ── Public API ────────────────────────────────────────────────────────────────


def compute_scorecard(
    equity_curve: Sequence[float],
    trades,
    fills,
    initial_capital: float,
    timestamps: Optional[Sequence[int]] = None,
    exposure_curve: Optional[Sequence[float]] = None,
    operational: Optional[OperationalStats] = None,
    rule_adherence: Optional[RuleAdherence] = None,
) -> Scorecard:
    """Score an equity curve + trades + fills against the agent's goal.

    Works identically for a BacktestResult (pass result.equity_curve / .trades /
    .fills) and for a live window (build the same shapes from real fills) — that
    is the whole point of one shared module.

    timestamps   : unix-ms aligned 1:1 with equity_curve. Required for the
                   duration / daily-consistency lines (otherwise they are None).
    exposure_curve: open position USD aligned with equity_curve. Required for the
                   exposure-efficiency lines (otherwise None). The live runtime
                   tracks this; the basic backtest does not.
    operational / rule_adherence: facts the runtime supplies; default to empty.
    """
    arr = np.asarray(list(equity_curve), dtype=float)
    if len(arr) < 2:
        # Degenerate (no trading window yet) — return a zeroed card, not a crash.
        return Scorecard(
            objective=0.0, total_return=0.0, net_pnl_usd=0.0,
            max_drawdown=0.0, max_drawdown_duration_days=None,
            sortino=0.0, sharpe=0.0, calmar=0.0,
            pct_positive_days=None, daily_pnl_vol=None,
            **{**_trade_quality(trades)},
            **dict(zip(("total_cost_usd", "cost_ratio"), _cost_lines(trades, fills))),
            turnover=0.0, avg_exposure_pct=None, peak_exposure_pct=None,
            operational=(operational or OperationalStats()).as_dict(),
            rule_adherence=(rule_adherence or RuleAdherence()).as_dict(),
        )

    returns = np.diff(arr) / arr[:-1]
    total_return = float((arr[-1] - initial_capital) / initial_capital)
    net_pnl = float(arr[-1] - initial_capital)
    mean_ret = float(returns.mean())
    std_ret = float(returns.std())
    sharpe = (mean_ret / std_ret * math.sqrt(252)) if std_ret > 0 else 0.0
    downside = returns[returns < 0]
    sortino = (
        mean_ret / downside.std() * math.sqrt(252)
        if len(downside) > 0 and downside.std() > 0 else 0.0
    )
    rolling_max = np.maximum.accumulate(arr)
    drawdowns = (arr - rolling_max) / rolling_max
    max_dd = float(drawdowns.min())
    calmar = (total_return / abs(max_dd)) if max_dd != 0 else 0.0
    objective = round(sortino - LAMBDA * abs(max_dd), 4)

    dd_duration = _max_drawdown_duration_days(arr, timestamps)
    pct_pos, daily_vol = _daily_consistency(arr, timestamps)
    tq = _trade_quality(trades)
    total_cost, cost_ratio = _cost_lines(trades, fills)

    avg_equity = float(arr.mean())
    total_volume = sum(float(f.order.size_usd) for f in fills)
    turnover = round(total_volume / avg_equity, 4) if avg_equity > 0 else 0.0

    avg_exp = peak_exp = None
    if exposure_curve is not None and len(exposure_curve) == len(arr):
        exp = np.asarray(list(exposure_curve), dtype=float)
        eq_safe = np.where(arr > _EPS, arr, np.nan)
        exp_pct = exp / eq_safe
        avg_exp = round(float(np.nanmean(exp_pct)), 4)
        peak_exp = round(float(np.nanmax(exp_pct)), 4)

    return Scorecard(
        objective=objective,
        total_return=round(total_return, 6),
        net_pnl_usd=round(net_pnl, 2),
        max_drawdown=round(max_dd, 6),
        max_drawdown_duration_days=dd_duration,
        sortino=round(float(sortino), 4),
        sharpe=round(float(sharpe), 4),
        calmar=round(float(calmar), 4),
        pct_positive_days=pct_pos,
        daily_pnl_vol=daily_vol,
        n_trades=tq["n_trades"],
        win_rate=tq["win_rate"],
        profit_factor=tq["profit_factor"],
        expectancy_usd=tq["expectancy_usd"],
        avg_win_usd=tq["avg_win_usd"],
        avg_loss_usd=tq["avg_loss_usd"],
        worst_trade_usd=tq["worst_trade_usd"],
        total_cost_usd=total_cost,
        cost_ratio=cost_ratio,
        turnover=turnover,
        avg_exposure_pct=avg_exp,
        peak_exposure_pct=peak_exp,
        operational=(operational or OperationalStats()).as_dict(),
        rule_adherence=(rule_adherence or RuleAdherence()).as_dict(),
    )


def scorecard_from_result(result, initial_capital: float, **kwargs) -> Scorecard:
    """Convenience: score a BacktestResult directly. `kwargs` forwards the optional
    timestamps / exposure_curve / operational / rule_adherence."""
    return compute_scorecard(
        result.equity_curve, result.trades, result.fills, initial_capital, **kwargs
    )
