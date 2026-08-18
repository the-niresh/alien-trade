"""Human-feedback gate wired into the loop - bad marks block, parity offline."""
from __future__ import annotations

from backtest.costs import BSCCostModel
from backtest.engine import Bar, Order
from strategy.combined import StrategyParams

from agent.convex_bridge import ConvexBridge
from agent.executor import PaperExecutor
from agent.feed import ReplayFeed
from agent.loop import DecisionLoop


class _FBBridge(ConvexBridge):
    """Offline bridge returning a fixed set of human feedback records."""
    def __init__(self, records):
        super().__init__(url="")
        self._records = records
        self.audits = []

    def is_halted(self):
        return False

    def get_equity_floor(self):
        return 0.0

    def get_feedback(self, setup_key):
        return self._records

    def audit(self, event_type, cycle_id, payload, severity="info"):
        self.audits.append((event_type, payload))


def _buy_strategy(h):
    bar = h[-1]
    return Order(side="buy", size_usd=50.0, symbol="ETH", timestamp=bar.timestamp)


def _bar(ts, price):
    return Bar(timestamp=ts, open=price, high=price, low=price, close=price, volume=1.0)


def _loop(bridge):
    return DecisionLoop(
        feed=ReplayFeed([]), strategy=_buy_strategy,
        executor=PaperExecutor(cost_model=BSCCostModel()), bridge=bridge,
        params=StrategyParams(symbol="ETH"), symbol="ETH", mode="paper",
        initial_capital=1000.0,
    )


def test_bad_feedback_blocks_buy():
    bridge = _FBBridge([{"label": "bad"}, {"label": "bad"}])   # net 2 → block
    loop = _loop(bridge)
    res = loop.run_cycle([_bar(0, 100.0)])
    assert res.verdict == "block"
    assert "human feedback" in res.reason
    assert loop.ledger.open_exposure(100.0) < 1e-3            # nothing bought
    assert any(p.get("source") == "human" for k, p in bridge.audits if k == "risk_veto")


def test_net_bad_shrinks_buy():
    bridge = _FBBridge([{"label": "bad"}])                     # net 1 → halve
    loop = _loop(bridge)
    res = loop.run_cycle([_bar(0, 100.0)])
    # The buy still executes but at a reduced size (penalty applied).
    assert loop.ledger.open_exposure(100.0) > 0.0
    assert any(p.get("size_penalty") for k, p in bridge.audits if k == "risk_veto")


def test_no_feedback_is_parity_noop():
    bridge = _FBBridge([])                                     # offline / no marks
    loop = _loop(bridge)
    res = loop.run_cycle([_bar(0, 100.0)])
    assert loop.ledger.open_exposure(100.0) > 0.0             # buy went through
    assert loop._current_setup_key != ""                      # key still computed
