import time
import pytest
from agent import sponsor_telemetry as st


def _drain(timeout: float = 0.4) -> None:
    """Give the daemon thread time to drain the queue."""
    time.sleep(timeout)


def setup_function():
    """Reset module state between tests."""
    st._sink = None
    while not st._queue.empty():
        try:
            st._queue.get_nowait()
        except Exception:
            break


def test_noop_when_no_sink():
    """record_sponsor_call is silent when no sink registered."""
    st.set_sink(None)
    # Should not raise
    st.record_sponsor_call("TWAK", "swap", "swap execute", "ok", 120)
    _drain()


def test_call_reaches_sink():
    """Recorded call is forwarded to the registered sink."""
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    st.record_sponsor_call("CMC", "data", "price feed", "ok", 55, cost_usd=0.001)
    _drain()
    assert len(received) == 1
    assert received[0].sponsor == "CMC"
    assert received[0].kind == "data"
    assert received[0].cost_usd == 0.001
    assert received[0].status == "ok"


def test_sink_exception_is_swallowed():
    """A sink that raises must not crash the daemon or caller."""
    def bad_sink(_call):
        raise RuntimeError("sink blew up")

    st.set_sink(bad_sink)
    st.record_sponsor_call("TWAK", "balance", "wallet balance", "ok", 30)
    _drain()

    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    st.record_sponsor_call("BNB_SDK", "sign", "onchain execute", "ok", 200)
    _drain()
    assert len(received) == 1


def test_as_row_fields():
    call = st.SponsorCall(
        sponsor="TWAK", kind="swap", endpoint="swap execute",
        status="ok", latency_ms=100, tx_hash="0xabc", ts_ms=1000000,
    )
    row = call.as_row()
    assert row["sponsor"] == "TWAK"
    assert row["tx_hash"] == "0xabc"
    assert row["latency_ms"] == 100
    assert row["ts_ms"] == 1000000


def test_error_status():
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)
    st.record_sponsor_call("TWAK", "swap", "swap execute", "error", 50, detail='{"err":"timeout"}')
    _drain()
    assert received[0].status == "error"
    assert received[0].detail == '{"err":"timeout"}'
