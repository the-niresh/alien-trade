# core/tests/test_engine_stops.py
from backtest.engine import Bar, Order
from risk.engine import RiskEngine
from risk.guardrails import RiskConfig


def _bar(ts: int, price: float, high: float, low: float) -> Bar:
    return Bar(timestamp=ts, open=price, high=high, low=low, close=price, volume=0.0)


def _buy_once(history):
    # Inner strategy: buy on the first bar only, then hold (None).
    return Order(side="buy", size_usd=1000.0, symbol="ETH", timestamp=history[-1].timestamp) \
        if len(history) == 1 else None


def test_hard_atr_stop_forces_exit_on_breach():
    cfg = RiskConfig(atr_stop_mult=2.0, atr_trail_mult=0.0, atr_period=2,
                     base_position_usd=1000.0, max_position_pct=1.0, max_open_exposure_pct=1.0)
    eng = RiskEngine(_buy_once, cfg, initial_capital=10_000.0)

    h = [_bar(0, 100.0, 101.0, 99.0)]
    eng(h)                                   # opens a long at ~100
    h.append(_bar(86_400_000, 100.0, 101.0, 98.0))
    eng(h)                                    # builds ATR, no breach
    # Drop price well below entry - 2*ATR -> stop must fire a sell.
    # ATR is computed from prior bars (stable vol estimate): ATR=3, stop=100-2*3=94.
    # Bar low=70.0 is well below 94, so stop triggers immediately.
    h.append(_bar(2 * 86_400_000, 80.0, 81.0, 70.0))
    order = eng(h)

    assert order is not None
    assert order.side == "sell"
    assert eng.last_stop_exit is not None
    assert eng.last_stop_exit["kind"] == "hard"


def test_no_stop_when_flat():
    cfg = RiskConfig(atr_stop_mult=2.0, atr_period=2)
    eng = RiskEngine(lambda h: None, cfg, initial_capital=10_000.0)
    assert eng([_bar(0, 100.0, 101.0, 99.0)]) is None
    assert eng.last_stop_exit is None
