"""
LedgerState — the live PnL / drawdown accountant.

Mirrors backtest.engine fill accounting so live equity reconciles against the
sim. Fed by REAL fills (on-chain receipts in live mode), it tracks cash,
position, peak equity, drawdown, cumulative costs, daily loss, and consecutive
losses — everything the dashboard and risk_state row need.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from backtest.engine import Fill


@dataclass
class LedgerState:
    initial_capital: float
    cash: float = field(init=False)
    units: float = 0.0
    avg_entry: float = 0.0
    peak_equity: float = field(init=False)
    cumulative_fees: float = 0.0
    cumulative_gas: float = 0.0
    realized_pnl_total: float = 0.0
    consecutive_losses: int = 0
    # daily-loss tracking
    current_day: int = -1
    day_start_equity: float = field(init=False)

    def __post_init__(self) -> None:
        self.cash = self.initial_capital
        self.peak_equity = self.initial_capital
        self.day_start_equity = self.initial_capital

    def mark(self, price: float) -> float:
        """Mark-to-market equity at `price`, updating the running peak."""
        equity = self.cash + self.units * price
        if equity > self.peak_equity:
            self.peak_equity = equity
        return equity

    def drawdown_pct(self, price: float) -> float:
        equity = self.cash + self.units * price
        if self.peak_equity <= 0:
            return 0.0
        return (equity - self.peak_equity) / self.peak_equity

    def open_exposure(self, price: float) -> float:
        return self.units * price

    def roll_day(self, timestamp_ms: int, price: float) -> None:
        day = timestamp_ms // 86_400_000
        if day != self.current_day:
            self.current_day = day
            self.day_start_equity = self.cash + self.units * price

    def daily_loss_usd(self, price: float) -> float:
        equity = self.cash + self.units * price
        return max(self.day_start_equity - equity, 0.0)

    def apply(self, fill: Fill) -> float:
        """
        Apply a fill; return the realized PnL for this fill (0 on a buy).
        Buy:  cash -= size + costs; units up; weighted avg entry.
        Sell: realize (price-entry)*units_sold - costs; units down.
        """
        order = fill.order
        cost = fill.total_cost_usd
        self.cumulative_fees += fill.fee_usd
        self.cumulative_gas += fill.gas_usd
        realized = 0.0

        if order.side == "buy":
            units = order.size_usd / fill.fill_price if fill.fill_price > 0 else 0.0
            if self.units <= 0:
                self.avg_entry = fill.fill_price
            elif units > 0:
                total = self.units + units
                self.avg_entry = (self.avg_entry * self.units + fill.fill_price * units) / total
            self.units += units
            self.cash -= order.size_usd + cost
        else:
            units_sold = min(order.size_usd / fill.fill_price if fill.fill_price > 0 else 0.0, self.units)
            realized = (fill.fill_price - self.avg_entry) * units_sold - cost
            self.cash += order.size_usd - cost
            self.units = max(self.units - units_sold, 0.0)
            self.realized_pnl_total += realized
            if realized < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0

        return realized

    def cumulative_pnl(self, price: float) -> float:
        """Total P&L incl. unrealized = current equity − starting capital."""
        return (self.cash + self.units * price) - self.initial_capital
