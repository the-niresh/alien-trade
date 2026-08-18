"""Trade proposals from live-mode Agents. An Agent NEVER swaps directly:
it writes a pending approval. The human approves in the PWA (control-token
gated), which enqueues the real command. Paper mode simulates with no tx."""
from __future__ import annotations

import json


def propose_trade(bridge, agent_id, *, command_type: str, params: dict):
    """Write a pending approval_request. Returns its id. Does NOT execute."""
    payload = json.dumps({"command_type": command_type, "params": params})
    return bridge.call("mutation", "approvals:propose",
                       {"agent_id": agent_id, "payload": payload})


def simulate_fill(symbol: str, side: str, *, usd: float, price: float) -> dict:
    """Paper fill - no on-chain tx."""
    qty = round(usd / price, 8) if price else 0.0
    return {"symbol": symbol, "side": side, "usd": usd, "price": price,
            "qty": qty, "tx_hash": None, "mode": "paper"}
