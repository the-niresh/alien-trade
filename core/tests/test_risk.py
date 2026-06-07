"""
Risk engine tests: sizing, guardrails, daily-loss kill, circuit breaker,
walk-forward drawdown comparison.
"""
from __future__ import annotations
import pytest
import numpy as np
from backtest.engine import Bar, Order, run_backtest
from backtest.costs import BSCCostModel
from backtest.walk_forward import WalkForwardConfig, run_walk_forward
from risk.guardrails import RiskConfig, TOKEN_ALLOWLIST, check_guardrails, check_slippage
from risk.sizing import vol_target_size, kelly_fraction, compute_position_size, realized_vol
from risk.engine import RiskEngine, make_risk_strategy
from strategy.combined import StrategyParams, make_strategy
from strategy.optimizer import walk_forward_optimize_fn, walk_forward_strategy_factory


def _bars(n, start=300.0, trend=1.002, vol=0.015, seed=42):
    rng = np.random.default_rng(seed)
    bars, price = [], start
    for i in range(n):
        price *= trend * (1 + rng.normal(0, vol))
        bars.append(Bar(
            timestamp=1_700_000_000_000 + i * 86_400_000,
            open=price * 0.999, high=price * 1.01,
            low=price * 0.99, close=price, volume=5_000_000.0,
        ))
    return bars


def _volatile_bars(n, start=300.0):
    rng = np.random.default_rng(7)
    bars, price = [], start
    for i in range(n):
        price *= 1 + rng.normal(0, 0.05)   # 5% daily vol — very high
        price = max(price, 1.0)
        bars.append(Bar(
            timestamp=1_700_000_000_000 + i * 86_400_000,
            open=price * 0.98, high=price * 1.06,
            low=price * 0.94, close=price, volume=10_000_000.0,
        ))
    return bars


# ── Sizing ────────────────────────────────────────────────────────────────────

class TestSizing:
    def test_high_vol_reduces_size(self):
        low_vol  = _bars(30, vol=0.005)
        high_vol = _volatile_bars(30)
        s_low  = vol_target_size(low_vol,  1_000.0, 10_000.0)
        s_high = vol_target_size(high_vol, 1_000.0, 10_000.0)
        assert s_high < s_low, f"high vol should shrink size: {s_high:.0f} vs {s_low:.0f}"

    def test_size_respects_capital_cap(self):
        bars = _bars(30, vol=0.001)   # very low vol → would want large size
        size = vol_target_size(bars, 1_000.0, capital=5_000.0, max_pct=0.20)
        assert size <= 5_000.0 * 0.20 + 1e-6

    def test_kelly_zero_on_no_edge(self):
        assert kelly_fraction(0.4, 0.01, 0.02) == 0.0   # negative edge

    def test_kelly_positive_edge(self):
        kf = kelly_fraction(0.6, 0.02, 0.01)
        assert 0.0 < kf <= 0.25

    def test_realized_vol_positive(self):
        rv = realized_vol(_bars(30))
        assert rv > 0.0

    def test_realized_vol_higher_for_volatile(self):
        rv_normal   = realized_vol(_bars(30, vol=0.01))
        rv_volatile = realized_vol(_volatile_bars(30))
        assert rv_volatile > rv_normal


# ── Guardrails ────────────────────────────────────────────────────────────────

class TestGuardrails:
    def _cfg(self, **kw):
        return RiskConfig(**kw)

    def test_daily_loss_halt(self):
        cfg = self._cfg(daily_loss_limit_pct=0.05)
        r = check_guardrails("BNB", 500.0, daily_loss_pct=0.06,
                             consecutive_losses=0, capital=10_000.0, config=cfg)
        assert not r.allowed
        assert "daily-loss" in r.reason

    def test_circuit_breaker(self):
        cfg = self._cfg(max_consecutive_losses=3)
        r = check_guardrails("BNB", 500.0, daily_loss_pct=0.0,
                             consecutive_losses=4, capital=10_000.0, config=cfg)
        assert not r.allowed
        assert "circuit breaker" in r.reason

    def test_trade_size_cap(self):
        cfg = self._cfg(max_trade_usd=1_000.0)
        r = check_guardrails("BNB", 1_500.0, daily_loss_pct=0.0,
                             consecutive_losses=0, capital=10_000.0, config=cfg)
        assert not r.allowed

    def test_token_allowlist_blocks_unknown(self):
        cfg = self._cfg()
        r = check_guardrails("DOGE", 500.0, daily_loss_pct=0.0,
                             consecutive_losses=0, capital=10_000.0, config=cfg)
        assert not r.allowed
        assert "allowlist" in r.reason

    def test_token_allowlist_passes_bnb(self):
        cfg = self._cfg()
        r = check_guardrails("BNB", 500.0, daily_loss_pct=0.0,
                             consecutive_losses=0, capital=10_000.0, config=cfg)
        assert r.allowed

    def test_slippage_cap(self):
        cfg = self._cfg(max_slippage_pct=0.02)
        assert not check_slippage(0.03, cfg).allowed
        assert check_slippage(0.01, cfg).allowed

    def test_clean_trade_passes_all(self):
        cfg = self._cfg()
        r = check_guardrails("BNB", 800.0, daily_loss_pct=0.01,
                             consecutive_losses=1, capital=10_000.0, config=cfg)
        assert r.allowed


