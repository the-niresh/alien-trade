"""
Activity floor — Track 1 requires >= 1 trade per calendar day. When enabled, the
loop forces ONE minimal compliance swap late in the day if nothing has traded yet.
These tests pin: off by default, fires only past the deadline hour with zero trades,
skips when a real trade already happened, trims when holding (never breaches caps),
and resets per calendar day.
"""
from __future__ import annotations

from backtest.costs import BSCCostModel
from strategy.combined import StrategyParams

from backtest.engine import Bar
from agent.convex_bridge import ConvexBridge
from agent.executor import PaperExecutor
from agent.feed import ReplayFeed
from agent.loop import DecisionLoop


def _bar(ts: int, price: float = 100.0) -> Bar:
    return Bar(timestamp=ts, open=price, high=price * 1.01,
               low=price * 0.99, close=price, volume=1_000.0)


def _ms(day: int, hour: int) -> int:
    return day * 86_400_000 + hour * 3_600_000


def _loop(*, enforce: bool, strategy=None):
    return DecisionLoop(
        feed=ReplayFeed([]), strategy=strategy or (lambda h: None),
        executor=PaperExecutor(cost_model=BSCCostModel()), bridge=ConvexBridge(url=""),
        params=StrategyParams(), symbol="ETH", mode="paper", initial_capital=10_000.0,
        enforce_activity_floor=enforce, activity_deadline_hour=23, activity_trade_usd=15.0,
    )


def test_off_by_default_no_forced_trade():
    loop = _loop(enforce=False)
    loop.run_cycle([_bar(_ms(1, 23))])   # late in the day, but floor disabled
    assert loop._trades_today == 0
    assert len(loop._fills) == 0


def test_no_trade_before_deadline_hour():
    loop = _loop(enforce=True)
    loop.run_cycle([_bar(_ms(1, 10))])   # mid-day — give the strategy room
    assert loop._trades_today == 0


def test_forces_buy_when_flat_past_deadline():
    loop = _loop(enforce=True)
    loop.run_cycle([_bar(_ms(1, 23))])   # end of day, flat, nothing traded yet
    assert loop._trades_today == 1
    assert len(loop._fills) == 1
    assert loop._fills[0].order.side == "buy"
    assert loop._fills[0].order.size_usd == 15.0


def test_skips_when_a_real_trade_already_happened():
    # Strategy that buys on the first cycle → a real trade exists for the day.
    from backtest.engine import Order
    fired = [False]

    def buy_once(h):
        if not fired[0]:
            fired[0] = True
            return Order(side="buy", size_usd=1_000.0, symbol="ETH", timestamp=h[-1].timestamp)
        return None

    loop = _loop(enforce=True, strategy=buy_once)
    loop.run_cycle([_bar(_ms(1, 23))])
    # Exactly the strategy's trade — no extra compliance swap piled on top.
    assert loop._trades_today == 1
    assert len(loop._fills) == 1
    assert loop._fills[0].order.size_usd == 1_000.0


def test_trims_when_holding_a_position():
    loop = _loop(enforce=True)
    loop.ledger.units = 5.0   # holding $500 at price 100 → trim, don't add
    loop.run_cycle([_bar(_ms(1, 23), price=100.0)])
    assert loop._trades_today == 1
    assert loop._fills[0].order.side == "sell"
    assert loop._fills[0].order.size_usd == 15.0


def test_counter_resets_each_calendar_day():
    loop = _loop(enforce=True)
    loop.run_cycle([_bar(_ms(1, 23))])   # day 1 forces a trade
    assert loop._trades_today == 1
    loop.run_cycle([_bar(_ms(2, 5))])    # day 2, early — counter reset, no forced trade yet
    assert loop._activity_day == 2
    assert loop._trades_today == 0
    loop.run_cycle([_bar(_ms(2, 23))])   # day 2, end — forces again
    assert loop._trades_today == 1


def test_halted_day_does_not_force_trade():
    class _HaltedBridge(ConvexBridge):
        def __init__(self):
            super().__init__(url="")
        def is_halted(self):
            return True

    loop = DecisionLoop(
        feed=ReplayFeed([]), strategy=lambda h: None,
        executor=PaperExecutor(cost_model=BSCCostModel()), bridge=_HaltedBridge(),
        params=StrategyParams(), symbol="ETH", mode="paper", initial_capital=10_000.0,
        enforce_activity_floor=True, activity_deadline_hour=23,
    )
    loop.run_cycle([_bar(_ms(1, 23))])   # halted returns before the activity floor
    assert loop._trades_today == 0
    assert len(loop._fills) == 0
