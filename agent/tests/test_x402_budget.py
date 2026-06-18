from unittest.mock import MagicMock, patch


def test_x402_gated_call_uses_twak_when_enabled():
    from agent.x402_provider import x402_gated_call
    twak = MagicMock()
    twak.x402_request.return_value = {"data": {"value": 42}, "statusCode": 200}
    with patch("agent.x402_provider._get_twak", return_value=twak):
        result = x402_gated_call(
            url="https://cmc.example.com/skill",
            max_payment="10000",
            body={"symbol": "ETH"},
            enabled=True,
            budget_usd=1.0,
            spent_usd=0.0,
        )
    assert result["data"]["value"] == 42
    twak.x402_request.assert_called_once()


def test_x402_gated_call_skips_when_disabled():
    from agent.x402_provider import x402_gated_call
    twak = MagicMock()
    result = x402_gated_call(
        url="https://cmc.example.com/skill",
        max_payment="10000",
        body={},
        enabled=False,
        budget_usd=1.0,
        spent_usd=0.0,
    )
    assert result is None
    twak.x402_request.assert_not_called()


def test_x402_gated_call_skips_when_budget_exceeded():
    from agent.x402_provider import x402_gated_call
    twak = MagicMock()
    result = x402_gated_call(
        url="https://cmc.example.com/skill",
        max_payment="10000",
        body={},
        enabled=True,
        budget_usd=0.5,
        spent_usd=0.6,   # over budget
    )
    assert result is None
