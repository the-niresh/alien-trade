"""Tests for the slippage retry ladder in OnchainExecutor.execute()."""
from unittest.mock import MagicMock, call

import pytest

from agent.executor import TwakSwapExecutor, FILLED, FAILED, REJECTED
from agent.twak_cli import TwakError, TwakSwapResult, TwakQuote
from core.risk.guardrails import RiskConfig
from backtest.engine import Bar, Order


def _bar():
    return Bar(open=1800, high=1820, low=1780, close=1800, volume=1e6,
               timestamp=1_700_000_000)


def _order(side="buy", size_usd=4.0):
    return Order(symbol="ETH", side=side, size_usd=size_usd, timestamp=1_700_000_000)


def _quote(impact=0.001):
    return TwakQuote(from_token="USDT", to_token="ETH",
                     amount_in=4.0, amount_out=0.002,
                     price_impact_pct=impact, raw={})


def _make_executor(twak, dry_run=False):
    return TwakSwapExecutor(
        twak,
        RiskConfig(max_slippage_pct=0.02),
        bnb_exec=None,
        bridge=None,
        dry_run=dry_run,
    )


# ── happy path ────────────────────────────────────────────────────────────────

def test_succeeds_first_rung():
    """If first slippage level works, no retry."""
    twak = MagicMock()
    twak.swap_quote.return_value = _quote()
    twak.swap_execute.return_value = TwakSwapResult(tx_hash="0xabc", raw={})
    twak.risk.return_value = {"isRug": False, "score": 0}

    ex = _make_executor(twak)
    report = ex.execute(_order(), _bar(), "key-1")

    assert report.status == FILLED
    assert report.tx_hash == "0xabc"
    # Only one swap_execute call — no retry needed
    assert twak.swap_execute.call_count == 1


# ── retry ladder ──────────────────────────────────────────────────────────────

def test_retries_on_tx_failed_then_succeeds():
    """TX_FAILED at 2% → auto-retries at 5% → succeeds."""
    twak = MagicMock()
    twak.swap_quote.return_value = _quote()
    twak.risk.return_value = {"isRug": False, "score": 0}

    call_count = [0]
    def execute_side_effect(from_tok, to_tok, *, usd, chain, slippage):
        call_count[0] += 1
        if call_count[0] == 1:
            raise TwakError("execution reverted: 0xf4059071 TX_FAILED")
        return TwakSwapResult(tx_hash="0xdef", raw={})

    twak.swap_execute.side_effect = execute_side_effect

    ex = _make_executor(twak)
    report = ex.execute(_order(), _bar(), "key-2")

    assert report.status == FILLED
    assert report.tx_hash == "0xdef"
    assert twak.swap_execute.call_count == 2

    # First call at base (2%), second at 5%
    calls = twak.swap_execute.call_args_list
    assert calls[0].kwargs["slippage"] == pytest.approx(2.0)
    assert calls[1].kwargs["slippage"] == pytest.approx(5.0)


def test_exhausts_all_rungs_returns_failed():
    """If all slippage levels get TX_FAILED, returns FAILED not exception."""
    twak = MagicMock()
    twak.swap_quote.return_value = _quote()
    twak.risk.return_value = {"isRug": False, "score": 0}
    twak.swap_execute.side_effect = TwakError("TX_FAILED at every level")

    ex = _make_executor(twak)
    report = ex.execute(_order(), _bar(), "key-3")

    assert report.status == FAILED
    # Should have tried all 3 rungs (2%, 5%, 8%)
    assert twak.swap_execute.call_count == 3


def test_non_tx_failed_error_does_not_retry():
    """Auth or network errors stop immediately — no retry."""
    twak = MagicMock()
    twak.swap_quote.return_value = _quote()
    twak.risk.return_value = {"isRug": False, "score": 0}
    twak.swap_execute.side_effect = TwakError("auth failed: wallet locked")

    ex = _make_executor(twak)
    report = ex.execute(_order(), _bar(), "key-4")

    assert report.status == FAILED
    assert twak.swap_execute.call_count == 1  # stops immediately


def test_rug_check_runs_once_across_retries():
    """_rug_check must not be called on every retry rung."""
    twak = MagicMock()
    twak.swap_quote.return_value = _quote()
    twak.risk.return_value = {"isRug": False, "score": 0}

    call_count = [0]
    def execute_side_effect(from_tok, to_tok, *, usd, chain, slippage):
        call_count[0] += 1
        if call_count[0] < 2:
            raise TwakError("TX_FAILED")
        return TwakSwapResult(tx_hash="0xghi", raw={})

    twak.swap_execute.side_effect = execute_side_effect

    ex = _make_executor(twak)
    ex.execute(_order(), _bar(), "key-5")

    # risk() = rug check — called once regardless of retry count
    assert twak.risk.call_count == 1
