import json
from unittest.mock import MagicMock, patch
from agent.command_worker import _dispatch


def _make_twak(tx_hash="0xabc"):
    twak = MagicMock()
    twak.available = True
    twak.transfer = MagicMock(return_value={"hash": tx_hash, "explorer": "https://bscscan.com/tx/0xabc"})
    return twak


def test_withdraw_usdt_dispatches_transfer():
    twak = _make_twak()
    with patch("agent.command_worker.TwakCli", return_value=twak):
        result = _dispatch("withdraw", {"to_address": "0xDEAD000000000000000000000000000000000001", "amount": 5.0, "token": "USDT"}, MagicMock())
    twak.transfer.assert_called_once_with("0xDEAD000000000000000000000000000000000001", 5.0, "USDT", chain="bsc")
    assert result["tx_hash"] == "0xabc"


def test_withdraw_bnb_native_transfer():
    twak = _make_twak("0xdef")
    with patch("agent.command_worker.TwakCli", return_value=twak):
        result = _dispatch("withdraw", {"to_address": "0xBEEF000000000000000000000000000000000002", "amount": 0.005, "token": "BNB"}, MagicMock())
    twak.transfer.assert_called_once_with("0xBEEF000000000000000000000000000000000002", 0.005, "BNB", chain="bsc")
    assert result["tx_hash"] == "0xdef"


def test_withdraw_missing_to_address_raises():
    twak = _make_twak()
    with patch("agent.command_worker.TwakCli", return_value=twak):
        try:
            _dispatch("withdraw", {"amount": 5.0, "token": "USDT"}, MagicMock())
            assert False, "should raise"
        except (ValueError, KeyError):
            pass  # expected


def test_withdraw_zero_amount_raises():
    twak = _make_twak()
    with patch("agent.command_worker.TwakCli", return_value=twak):
        try:
            _dispatch("withdraw", {"to_address": "0xABC0000000000000000000000000000000000003", "amount": 0, "token": "USDT"}, MagicMock())
            assert False, "should raise"
        except ValueError:
            pass


def test_withdraw_invalid_address_raises():
    twak = _make_twak()
    with patch("agent.command_worker.TwakCli", return_value=twak):
        try:
            _dispatch("withdraw", {"to_address": "notanaddress", "amount": 1.0, "token": "USDT"}, MagicMock())
            assert False, "should raise"
        except ValueError:
            pass
