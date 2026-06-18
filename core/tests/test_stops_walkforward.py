"""
OOS guard: stops must not worsen out-of-sample max-drawdown. Anti-overfitting
rule (locked decision #7) — we assert on OOS, never select params on in-sample.
"""
import pytest
from backtest.engine import Bar, Order, run_backtest
from risk.engine import RiskEngine
from risk.guardrails import RiskConfig


def _ramp_then_crash(n: int = 120) -> list[Bar]:
    """Synthetic bars: rally for first half, then crash for second half."""
    bars: list[Bar] = []
    price = 100.0
    for i in range(n):
        price = price * (1.01 if i < n // 2 else 0.98)   # rally then sustained drawdown
        bars.append(Bar(
            timestamp=i * 86_400_000,
            open=price,
            high=price * 1.01,
            low=price * 0.99,
            close=price,
            volume=1.0
        ))
    return bars


def _always_long(history: list[Bar]) -> Order | None:
    """Simple always-long strategy: buy on first bar only."""
    if len(history) == 1:
        return Order(side="buy", size_usd=1000.0, symbol="ETH", timestamp=history[-1].timestamp)
    return None


@pytest.mark.unit
def test_stops_do_not_worsen_oos_drawdown():
    """
    Assert that enabling stops reduces max drawdown on the crash half of the bars.

    Scenario:
    - 120 bars: first 60 rally up, last 60 crash down
    - Strategy: always long from bar 0
    - No stops: takes full crash drawdown
    - With stops: ATR stops (2.0x, 3.0x) trigger during crash, closing position early
    - Expected: dd_on >= dd_off (stops-on drawdown closer to zero)
    """
    bars = _ramp_then_crash()

    # No stops: ATR multipliers set to 0.0
    no_stop = RiskEngine(
        _always_long,
        RiskConfig(
            atr_stop_mult=0.0,
            atr_trail_mult=0.0,
            max_position_pct=1.0,
            max_open_exposure_pct=1.0
        ),
        initial_capital=10_000.0
    )

    # With stops: ATR multipliers set to 2.0 and 3.0
    with_stop = RiskEngine(
        _always_long,
        RiskConfig(
            atr_stop_mult=2.0,
            atr_trail_mult=3.0,
            max_position_pct=1.0,
            max_open_exposure_pct=1.0
        ),
        initial_capital=10_000.0
    )

    # Run backtests
    dd_off = run_backtest(bars, no_stop).metrics.get("max_drawdown", 0.0)
    dd_on = run_backtest(bars, with_stop).metrics.get("max_drawdown", 0.0)

    # max_drawdown is negative; "not worse" means on >= off (closer to zero).
    # Stops should cut the crash drawdown, so dd_on >= dd_off
    assert dd_on >= dd_off, (
        f"stops worsened drawdown: dd_off={dd_off:.6f} vs dd_on={dd_on:.6f}. "
        "Stops should reduce or preserve drawdown."
    )
