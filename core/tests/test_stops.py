# core/tests/test_stops.py
from backtest.engine import Bar
from risk.stops import compute_atr, hard_stop_level, trailing_stop_level, stop_triggered


def _bar(h: float, l: float, c: float) -> Bar:
    return Bar(timestamp=0, open=c, high=h, low=l, close=c, volume=0.0)


def test_compute_atr_true_range_average():
    bars = [_bar(10, 9, 9.5), _bar(11, 9.5, 10.5), _bar(12, 10, 11.5)]
    atr = compute_atr(bars, period=2)
    assert atr > 0.0
    assert round(atr, 4) == 1.75   # TR of last two bars: (11-9.5)=1.5, (12-10)=2.0 -> mean 1.75


def test_compute_atr_too_short_is_zero():
    assert compute_atr([_bar(10, 9, 9.5)], period=14) == 0.0


def test_hard_stop_level_below_entry():
    assert hard_stop_level(avg_entry=100.0, atr=5.0, mult=2.0) == 90.0


def test_trailing_stop_tracks_high_water():
    assert trailing_stop_level(high_water=120.0, atr=5.0, mult=2.0) == 110.0


def test_stop_triggered_only_when_breached():
    assert stop_triggered(price=89.0, stop=90.0) is True
    assert stop_triggered(price=91.0, stop=90.0) is False
    assert stop_triggered(price=50.0, stop=0.0) is False   # disabled stop never fires
