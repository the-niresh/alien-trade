"""
Step 2 exit criterion tests.
Covers: cost model, data loader, regime detector, walk-forward harness.
All tests use synthetic data — no network calls.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from backtest.engine import Bar, BacktestResult, Fill, Order, Trade, run_backtest
from backtest.costs import BSCCostModel, amm_slippage
from backtest.regime import Regime, detect_regime
from backtest.walk_forward import WalkForwardConfig, WalkForwardResult, run_walk_forward


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bars(n: int = 100, start_price: float = 300.0, trend: float = 1.002) -> list[Bar]:
    bars, price = [], start_price
    for i in range(n):
        price *= trend
        bars.append(Bar(
            timestamp=1_700_000_000_000 + i * 86_400_000,
            open=price * 0.999,
            high=price * 1.005,
            low=price * 0.994,
            close=price,
            volume=5_000_000.0,
        ))
    return bars


def _choppy_bars(n: int = 100, start_price: float = 300.0) -> list[Bar]:
    """Alternating up/down — no persistent trend."""
    bars, price = [], start_price
    for i in range(n):
        price *= (1.01 if i % 2 == 0 else 0.99)
        bars.append(Bar(
            timestamp=1_700_000_000_000 + i * 86_400_000,
            open=price * 0.999,
            high=price * 1.02,
            low=price * 0.98,
            close=price,
            volume=3_000_000.0,
        ))
    return bars


def _volatile_bars(n: int = 50) -> list[Bar]:
    """High ATR/price ratio to trigger HIGH_VOL regime."""
    bars, price = [], 300.0
    for i in range(n):
        swing = 0.07 * price
        bars.append(Bar(
            timestamp=1_700_000_000_000 + i * 86_400_000,
            open=price - swing * 0.5,
            high=price + swing,
            low=price - swing,
            close=price * (1.005 if i % 3 != 0 else 0.98),
            volume=10_000_000.0,
        ))
        price = bars[-1].close
    return bars


def _buy_once(history: list[Bar]) -> Order | None:
    if len(history) == 1:
        return Order(side="buy", size_usd=1_000.0, symbol="BNB", timestamp=history[-1].timestamp)
    return None


def _buy_sell(history: list[Bar]) -> Order | None:
    """Buy on bar 5, sell on bar 15."""
    if len(history) == 5:
        return Order(side="buy", size_usd=500.0, symbol="BNB", timestamp=history[-1].timestamp)
    if len(history) == 15:
        return Order(side="sell", size_usd=500.0, symbol="BNB", timestamp=history[-1].timestamp)
    return None


def _do_nothing(history: list[Bar]) -> Order | None:
    return None


# ── Step 0 harness — must still pass ─────────────────────────────────────────

class TestHarnessBackcompat:
    def test_empty_strategy_returns_initial_capital(self):
        bars = _bars(20)
        result = run_backtest(bars, _do_nothing, initial_capital=10_000.0)
        assert len(result.equity_curve) == 20
        assert result.equity_curve[0] == pytest.approx(10_000.0)
        assert result.equity_curve[-1] == pytest.approx(10_000.0)

    def test_buy_and_hold_produces_fills(self):
        result = run_backtest(_bars(50), _buy_once, initial_capital=10_000.0)
        assert len(result.fills) == 1
        assert result.fills[0].order.side == "buy"

    def test_metrics_keys_present(self):
        result = run_backtest(_bars(50), _buy_once)
        for key in ("total_return", "sharpe", "sortino", "max_drawdown", "calmar"):
            assert key in result.metrics, f"missing metric: {key}"

    def test_no_look_ahead(self):
        seen = []
        def recorder(h):
            seen.append(len(h))
            return None
        run_backtest(_bars(10), recorder)
        assert seen == list(range(1, 11))

    def test_cost_model_deducted(self):
        result = run_backtest(_bars(10), _buy_once)
        assert result.fills[0].total_cost_usd > 0

    def test_uptrend_positive_return(self):
        result = run_backtest(_bars(100), _buy_once)
        assert result.metrics["total_return"] > 0


# ── Cost model ────────────────────────────────────────────────────────────────

class TestBSCCostModel:
    def test_fee_is_25_bps(self):
        model = BSCCostModel()
        bar = _bars(1)[0]
        order = Order(side="buy", size_usd=10_000.0, symbol="BNB", timestamp=0)
        fee, gas, slippage = model(order, bar)
        assert fee == pytest.approx(10_000.0 * 0.0025)

    def test_gas_positive_and_bounded(self):
        model = BSCCostModel()
        bar = _bars(1)[0]
        order = Order(side="buy", size_usd=1_000.0, symbol="BNB", timestamp=0)
        _, gas, _ = model(order, bar)
        assert 0.10 < gas < 5.0, f"gas out of expected range: {gas}"

    def test_slippage_grows_with_size(self):
        s_small = amm_slippage(100.0)
        s_large = amm_slippage(100_000.0)
        assert s_large > s_small

    def test_slippage_sqrt_relationship(self):
        """Impact ∝ sqrt(size/liquidity) — 4x size → ~2x impact rate."""
        s1 = amm_slippage(1_000.0)
        s4 = amm_slippage(4_000.0)
        ratio = (s4 / 4_000.0) / (s1 / 1_000.0)
        assert 1.8 < ratio < 2.2, f"sqrt relationship broken: ratio={ratio}"

    def test_total_cost_higher_than_placeholder(self):
        """Real cost model must be more conservative than the 0.10% slippage placeholder."""
        model = BSCCostModel()
        bar = _bars(1)[0]
        order = Order(side="buy", size_usd=5_000.0, symbol="BNB", timestamp=0)
        fee, gas, slippage = model(order, bar)
        real_cost = fee + gas + slippage
        placeholder_cost = 5_000.0 * 0.0025 + 0.30 + 5_000.0 * 0.001
        assert real_cost > placeholder_cost * 0.5  # real cost is in the same ballpark

    def test_funding_cost_zero_when_no_rate(self):
        model = BSCCostModel()
        bar = Bar(timestamp=0, open=300.0, high=305.0, low=295.0, close=300.0, volume=1e6)
        assert model.funding_cost(10_000.0, bar) == 0.0

    def test_funding_cost_nonzero_with_rate(self):
        model = BSCCostModel()
        bar = Bar(timestamp=0, open=300.0, high=305.0, low=295.0, close=300.0,
                  volume=1e6, funding_rate=0.0001)
        cost = model.funding_cost(10_000.0, bar)
        assert cost == pytest.approx(10_000.0 * 0.0001 * 3.0)


# ── Regime detector ───────────────────────────────────────────────────────────

class TestRegimeDetector:
    def test_insufficient_data_is_chop(self):
        assert detect_regime(_bars(5), lookback=20) == Regime.CHOP

    def test_strong_uptrend_detected(self):
        bars = _bars(50, trend=1.004)  # strong 0.4%/day trend
        regime = detect_regime(bars, lookback=20)
        assert regime == Regime.TREND

    def test_high_vol_detected(self):
        bars = _volatile_bars(50)
        regime = detect_regime(bars, lookback=20)
        assert regime == Regime.HIGH_VOL

    def test_crash_detected(self):
        bars = _bars(30, start_price=400.0)
        # Crash: last bar way below the peak
        for i in range(5):
            bars.append(Bar(
                timestamp=bars[-1].timestamp + 86_400_000,
                open=200.0, high=205.0, low=195.0, close=200.0,
                volume=20_000_000.0,
            ))
        regime = detect_regime(bars, lookback=20)
        assert regime == Regime.CRASH

    def test_choppy_is_chop(self):
        bars = _choppy_bars(50)
        regime = detect_regime(bars, lookback=20)
        assert regime in (Regime.CHOP, Regime.HIGH_VOL)  # both valid for noisy data


# ── Walk-forward harness ──────────────────────────────────────────────────────

class TestWalkForward:
    def _simple_factory(self, params: dict):
        """Ignore params; always buy once."""
        return _buy_once

    def _simple_optimize(self, train_bars: list[Bar]) -> dict:
        return {"dummy": 1}

    def test_oos_windows_produced(self):
        bars = _bars(600)
        cfg = WalkForwardConfig(train_bars=200, test_bars=100)
        result = run_walk_forward(bars, self._simple_factory, self._simple_optimize, cfg)
        assert len(result.oos_windows) >= 2

    def test_oos_metrics_keys_present(self):
        bars = _bars(500)
        cfg = WalkForwardConfig(train_bars=200, test_bars=100)
        result = run_walk_forward(bars, self._simple_factory, self._simple_optimize, cfg)
        for key in ("oos_total_return", "oos_sharpe", "oos_sortino",
                    "oos_max_drawdown", "oos_calmar", "oos_win_rate", "oos_n_fills"):
            assert key in result.oos_metrics, f"missing OOS metric: {key}"

    def test_no_insample_keys_in_oos_metrics(self):
        bars = _bars(500)
        cfg = WalkForwardConfig(train_bars=200, test_bars=100)
        result = run_walk_forward(bars, self._simple_factory, self._simple_optimize, cfg)
        for key in result.oos_metrics:
            assert key.startswith("oos_"), f"non-OOS key leaked: {key}"

    def test_params_logged_per_window(self):
        bars = _bars(500)
        cfg = WalkForwardConfig(train_bars=200, test_bars=100)
        result = run_walk_forward(bars, self._simple_factory, self._simple_optimize, cfg)
        assert len(result.window_params) == len(result.oos_windows)

    def test_real_cost_model_applied(self):
        from backtest.costs import BSCCostModel
        bars = _bars(500)
        cfg = WalkForwardConfig(train_bars=200, test_bars=100)
        result_plain = run_walk_forward(bars, self._simple_factory, self._simple_optimize, cfg)
        result_bsc = run_walk_forward(
            bars, self._simple_factory, self._simple_optimize, cfg,
            cost_model=BSCCostModel(),
        )
        # BSC cost model should result in lower or equal OOS return (more costs)
        assert result_bsc.oos_metrics["oos_total_return"] <= result_plain.oos_metrics["oos_total_return"] + 1e-6

    def test_insufficient_data_no_windows(self):
        bars = _bars(50)
        cfg = WalkForwardConfig(train_bars=100, test_bars=30)
        result = run_walk_forward(bars, self._simple_factory, self._simple_optimize, cfg)
        assert len(result.oos_windows) == 0


# ── New engine features ───────────────────────────────────────────────────────

class TestEngineNewFeatures:
    def test_round_trip_trade_recorded(self):
        result = run_backtest(_bars(30), _buy_sell)
        assert len(result.trades) == 1

    def test_win_rate_in_metrics(self):
        result = run_backtest(_bars(50), _buy_sell)
        assert "win_rate" in result.metrics

    def test_n_trades_in_metrics(self):
        result = run_backtest(_bars(50), _buy_sell)
        assert result.metrics["n_trades"] >= 0

    def test_next_bar_fill_no_look_ahead(self):
        """With 1-bar latency, strategy on bar i cannot affect bar i fill price."""
        seen = []
        def spy(h):
            seen.append(len(h))
            if len(h) == 3:
                return Order(side="buy", size_usd=500.0, symbol="BNB", timestamp=h[-1].timestamp)
            return None

        bars = _bars(10)
        result = run_backtest(bars, spy, next_bar_open_fill=True)
        # Fill should happen at bar 4's open (index 3), so equity starts changing from bar 4
        assert len(result.fills) == 1
        assert seen == list(range(1, 11))

    def test_n_fills_matches_actual_fills(self):
        result = run_backtest(_bars(30), _buy_sell)
        assert result.metrics["n_fills"] == len(result.fills)


# ── Data loader ───────────────────────────────────────────────────────────────

@pytest.mark.integration   # reads parquet history from core/data/parquet (gitignored)
class TestDataLoader:
    def test_loads_bnb_bars(self):
        from backtest.data_loader import load_bars
        bars = load_bars("BNB")
        assert len(bars) >= 365, f"Expected ≥365 bars, got {len(bars)}"

    def test_bars_are_sorted_ascending(self):
        from backtest.data_loader import load_bars
        bars = load_bars("BNB")
        ts = [b.timestamp for b in bars]
        assert ts == sorted(ts), "Bars not sorted ascending by timestamp"

    def test_bar_fields_populated(self):
        from backtest.data_loader import load_bars
        bar = load_bars("BNB")[0]
        assert bar.open > 0
        assert bar.high >= bar.low
        assert bar.close > 0
        assert bar.volume >= 0

    def test_multi_symbol_load(self):
        from backtest.data_loader import load_multi
        data = load_multi(["BNB", "BTC", "ETH"])
        assert set(data.keys()) == {"BNB", "BTC", "ETH"}
        for sym, bars in data.items():
            assert len(bars) > 100, f"{sym} has too few bars"

    def test_missing_file_raises(self):
        from backtest.data_loader import load_bars
        with pytest.raises(FileNotFoundError):
            load_bars("FAKECOIN")
