from unittest.mock import MagicMock, patch
from agent.command_worker import run_one_command, _dispatch


def test_run_one_command_returns_false_when_empty():
    bridge = MagicMock()
    bridge.pop_queued_command.return_value = None
    assert run_one_command(bridge) is False


def test_run_one_command_dispatches_and_marks_done():
    bridge = MagicMock()
    bridge.pop_queued_command.return_value = {
        "_id": "cmd123",
        "command_type": "automate_pause",
        "params": '{"id": "auto-1"}',
    }
    with patch("agent.command_worker._dispatch", return_value={"ok": True}) as mock_d:
        result = run_one_command(bridge)
    assert result is True
    bridge.update_command_status.assert_called_with("cmd123", "done", result='{"ok": true}')


def test_dispatch_raises_on_unknown_type():
    import pytest
    with pytest.raises(ValueError, match="unknown command_type"):
        _dispatch("mystery_command", {}, MagicMock())


def _convert_params(from_token="BNB", to_token="USDT", usd=4.0):
    return {"from_token": from_token, "to_token": to_token, "usd": usd}


def test_convert_quotes_then_executes_when_impact_ok():
    bridge = MagicMock()
    # Patch BNBExec so the post-swap gas-receipt step never hits the real chain.
    with patch("agent.command_worker.TwakCli") as MockCli, \
         patch("exec.bnb.BNBExec"):
        twak = MockCli.return_value
        twak.swap_quote.return_value = MagicMock(price_impact_pct=0.012, amount_out=3.98,
                                                 amount_in=4.0, raw={})
        twak.balance.return_value = {"available": 100.0, "tokens": []}  # BNB funds available
        twak.swap_execute.return_value = MagicMock(tx_hash="0xdead", raw={})
        result = _dispatch("convert", _convert_params(), bridge)
    twak.swap_quote.assert_called_once()
    twak.swap_execute.assert_called_once()
    bridge.record_trade.assert_called_once()
    assert result["tx_hash"] == "0xdead"
    assert result["from_token"] == "BNB"
    assert result["to_token"] == "USDT"
    assert result["expected_out"] == 3.98


def test_convert_aborts_when_price_impact_exceeds_cap():
    import pytest
    with patch("agent.command_worker.TwakCli") as MockCli:
        twak = MockCli.return_value
        twak.swap_quote.return_value = MagicMock(price_impact_pct=0.09, amount_out=3.5)
        with pytest.raises(ValueError, match="price impact"):
            _dispatch("convert", _convert_params(), MagicMock())
        twak.swap_execute.assert_not_called()


def test_convert_rejects_same_from_and_to():
    import pytest
    with patch("agent.command_worker.TwakCli") as MockCli:
        with pytest.raises(ValueError, match="differ"):
            _dispatch("convert", _convert_params(from_token="USDT", to_token="USDT"), MagicMock())


def test_convert_rejects_unsupported_token():
    import pytest
    # DOGE is not in CONVERT_ALLOWLIST (CAKE/ETH/etc. ARE) — must be rejected.
    with patch("agent.command_worker.TwakCli"):
        with pytest.raises(ValueError, match="unsupported"):
            _dispatch("convert", {"from_token": "DOGE", "to_token": "USDT", "usd": 4.0}, MagicMock())
