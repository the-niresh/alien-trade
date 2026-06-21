# agent/tests/test_kol_overlay.py
from backtest.engine import Bar
from agent.loop import DecisionLoop


def _bar(ts=0, price=100.0):
    return Bar(timestamp=ts, open=price, high=price * 1.01, low=price * 0.99,
               close=price, volume=1.0)


class _Bridge:
    def __init__(self, reading):
        self._reading = reading
        self.events = []
    def get_sentiment_state(self, symbol):
        return self._reading
    def emit_event(self, ev):
        self.events.append(ev)
    def audit(self, *a, **k): pass


class _Executor:
    def __init__(self):
        self.calls = []
    def execute(self, order, bar, idempotency_key=None):
        self.calls.append(order)
        from agent.executor import ExecutionReport
        from backtest.engine import Fill
        fill = Fill(order=order, fill_price=bar.close, fee_usd=0.0, gas_usd=0.0, slippage_usd=0.0)
        return ExecutionReport(status="filled", reason="ok", fill=fill, tx_hash="0xabc", order=order)


def _loop(reading, *, enforce_kol=True):
    loop = DecisionLoop.__new__(DecisionLoop)          # bypass full __init__ wiring
    loop.symbol = "ETH"
    loop.mode = "paper"
    loop.bridge = _Bridge(reading)
    loop.executor = _Executor()
    loop.base_position_usd = 100.0
    loop.kol_enabled = enforce_kol
    loop._kol_min_conf = 0.5
    return loop


def test_bullish_kol_opens_long_through_executor():
    reading = {"symbol": "ETH", "score": 0.7, "confidence": 0.9, "ts_ms": 0, "n_posts": 6}
    loop = _loop(reading)
    # Stub the bits _apply_kol_signal calls on a real loop:
    loop.ledger = type("L", (), {"open_exposure": lambda self, p: 0.0,
                                 "mark": lambda self, p: 1000.0,
                                 "daily_loss_usd": lambda self, p: 0.0,
                                 "consecutive_losses": 0})()
    handled = {}
    loop._handle_execution = lambda *a, **k: ("allow", "ok", "t1")
    loop._finalise = lambda *a, **k: handled.setdefault("done", True)
    out = loop._apply_kol_signal(_bar(), "ETH-0")
    assert loop.executor.calls and loop.executor.calls[0].side == "buy"
    assert any(ev.agent == "Scout" for ev in loop.bridge.events)


def test_disabled_overlay_is_noop():
    loop = _loop({"symbol": "ETH", "score": 0.9, "confidence": 0.9, "ts_ms": 0, "n_posts": 9},
                 enforce_kol=False)
    assert loop._apply_kol_signal(_bar(), "ETH-0") is None
