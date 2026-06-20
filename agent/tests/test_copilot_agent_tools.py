import json
from unittest.mock import MagicMock
from agent.copilot_agent import TOOLS, execute_tool


def _deps():
    twak = MagicMock()
    skills = MagicMock()
    bridge = MagicMock()
    return twak, skills, bridge


def test_tools_have_unique_names_and_schemas():
    names = [t["name"] for t in TOOLS]
    assert names == sorted(set(names))  # unique
    for t in TOOLS:
        assert t["name"] and t["description"]
        assert t["input_schema"]["type"] == "object"


def test_get_agent_state_summarises_bridge():
    twak, skills, bridge = _deps()
    bridge.latest_ledger.return_value = {"cumulative_pnl_usd": 1.5, "current_drawdown_pct": 0.02}
    bridge.get_config.return_value = {"halted": False, "trading_mode": "mainnet", "strategy_name": "contrarian"}
    bridge.recent_decisions.return_value = [
        {"regime": "CHOP", "risk_verdict": "BLOCK", "timestamp_ms": 1, "risk_reason": "chop gate"},
    ]
    out = json.loads(execute_tool("get_agent_state", {}, twak=twak, skills=skills, bridge=bridge))
    assert out["pnl_usd"] == 1.5
    assert out["drawdown_pct"] == 0.02
    assert out["halted"] is False
    assert out["recent_decisions"][0]["regime"] == "CHOP"


def test_get_price_calls_twak():
    twak, skills, bridge = _deps()
    twak.price.return_value = {"price": 2.31}
    out = json.loads(execute_tool("get_price", {"token": "CAKE"}, twak=twak, skills=skills, bridge=bridge))
    twak.price.assert_called_once_with("CAKE", "bsc")
    assert out["price"] == 2.31


def test_check_token_risk_calls_twak():
    twak, skills, bridge = _deps()
    twak.risk.return_value = {"score": "low"}
    out = json.loads(execute_tool("check_token_risk", {"asset_id": "c60"}, twak=twak, skills=skills, bridge=bridge))
    twak.risk.assert_called_once_with("c60")
    assert out["score"] == "low"


def test_get_wallet_calls_portfolio():
    twak, skills, bridge = _deps()
    twak.portfolio.return_value = {"total_usd": 18.0}
    out = json.loads(execute_tool("get_wallet", {}, twak=twak, skills=skills, bridge=bridge))
    assert out["total_usd"] == 18.0


def test_get_trending_calls_twak():
    twak, skills, bridge = _deps()
    twak.trending.return_value = [{"symbol": "CAKE"}]
    out = json.loads(execute_tool("get_trending", {"limit": 3}, twak=twak, skills=skills, bridge=bridge))
    twak.trending.assert_called_once_with(category="bnb", limit=3)
    assert out[0]["symbol"] == "CAKE"


def test_cmc_market_skill_runs_top_candidate():
    twak, skills, bridge = _deps()
    skills.enabled = True
    skills.find_skill.return_value = [{"uniqueName": "ohlcv_latest"}]
    skills.execute_skill.return_value = {"data": {"price": 1}}
    out = json.loads(execute_tool("cmc_market_skill", {"query": "eth ohlcv"}, twak=twak, skills=skills, bridge=bridge))
    skills.execute_skill.assert_called_once()
    assert out["data"]["price"] == 1


def test_cmc_market_skill_offline_returns_marker():
    twak, skills, bridge = _deps()
    skills.enabled = False
    out = json.loads(execute_tool("cmc_market_skill", {"query": "x"}, twak=twak, skills=skills, bridge=bridge))
    assert out["status"] == "offline"


def test_unknown_tool_returns_error_marker():
    twak, skills, bridge = _deps()
    out = json.loads(execute_tool("nope", {}, twak=twak, skills=skills, bridge=bridge))
    assert "error" in out


def test_tool_exception_is_caught_not_raised():
    twak, skills, bridge = _deps()
    twak.price.side_effect = RuntimeError("twak down")
    out = json.loads(execute_tool("get_price", {"token": "X"}, twak=twak, skills=skills, bridge=bridge))
    assert "error" in out and "twak down" in out["error"]