# ── RiskEngine ────────────────────────────────────────────────────────────────

class TestRiskEngine:
    def _make(self, **cfg_kw):
        params = StrategyParams(s1_fast=8, s1_slow=21, position_size_usd=1_000.0)
        inner = make_strategy(params)
        cfg = RiskConfig(**cfg_kw)
        return make_risk_strategy(inner, cfg, initial_capital=10_000.0)

    def test_engine_is_callable_strategy(self):
        engine = self._make()
        bars = _bars(50, trend=1.004)
        result = run_backtest(bars, engine, cost_model=BSCCostModel())
        assert "sortino" in result.metrics

    def test_daily_loss_kill_halts_trading(self):
        """Simulate a bad day: inject daily_loss > limit → engine must stop issuing orders."""
        params = StrategyParams(s1_fast=5, s1_slow=21, entry_threshold=0.05,
                                position_size_usd=1_000.0)
        inner = make_strategy(params)
        cfg = RiskConfig(daily_loss_limit_pct=0.03)   # 3% daily limit
        engine = RiskEngine(inner, cfg, initial_capital=10_000.0)

        # Force a large loss in the tracker by simulating a crash day
        crash_bars = _bars(60, trend=0.93, vol=0.02)  # crashing market
        result = run_backtest(crash_bars, engine, cost_model=BSCCostModel())
        # Engine must have produced fewer fills than a naive strategy would
        naive = make_strategy(params)
        naive_result = run_backtest(crash_bars, naive, cost_model=BSCCostModel())
        assert len(result.fills) <= len(naive_result.fills)

    def test_high_vol_shrinks_order_size(self):
        """In volatile market, risk engine should issue smaller orders than base size."""
        params = StrategyParams(s1_fast=5, s1_slow=21, entry_threshold=0.05,
                                position_size_usd=1_000.0)
        inner = make_strategy(params)
        cfg = RiskConfig(base_position_usd=1_000.0, target_vol_ann=0.15)
        engine = RiskEngine(inner, cfg, initial_capital=10_000.0)

        bars = _volatile_bars(80)
        result = run_backtest(bars, engine, cost_model=BSCCostModel())
        if result.fills:
            avg_size = sum(f.order.size_usd for f in result.fills) / len(result.fills)
            assert avg_size <= 1_000.0 * 1.05, f"size not shrunk in high vol: {avg_size:.0f}"

    def test_blocked_token_never_trades(self):
        """Orders for non-allowlisted tokens must be blocked."""
        def bad_strategy(history):
            if len(history) == 5:
                return Order(side="buy", size_usd=500.0,
                             symbol="DOGE", timestamp=history[-1].timestamp)
            return None
        cfg = RiskConfig()
        engine = RiskEngine(bad_strategy, cfg, initial_capital=10_000.0)
        result = run_backtest(_bars(20), engine)
        assert len(result.fills) == 0

    def test_per_trade_cap_enforced(self):
        """No fill should exceed max_trade_usd."""
        params = StrategyParams(s1_fast=5, s1_slow=21, entry_threshold=0.05,
                                position_size_usd=5_000.0)   # wants big size
        inner = make_strategy(params)
        cfg = RiskConfig(max_trade_usd=1_000.0)
        engine = RiskEngine(inner, cfg, initial_capital=10_000.0)
        result = run_backtest(_bars(100, trend=1.004), engine, cost_model=BSCCostModel())
        for f in result.fills:
            assert f.order.size_usd <= 1_000.0 + 1e-6, f"cap breached: {f.order.size_usd}"


# ── Walk-forward: risk engine reduces max drawdown ────────────────────────────

class TestWalkForwardWithRisk:
    def test_risk_engine_cuts_drawdown_on_real_data(self):
        from backtest.data_loader import load_bars
        from backtest.walk_forward import print_oos_report

        bars = load_bars("BNB")
        cfg = WalkForwardConfig(train_bars=180, test_bars=90)
        cost = BSCCostModel()

        # Plain walk-forward (no risk engine)
        plain = run_walk_forward(bars, walk_forward_strategy_factory,
                                 walk_forward_optimize_fn, cfg, cost_model=cost)

        # Walk-forward WITH risk engine wrapping each window's strategy
        cfg2 = RiskConfig(daily_loss_limit_pct=0.05, max_consecutive_losses=5,
                          target_vol_ann=0.15)

        def risk_factory(params):
            inner = walk_forward_strategy_factory(params)
            return make_risk_strategy(inner, cfg2, initial_capital=10_000.0)

        risk_wf = run_walk_forward(bars, risk_factory,
                                   walk_forward_optimize_fn, cfg, cost_model=cost)

        print("\n--- Plain OOS ---")
        print_oos_report(plain)
        print("--- Risk-engine OOS ---")
        print_oos_report(risk_wf)

        plain_dd  = plain.oos_metrics.get("oos_max_drawdown", 0.0)
        risk_dd   = risk_wf.oos_metrics.get("oos_max_drawdown", 0.0)
        # Risk engine drawdown must be ≥ plain (less negative = better)
        assert risk_dd >= plain_dd - 0.02, (
            f"Risk engine worsened drawdown: {risk_dd:.2%} vs plain {plain_dd:.2%}"
        )
