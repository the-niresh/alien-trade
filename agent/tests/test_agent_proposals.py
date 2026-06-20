import json
import pytest
from agent.agents import proposals


class Bridge:
    def __init__(self): self.calls = []
    def call(self, kind, path, args):
        self.calls.append((kind, path, args))
        return "appr1"


def test_propose_writes_pending_approval_and_no_swap():
    b = Bridge()
    out = proposals.propose_trade(b, "a1", command_type="twak_swap",
                                  params={"from": "USDT", "to": "CAKE", "amount": 4})
    assert out == "appr1"
    assert len(b.calls) == 1
    kind, path, args = b.calls[0]
    assert (kind, path) == ("mutation", "approvals:propose")
    assert args["agent_id"] == "a1"
    assert all("command" not in p.lower() and "twak" not in p.lower()
               for _, p, _ in b.calls)


def test_paper_simulate_fill_has_no_tx():
    fill = proposals.simulate_fill("CAKE", "buy", usd=4.0, price=2.0)
    assert fill["qty"] == 2.0 and fill["tx_hash"] is None and fill["mode"] == "paper"


def test_resolve_contract_enqueues_one_command_on_approve_only():
    queued = []
    def resolve(status, payload):
        if status == "approved":
            c = json.loads(payload)
            queued.append({"command_type": c["command_type"],
                           "params": json.dumps(c["params"]), "status": "queued"})
    payload = json.dumps({"command_type": "twak_swap",
                          "params": {"from": "USDT", "to": "CAKE", "amount": 4}})
    resolve("rejected", payload); assert queued == []
    resolve("approved", payload); assert len(queued) == 1
    assert queued[0]["status"] == "queued" and queued[0]["command_type"] == "twak_swap"
