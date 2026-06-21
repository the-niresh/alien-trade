"""Tests for TwakCli extensions — all TWAK calls are mocked."""
from __future__ import annotations
import json
from unittest.mock import patch, MagicMock
import pytest
from agent.twak_cli import TwakCli, TwakError


@pytest.fixture()
def cli():
    c = TwakCli()
    c._bin = "/fake/twak"
    return c


def _mock_run(return_value: dict):
    return patch.object(TwakCli, "_run", return_value=return_value)


def test_portfolio_returns_dict(cli):
    with _mock_run({"chains": [{"name": "bsc", "tokens": []}], "totalUsd": 5.0}):
        result = cli.portfolio()
    assert isinstance(result, dict)
    assert "totalUsd" in result


def test_price_returns_dict(cli):
    with _mock_run({"price": 3000.0, "symbol": "ETH"}):
        result = cli.price("ETH")
    assert result["price"] == 3000.0


def test_risk_returns_dict(cli):
    with _mock_run({"isRug": False, "riskScore": 10}):
        result = cli.risk("c60")
    assert result["riskScore"] == 10


def test_trending_returns_list(cli):
    with _mock_run([{"symbol": "CAKE", "priceChange": 5.2}]):
        result = cli.trending()
    assert isinstance(result, list)


def test_automate_list_returns_list(cli):
    with _mock_run([{"id": "auto-1", "status": "active"}]):
        result = cli.automate_list()
    assert result[0]["id"] == "auto-1"


def test_automate_add_dca(cli):
    with _mock_run({"id": "auto-2", "type": "dca"}):
        result = cli.automate_add("USDT", "ETH", "10", interval="1d")
    assert result["id"] == "auto-2"


def test_automate_add_requires_interval_or_price(cli):
    with pytest.raises(ValueError, match="interval or price"):
        cli.automate_add("USDT", "ETH", "10")


def test_alert_create_requires_above_or_below(cli):
    with pytest.raises(ValueError, match="above or below"):
        cli.alert_create("ETH", "bsc")


def test_erc20_allowance_returns_dict(cli):
    with _mock_run({"allowance": "1000000"}):
        result = cli.erc20_allowance("c60_t0xabc", "0xowner", "0xspender")
    assert "allowance" in result


def test_x402_quote_returns_dict(cli):
    with _mock_run({"routes": [{"chain": "bsc", "amount": "10000"}]}):
        result = cli.x402_quote("https://example.com/api")
    assert "routes" in result


def test_bsc_token_registry_addresses_are_valid():
    """Every registry address must be a 40-hex-char checksummed BSC address.
    Guards against truncation typos that would silently break swaps on a token
    and (via the sustained-failure watchdog) auto-halt the live agent."""
    import re
    from agent.twak_cli import _BSC_TOKEN_REGISTRY

    addr_re = re.compile(r"^0x[0-9a-fA-F]{40}$")
    bad = {sym: a for sym, a in _BSC_TOKEN_REGISTRY.items() if not addr_re.match(a)}
    assert not bad, f"invalid BSC token addresses: {bad}"
