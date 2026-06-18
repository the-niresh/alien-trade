"""Tests for the pre-trade rug-check gate in executor.py."""
from unittest.mock import MagicMock
import pytest


def _make_executor(rug_check_enabled=True, rug_risk_threshold=75):
    from agent.executor import TwakSwapExecutor
    bridge = MagicMock()
    bridge.get_config.return_value = {
        "rug_check_enabled": rug_check_enabled,
        "rug_risk_threshold": rug_risk_threshold,
    }
    twak = MagicMock()
    ex = TwakSwapExecutor.__new__(TwakSwapExecutor)
    ex.bridge = bridge
    ex._twak = twak
    ex.mode = "mainnet"
    return ex, bridge, twak


def test_rug_check_blocks_risky_token():
    ex, bridge, twak = _make_executor()
    twak.risk.return_value = {"isRug": False, "riskScore": 90}
    with pytest.raises(Exception, match="rug risk"):
        ex._rug_check("c60_t0xSUSPECT")


def test_rug_check_blocks_rug_flag():
    ex, bridge, twak = _make_executor()
    twak.risk.return_value = {"isRug": True, "riskScore": 30}
    with pytest.raises(Exception, match="rug risk"):
        ex._rug_check("c60_t0xRUG")


def test_rug_check_passes_safe_token():
    ex, bridge, twak = _make_executor()
    twak.risk.return_value = {"isRug": False, "riskScore": 10}
    ex._rug_check("c60")   # should not raise


def test_rug_check_skipped_when_disabled():
    ex, bridge, twak = _make_executor(rug_check_enabled=False)
    ex._rug_check("c60_t0xANYTHING")   # should not raise, not even call twak
    twak.risk.assert_not_called()
