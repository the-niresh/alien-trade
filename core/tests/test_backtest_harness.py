"""
Step 0 exit criterion: proves the backtest loop wires end-to-end.
Uses a synthetic bar series - no real data needed.
"""
import pytest
from backtest.engine import Bar, Order, run_backtest


def _make_bars(n: int = 50, start_price: float = 300.0) -> list[Bar]:
    """Synthetic uptrending bars for harness validation."""
    bars = []
    price = start_price
    for i in range(n):
        price *= 1.002  # +0.2% per bar
        bars.append(
            Bar(
                timestamp=1_700_000_000_000 + i * 3_600_000,
                open=price * 0.999,
                high=price * 1.001,
                low=price * 0.998,
                close=price,
                volume=1_000_000.0,
            )
        )
    return bars


def _buy_and_hold(history: list[Bar]) -> Order | None:
    """Buy once on bar 1, never sell. Simplest possible strategy."""
    if len(history) == 1:
        return Order(side="buy", size_usd=1000.0, symbol="BNB", timestamp=history[-1].timestamp)
    return None


def _do_nothing(history: list[Bar]) -> Order | None:
    return None


class TestBacktestHarness:
    def test_empty_strategy_returns_initial_capital(self):
        bars = _make_bars(20)
        result = run_backtest(bars, _do_nothing, initial_capital=10_000.0)
        assert len(result.equity_curve) == 20
        assert result.equity_curve[0] == pytest.approx(10_000.0)
        assert result.equity_curve[-1] == pytest.approx(10_000.0)

    def test_buy_and_hold_produces_fills(self):
        bars = _make_bars(50)
        result = run_backtest(bars, _buy_and_hold, initial_capital=10_000.0)
        assert len(result.fills) == 1
        assert result.fills[0].order.side == "buy"

    def test_metrics_keys_present(self):
        bars = _make_bars(50)
        result = run_backtest(bars, _buy_and_hold, initial_capital=10_000.0)
        for key in ("total_return", "sharpe", "sortino", "max_drawdown", "calmar"):
            assert key in result.metrics, f"missing metric: {key}"

    def test_no_look_ahead(self):
        """Strategy must never see future bars."""
        seen_lengths = []

        def recorder(history: list[Bar]) -> Order | None:
            seen_lengths.append(len(history))
            return None

        bars = _make_bars(10)
        run_backtest(bars, recorder)
        assert seen_lengths == list(range(1, 11)), "look-ahead bias detected"

    def test_cost_model_deducted(self):
        bars = _make_bars(10)
        result = run_backtest(bars, _buy_and_hold, initial_capital=10_000.0)
        fill = result.fills[0]
        assert fill.total_cost_usd > 0

    def test_uptrend_positive_return(self):
        bars = _make_bars(100)
        result = run_backtest(bars, _buy_and_hold, initial_capital=10_000.0)
        # buy-and-hold on an uptrend should be positive after costs
        assert result.metrics["total_return"] > 0
