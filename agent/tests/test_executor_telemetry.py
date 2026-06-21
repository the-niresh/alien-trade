"""
Tests that OnchainExecutor.execute records BNB_SDK sponsor telemetry.
Uses __new__ to bypass __init__ dependency injection.
"""
import time
import pytest
from unittest.mock import MagicMock, patch
from agent import sponsor_telemetry as st


def setup_function():
    st._sink = None
    while not st._queue.empty():
        try:
            st._queue.get_nowait()
        except Exception:
            break


def _drain():
    time.sleep(0.4)


def _make_executor():
    from agent.executor import OnchainExecutor
    e = OnchainExecutor.__new__(OnchainExecutor)
    e._seen = {}
    e._dry_run = False
    e._wallet = "0xtest"

    # minimal risk config
    risk = MagicMock()
    risk.max_slippage_pct = 0.05
    e._risk = risk

    # cost model that returns zeros
    cost = MagicMock()
    cost.return_value = (0.0, 0.0, 0.0)
    e._cost = cost

    # BNB executor mock
    bnb = MagicMock()
    sim = MagicMock()
    sim.success = True
    sim.error = ""
    bnb.simulate_swap.return_value = sim
    bnb.build_unsigned_tx.return_value = MagicMock()
    bnb.broadcast.return_value = "0xtxhash123"
    receipt = MagicMock()
    receipt.status = 1
    receipt.gasUsed = 50000
    bnb.wait_for_receipt.return_value = receipt
    bnb.gas_price_gwei.return_value = 5.0
    bnb.tokens = {"USDT": "0xusdt", "WBNB": "0xwbnb"}
    e._bnb = bnb

    # signer mock
    signer = MagicMock()
    signed = MagicMock()
    signed.raw_hex = "0xdeadbeef"
    signer.sign_transaction.return_value = signed
    e._signer = signer

    return e


def test_bnb_sdk_recorded_on_successful_execute():
    """OnchainExecutor.execute records sponsor=BNB_SDK with tx_hash."""
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)

    e = _make_executor()

    order = MagicMock()
    order.symbol = "ETH"
    order.side = "buy"
    order.size_usd = 4.0

    bar = MagicMock()
    bar.close = 1000.0

    cap = MagicMock()
    cap.allowed = True

    with patch.object(e, "_order_to_swap", return_value=MagicMock()), \
         patch("agent.executor._expected_slippage_pct", return_value=0.001), \
         patch("agent.executor.check_slippage", return_value=cap), \
         patch("agent.executor._gas_usd_from_receipt", return_value=0.01):
        result = e.execute(order, bar, "key-success-123")

    _drain()

    assert result is not None
    bnb_calls = [c for c in received if c.sponsor == "BNB_SDK"]
    assert len(bnb_calls) == 1
    assert bnb_calls[0].tx_hash == "0xtxhash123"
    assert bnb_calls[0].kind == "sign"
    assert bnb_calls[0].status == "ok"


def test_bnb_sdk_records_error_on_broadcast_failure():
    """OnchainExecutor.execute records status=error when broadcast fails."""
    received: list[st.SponsorCall] = []
    st.set_sink(received.append)

    e = _make_executor()
    e._bnb.broadcast.side_effect = RuntimeError("broadcast failed")

    order = MagicMock()
    order.symbol = "ETH"
    order.side = "buy"
    order.size_usd = 4.0

    bar = MagicMock()
    bar.close = 1000.0

    cap = MagicMock()
    cap.allowed = True

    with patch.object(e, "_order_to_swap", return_value=MagicMock()), \
         patch("agent.executor._expected_slippage_pct", return_value=0.001), \
         patch("agent.executor.check_slippage", return_value=cap):
        result = e.execute(order, bar, "key-fail-456")

    _drain()

    assert result is not None  # returns FAILED report, does not raise
    from agent.executor import FAILED
    assert result.status == FAILED

    bnb_calls = [c for c in received if c.sponsor == "BNB_SDK"]
    assert len(bnb_calls) == 1
    assert bnb_calls[0].status == "error"
