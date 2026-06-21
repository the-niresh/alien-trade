import json
import time
import pytest
from unittest.mock import patch, MagicMock
from agent import sponsor_telemetry as st
from agent.twak_cli import TwakCli, TwakError


def setup_function():
    st._sink = None
    while not st._queue.empty():
        try:
            st._queue.get_nowait()
        except Exception:
            break


def _drain():
    time.sleep(0.4)


def _proc(stdout: str = "{}", returncode: int = 0, stderr: str = ""):
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    m.stderr = stderr
    return m


def test_x402_classified_as_cmc():
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    cli = TwakCli(binary="/fake/twak")
    with patch("subprocess.run", return_value=_proc("{}")):
        cli._run("x402", "request", "https://example.com")
    _drain()
    assert len(received) == 1
    assert received[0].sponsor == "CMC"
    assert received[0].kind == "data"


def test_swap_classified_as_twak():
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    cli = TwakCli(binary="/fake/twak")
    result_json = json.dumps({"txHash": "0xabc"})
    with patch("subprocess.run", return_value=_proc(result_json)):
        cli._run("swap", "execute", "--amount", "4")
    _drain()
    assert received[0].sponsor == "TWAK"
    assert received[0].kind == "execute"
    assert received[0].tx_hash == "0xabc"


def test_error_records_status_and_reraises():
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    cli = TwakCli(binary="/fake/twak")
    with patch("subprocess.run", return_value=_proc("", returncode=1, stderr="bad")):
        with pytest.raises(TwakError):
            cli._run("swap", "execute")
    _drain()
    assert len(received) == 1
    assert received[0].status == "error"


def test_return_value_unchanged():
    """Wrapping must not alter the return value."""
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    cli = TwakCli(binary="/fake/twak")
    data = {"balance": "1.5"}
    with patch("subprocess.run", return_value=_proc(json.dumps(data))):
        result = cli._run("wallet", "balance", "--chain", "bsc")
    assert result == data
    _drain()
    assert received[0].sponsor == "TWAK"
    assert received[0].kind == "balance"
