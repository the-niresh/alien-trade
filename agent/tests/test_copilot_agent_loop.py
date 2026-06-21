from types import SimpleNamespace
from unittest.mock import MagicMock
from agent.copilot_agent import run_read_loop, MAX_TOOL_TURNS


def _text_block(text):
    return SimpleNamespace(type="text", text=text)


def _tool_block(tid, name, inp):
    return SimpleNamespace(type="tool_use", id=tid, name=name, input=inp)


def _resp(stop_reason, content):
    return SimpleNamespace(stop_reason=stop_reason, content=content)


def _deps():
    return MagicMock(), MagicMock(), MagicMock()


def test_answers_without_tools_when_model_does_not_call_any():
    twak, skills, bridge = _deps()
    client = MagicMock()
    client.messages.create.return_value = _resp("end_turn", [_text_block("All good, flat.")])
    out = run_read_loop("hi", twak=twak, skills=skills, bridge=bridge, client=client)
    assert out["answer"] == "All good, flat."
    assert out["grounded"] is False
    assert out["sources"] == []
    assert client.messages.create.call_count == 1


def test_executes_tool_then_returns_final_text():
    twak, skills, bridge = _deps()
    twak.price.return_value = {"price": 2.31}
    client = MagicMock()
    client.messages.create.side_effect = [
        _resp("tool_use", [_tool_block("t1", "get_price", {"token": "CAKE"})]),
        _resp("end_turn", [_text_block("CAKE is $2.31.")]),
    ]
    out = run_read_loop("price of cake?", twak=twak, skills=skills, bridge=bridge, client=client)
    assert out["answer"] == "CAKE is $2.31."
    assert out["grounded"] is True
    assert out["sources"] == [{"tool": "get_price", "args": {"token": "CAKE"}}]
    assert client.messages.create.call_count == 2


def test_loop_stops_at_max_turns():
    twak, skills, bridge = _deps()
    client = MagicMock()
    # Always returns tool_use -> would loop forever without the cap.
    client.messages.create.return_value = _resp(
        "tool_use", [_tool_block("t", "get_wallet", {})]
    )
    out = run_read_loop("x", twak=twak, skills=skills, bridge=bridge, client=client)
    # One create() per turn, capped at MAX_TOOL_TURNS.
    assert client.messages.create.call_count == MAX_TOOL_TURNS
    assert isinstance(out["answer"], str)


def test_tool_error_does_not_crash_loop():
    twak, skills, bridge = _deps()
    twak.price.side_effect = RuntimeError("twak down")
    client = MagicMock()
    client.messages.create.side_effect = [
        _resp("tool_use", [_tool_block("t1", "get_price", {"token": "X"})]),
        _resp("end_turn", [_text_block("Couldn't fetch the price.")]),
    ]
    out = run_read_loop("price?", twak=twak, skills=skills, bridge=bridge, client=client)
    assert out["answer"] == "Couldn't fetch the price."
    assert out["grounded"] is True  # a tool was attempted
