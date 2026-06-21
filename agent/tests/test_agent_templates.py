from agent.agents.templates import market_watcher


def test_market_watcher_is_valid_and_read_only():
    spec = market_watcher("CAKE", "funding flips negative")
    assert spec["mode"] == "paper"
    assert spec["allowed_tools"] == ["get_price", "cmc_market_skill"]
    assert spec["trigger"] == {"kind": "schedule", "spec": "1h"}
    assert "CAKE" in spec["goal"] and "funding flips negative" in spec["goal"]
