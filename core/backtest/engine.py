"""
Event-driven backtest engine.
Sim and live share this module — no duplicate logic anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterator
import numpy as np


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
class BacktestResult:
    fills: list[Fill] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


StrategyFn = Callable[[list[Bar]], Order | None]
CostModelFn = Callable[[Order, Bar], tuple[float, float, float]]  # fee, gas, slippage


def _default_cost_model(order: Order, bar: Bar) -> tuple[float, float, float]:
    """Placeholder cost model — Phase 2 replaces with real BSC gas + AMM slippage."""
    fee = order.size_usd * 0.0025        # 0.25% PancakeSwap fee
    gas = 0.30                            # ~$0.30 BSC gas flat placeholder
    slippage = order.size_usd * 0.0010   # 0.10% slippage placeholder
    return fee, gas, slippage


def run_backtest(
    bars: list[Bar],
    strategy: StrategyFn,
    initial_capital: float = 10_000.0,
    cost_model: CostModelFn = _default_cost_model,
) -> BacktestResult:
    """
    Event-driven loop: iterate bars strictly in time order.
    Strategy sees only bars up to and including the current one (no look-ahead).
    """
    result = BacktestResult()
    cash = initial_capital
    position_units = 0.0  # asset quantity; marked to market each bar

    for i, bar in enumerate(bars):
        history = bars[: i + 1]          # point-in-time: only past + current bar
        order = strategy(history)

        if order is not None:
            fee, gas, slippage = cost_model(order, bar)
            slippage_pct = slippage / order.size_usd
            fill_price = bar.close * (1 + slippage_pct if order.side == "buy" else 1 - slippage_pct)
            fill = Fill(
                order=order,
                fill_price=fill_price,
                fee_usd=fee,
                gas_usd=gas,
                slippage_usd=slippage,
            )
            result.fills.append(fill)
            units = order.size_usd / fill_price
            cost = fill.total_cost_usd
            if order.side == "buy":
                cash -= order.size_usd + cost
                position_units += units
            else:
                cash += order.size_usd - cost
                position_units -= units

        equity = cash + position_units * bar.close  # mark to market
        result.equity_curve.append(equity)

    result.metrics = _compute_metrics(result.equity_curve, initial_capital)
    return result


def _compute_metrics(curve: list[float], initial: float) -> dict:
    if len(curve) < 2:
        return {}
    arr = np.array(curve, dtype=float)
    returns = np.diff(arr) / arr[:-1]
    total_return = (arr[-1] - initial) / initial
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0.0
    downside = returns[returns < 0]
    sortino = (returns.mean() / downside.std()) * np.sqrt(252) if len(downside) > 0 and downside.std() > 0 else 0.0
    rolling_max = np.maximum.accumulate(arr)
    drawdowns = (arr - rolling_max) / rolling_max
    max_drawdown = drawdowns.min()
    calmar = (total_return / abs(max_drawdown)) if max_drawdown != 0 else 0.0
    return {
        "total_return": round(total_return, 6),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "max_drawdown": round(max_drawdown, 6),
        "calmar": round(calmar, 4),
        "n_fills": 0,  # populated by caller if needed
    }
