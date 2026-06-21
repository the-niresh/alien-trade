import pytest
from agent.agents.spec import validate_agent_spec, AGENT_TOOL_NAMES


def test_defaults_mode_paper_and_keeps_known_tools():
    rec = validate_agent_spec({
        "name": "CAKE-Watcher", "goal": "watch CAKE funding",
        "allowed_tools": ["get_price", "cmc_market_skill"],
    })
    assert rec["mode"] == "paper"
    assert rec["allowed_tools"] == ["get_price", "cmc_market_skill"]
    assert rec["notify_policy"] == {"webpush": True, "severity_min": "info"}


def test_rejects_unknown_tool():
    with pytest.raises(ValueError, match="unknown tool"):
        validate_agent_spec({"name": "x", "goal": "g", "allowed_tools": ["drain_wallet"]})


def test_requires_name_and_goal():
    with pytest.raises(ValueError):
        validate_agent_spec({"name": "", "goal": "g"})


def test_known_tool_names_cover_copilot_tools():
    assert {"get_price", "get_trending", "check_token_risk",
            "cmc_market_skill", "get_agent_state"} <= AGENT_TOOL_NAMES
