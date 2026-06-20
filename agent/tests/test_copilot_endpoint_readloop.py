from unittest.mock import patch, MagicMock
import agent.server as server


def test_copilot_uses_read_loop_when_second_brain_off():
    body = {"question": "what's my pnl?"}
    loop_result = {"answer": "Up $1.50.", "grounded": True,
                   "sources": [{"tool": "get_agent_state", "args": {}}]}
    with patch.object(server, "_second_brain", return_value=None), \
         patch.object(server, "_copilot_read_loop", return_value=loop_result) as rl:
        out = server.copilot(body)
    rl.assert_called_once_with("what's my pnl?")
    assert out["answer"] == "Up $1.50."
    assert out["grounded"] is True
    assert "action" in out  # server attaches action (None for a read)


def test_copilot_falls_back_to_narrator_when_read_loop_returns_none():
    body = {"question": "hello"}
    with patch.object(server, "_second_brain", return_value=None), \
         patch.object(server, "_copilot_read_loop", return_value=None), \
         patch.object(server, "_copilot_fallback", return_value="hi there") as fb:
        out = server.copilot(body)
    fb.assert_called_once()
    assert out["answer"] == "hi there"
    assert out["grounded"] is False


def test_read_loop_helper_returns_none_without_api_key():
    with patch.dict("os.environ", {}, clear=False) as _env:
        import os
        os.environ.pop("ANTHROPIC_API_KEY", None)
        assert server._copilot_read_loop("x") is None
