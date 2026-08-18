"""
Event-driven backtest engine.
Sim and live share this module - no duplicate logic anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, Optional
import numpy as np


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Bar:
    timestamp: int        # unix ms
    open: float
    high: float
    low: float
    close: float
    volume: float
    # Extended fields populated from CMC (Phase 1)
    funding_rate: float = 0.0
    open_interest: float = 0.0
    social_score: float = 0.0
    net_flow: float = 0.0   # on-chain exchange net flow


@dataclass
class Order:
    side: str             # "buy" | "sell"
    size_usd: float
    symbol: str
    timestamp: int


@dataclass
class Fill:
    order: Order
    fill_price: float
    fee_usd: float
    gas_usd: float
    slippage_usd: float

    @property
    def total_cost_usd(self) -> float:
        return self.fee_usd + self.gas_usd + self.slippage_usd


@dataclass
class Trade:
    """Closed round-trip: one entry fill + one exit fill."""
    entry: Fill
    exit: Fill
    pnl_usd: float   # realised P&L net of both legs' costs


@dataclass
class BacktestResult:
    fills: list[Fill] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    # Accounting-integrity counters.
    #
    # Both of these record a strategy asking for something physically impossible. The
    # engine refuses it, sizes the fill to what is actually available, and counts it
    # here. A run with either counter above zero has a strategy whose idea of the
    # account has drifted from the engine's, and its numbers should be treated as
    # suspect until that is resolved.
    #
    # They exist because both failures used to pass silently, and both flattered the
    # result: an oversized sell created cash, an underfunded buy bought on margin the
    # account never had.
    oversized_sells: int = 0
    oversized_sell_usd: float = 0.0
    underfunded_buys: int = 0
    underfunded_buy_usd: float = 0.0


# ── Callable types ────────────────────────────────────────────────────────────

StrategyFn = Callable[[list[Bar]], Order | None]
CostModelFn = Callable[[Order, Bar], tuple[float, float, float]]  # fee, gas, slippage


# ── Default cost model (placeholder - replaced by BSCCostModel in production) ─

def _default_cost_model(order: Order, bar: Bar) -> tuple[float, float, float]:
    fee = order.size_usd * 0.0025        # 0.25% PancakeSwap fee
    gas = 0.43                            # ~$0.43 BSC gas at 5 gwei / 150k units / $572 BNB
    slippage = order.size_usd * 0.0010   # 0.10% slippage placeholder
    return fee, gas, slippage


# ── Engine ────────────────────────────────────────────────────────────────────

def run_backtest(
    bars: list[Bar],
    strategy: StrategyFn,
    initial_capital: float = 10_000.0,
    cost_model: CostModelFn = _default_cost_model,
    next_bar_open_fill: bool = False,
    periods_per_year: float = 252.0,
) -> BacktestResult:
    """
    Event-driven loop: iterate bars strictly in time order.
    Strategy sees only bars[0..i] - no look-ahead.

    next_bar_open_fill=True  → order generated at bar i fills at bar i+1's open
                                (realistic 1-bar execution latency).
    next_bar_open_fill=False → fills at current bar's close
                                (backward-compatible; still no look-ahead bias).
    """
    result = BacktestResult()
    cash = initial_capital
    position_units = 0.0
    entry_fill: Optional[Fill] = None
    total_volume = 0.0
    pending_order: Optional[Order] = None

    for i, bar in enumerate(bars):
        # ── Execute pending order (1-bar delayed fill at next open) ──────────
        if next_bar_open_fill and pending_order is not None:
            cash, position_units, entry_fill, executed_usd = _apply_fill(
                pending_order, bar.open, bar, cash, position_units,
                entry_fill, cost_model, result,
            )
            total_volume += executed_usd
            pending_order = None

        # ── Strategy signal (point-in-time: only bars[0..i]) ─────────────────
        history = bars[: i + 1]
        order = strategy(history)

        if order is not None:
            if next_bar_open_fill:
                pending_order = order
            else:
                # Fill at current bar's close with slippage priced in
                fee, gas, slippage = cost_model(order, bar)
                slippage_pct = slippage / order.size_usd if order.size_usd > 0 else 0.0
                fill_price = bar.close * (1 + slippage_pct if order.side == "buy" else 1 - slippage_pct)
                cash, position_units, entry_fill, executed_usd = _apply_fill(
                    order, fill_price, bar, cash, position_units,
                    entry_fill, cost_model, result,
                    precomputed=(fee, gas, slippage),
                )
                total_volume += executed_usd

        equity = cash + position_units * bar.close
        result.equity_curve.append(equity)

    avg_equity = float(np.mean(result.equity_curve)) if result.equity_curve else initial_capital
    result.metrics = _compute_metrics(
        result.equity_curve, initial_capital,
        result.trades, total_volume, avg_equity,
        n_fills=len(result.fills),
        periods_per_year=periods_per_year,
    )
    result.metrics["oversized_sells"] = result.oversized_sells
    result.metrics["oversized_sell_usd"] = result.oversized_sell_usd
    result.metrics["underfunded_buys"] = result.underfunded_buys
    result.metrics["underfunded_buy_usd"] = result.underfunded_buy_usd
    return result


def _buy_cost_floor(
    order: Order,
    bar: Bar,
    cost_model: CostModelFn,
    precomputed: Optional[tuple[float, float, float]],
) -> float:
    """
    Cash that must be left over to pay a buy's costs.

    Fees and slippage scale with size, so they shrink along with a clamped order; gas is
    a flat charge that has to be affordable whatever the size. Reserving gas is what
    stops a clamp from producing a fill the account cannot actually settle.
    """
    _, gas, _ = precomputed if precomputed is not None else cost_model(order, bar)
    return gas


def _apply_fill(
    order: Order,
    fill_price: float,
    bar: Bar,
    cash: float,
    position_units: float,
    entry_fill: Optional[Fill],
    cost_model: CostModelFn,
    result: BacktestResult,
    precomputed: Optional[tuple[float, float, float]] = None,
) -> tuple[float, float, Optional[Fill], float]:
    """
    Record fill, update cash/position, close trades.
    Returns (cash, position_units, entry_fill, executed_usd).
    precomputed: (fee, gas, slippage) if already computed by caller (avoids double call).

    A sell is capped at the position actually held. Without that cap the engine would
    credit the full requested proceeds while flooring the position at zero, which
    creates cash out of nothing and inflates the equity curve - silently, and always
    in the flattering direction.
    """
    executed_usd = order.size_usd

    if order.side == "sell":
        held_usd = position_units * fill_price
        if order.size_usd > held_usd + 1e-9:
            result.oversized_sells += 1
            result.oversized_sell_usd += order.size_usd - held_usd
            executed_usd = max(held_usd, 0.0)
        if executed_usd <= 1e-9:
            # Nothing to sell. Recording a fill here would fabricate a trade and,
            # with an open entry_fill, a PnL figure for a sale that never happened.
            return cash, position_units, entry_fill, 0.0
    else:
        # Spot, long only, unlevered: a buy is bounded by settled cash. Without this
        # the account borrows silently, and a strategy that over-trades reports a loss
        # deeper than 100% - which is not a bad result, it is an impossible one.
        affordable = cash - _buy_cost_floor(order, bar, cost_model, precomputed)
        if order.size_usd > affordable + 1e-9:
            result.underfunded_buys += 1
            result.underfunded_buy_usd += order.size_usd - max(affordable, 0.0)
            executed_usd = max(affordable, 0.0)
        if executed_usd <= 1e-9:
            return cash, position_units, entry_fill, 0.0

    fee, gas, slippage = precomputed if precomputed is not None else cost_model(order, bar)
    if executed_usd != order.size_usd and order.size_usd > 0:
        # Costs were priced off the requested size; scale them to what actually traded.
        scale = executed_usd / order.size_usd
        fee, gas, slippage = fee * scale, gas, slippage * scale
        order = replace(order, size_usd=executed_usd)

    fill = Fill(order=order, fill_price=fill_price,
                fee_usd=fee, gas_usd=gas, slippage_usd=slippage)
    result.fills.append(fill)

    units = executed_usd / fill_price if fill_price > 0 else 0.0
    cost = fill.total_cost_usd

    if order.side == "buy":
        cash -= executed_usd + cost
        position_units += units
        if entry_fill is None:
            entry_fill = fill
    else:
        cash += executed_usd - cost
        position_units = max(position_units - units, 0.0)
        if entry_fill is not None:
            pnl = (fill_price - entry_fill.fill_price) * units - cost - entry_fill.total_cost_usd
            result.trades.append(Trade(entry=entry_fill, exit=fill, pnl_usd=pnl))
            entry_fill = None

    return cash, position_units, entry_fill, executed_usd


# ── Metrics ───────────────────────────────────────────────────────────────────

def _compute_metrics(
    curve: list[float],
    initial: float,
    trades: list[Trade],
    total_volume: float,
    avg_equity: float,
    n_fills: int = 0,
    periods_per_year: float = 252.0,
) -> dict:
    if len(curve) < 2:
        return {}

    arr = np.array(curve, dtype=float)
    returns = np.diff(arr) / arr[:-1]
    total_return = (arr[-1] - initial) / initial
    mean_ret = float(returns.mean())
    std_ret = float(returns.std())
    # Annualization factor must match the bar interval of `curve`. Defaults to 252
    # (daily). For hourly bars pass periods_per_year=252*24; for the equity curve from
    # 1h live bars, daily annualization understates Sharpe/Sortino ~5x.
    ann = np.sqrt(periods_per_year)
    sharpe = (mean_ret / std_ret * ann) if std_ret > 0 else 0.0
    downside = returns[returns < 0]
    sortino = (mean_ret / downside.std() * ann) if len(downside) > 0 and downside.std() > 0 else 0.0
    rolling_max = np.maximum.accumulate(arr)
    drawdowns = (arr - rolling_max) / rolling_max
    max_drawdown = float(drawdowns.min())
    calmar = (total_return / abs(max_drawdown)) if max_drawdown != 0 else 0.0

    n_trades = len(trades)
    winning = sum(1 for t in trades if t.pnl_usd > 0)
    win_rate = winning / n_trades if n_trades > 0 else 0.0
    turnover = total_volume / avg_equity if avg_equity > 0 else 0.0

    return {
        "total_return": round(total_return, 6),
        "sharpe": round(float(sharpe), 4),
        "sortino": round(float(sortino), 4),
        "max_drawdown": round(max_drawdown, 6),
        "calmar": round(float(calmar), 4),
        "win_rate": round(win_rate, 4),
        "turnover": round(turnover, 4),
        "n_fills": n_fills,
        "n_trades": n_trades,
    }
