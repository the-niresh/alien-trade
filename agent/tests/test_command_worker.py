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
        _dispatch("mystery_command", {})
