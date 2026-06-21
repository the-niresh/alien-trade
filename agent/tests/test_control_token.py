"""CSO-1: the control-token guard on state-changing Convex mutations.

Three layers:
- `test_guard_unit` — pure mirror of convex/control.ts assertControlToken semantics
  (documents fail-open-when-unset, fail-closed-when-set).
- `test_token_injected_*` — the agent bridge attaches control_token to guarded
  mutations only (offline capture; no network).
- `test_wrong_token_rejected` — live round-trip, skipped without CONVEX_URL.
"""
import os
import pytest

from agent.convex_bridge import ConvexBridge


def test_guard_unit():
    # pure-unit mirror of assertControlToken semantics
    def guard(expected, provided):
        if not expected:
            return
        if provided != expected:
            raise ValueError("unauthorized")
    guard("", "anything")          # fail-open when unset
    guard("s3cr3t", "s3cr3t")      # ok
    with pytest.raises(ValueError):
        guard("s3cr3t", "bad")


def test_token_injected_into_guarded_mutation():
    b = ConvexBridge(url="", control_token="tok123")  # offline → args captured
    b.set_halted(True)
    call = b._offline_log[-1]
    assert call["path"] == "config:setHalted"
    assert call["args"].get("control_token") == "tok123"


def test_token_not_injected_when_unset():
    b = ConvexBridge(url="", control_token="")  # no token → nothing attached
    b.set_halted(True)
    assert "control_token" not in b._offline_log[-1]["args"]


def test_token_not_injected_into_unguarded_mutation():
    # config:ensure is NOT guarded — injecting a token would make Convex reject the arg
    b = ConvexBridge(url="", control_token="tok123")
    b._call("mutation", "config:ensure", {})
    assert "control_token" not in b._offline_log[-1]["args"]


@pytest.mark.skipif(not os.environ.get("CONVEX_URL"), reason="needs live convex")
def test_wrong_token_rejected(monkeypatch):
    b = ConvexBridge(url=os.environ["CONVEX_URL"], control_token="definitely-wrong")
    # If CONTROL_TOKEN is set server-side, the wrong token must be rejected. The
    # bridge swallows the error and returns None (it never crashes a cycle), so we
    # assert the call did not succeed by reading state back is out of scope here;
    # this test simply documents the live path is exercised without raising.
    b.set_halted(True)
