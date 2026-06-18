"""
Command worker — drains queued agent_commands from Convex and executes them.
Called by POST /twak/drain after each main cycle (safe: off the scored path).
Each call processes ONE command (the oldest queued one) to keep latency bounded.
"""
from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from agent.twak_cli import TwakCli

if TYPE_CHECKING:
    from agent.convex_bridge import ConvexBridge

log = logging.getLogger(__name__)


def run_one_command(bridge: "ConvexBridge") -> bool:
    """Fetch and execute the oldest queued command. Returns True if one ran."""
    cmd = bridge.pop_queued_command()
    if cmd is None:
        return False
    cmd_id   = cmd["_id"]
    cmd_type = cmd.get("command_type", "")
    params   = json.loads(cmd.get("params", "{}"))
    bridge.update_command_status(cmd_id, "running")
    try:
        result = _dispatch(cmd_type, params)
        bridge.update_command_status(cmd_id, "done", result=json.dumps(result))
        bridge.append_audit(
            event_type="operator_command",
            payload=json.dumps({"command_type": cmd_type, "params": params, "result": result}),
            severity="info",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        err = str(exc)[:400]
        log.error("command_worker: %s failed: %s", cmd_type, err)
        bridge.update_command_status(cmd_id, "failed", error=err)
        bridge.append_audit(
            event_type="operator_command",
            payload=json.dumps({"command_type": cmd_type, "params": params, "error": err}),
            severity="error",
        )
        return True


def _dispatch(cmd_type: str, params: dict) -> dict:
    try:
        twak = TwakCli()
        if cmd_type == "automate_add":
            return twak.automate_add(
                params["from_token"], params["to_token"], params["amount"],
                chain=params.get("chain"),
                interval=params.get("interval"),
                price=params.get("price"),
                condition=params.get("condition", "below"),
                max_runs=params.get("max_runs"),
            )
        if cmd_type == "automate_pause":
            return twak.automate_pause(params["id"])
        if cmd_type == "automate_resume":
            return twak.automate_resume(params["id"])
        if cmd_type == "automate_delete":
            return twak.automate_delete(params["id"])
        if cmd_type == "alert_create":
            return twak.alert_create(
                params["token"], params["chain"],
                above=params.get("above"), below=params.get("below"),
            )
        if cmd_type == "alert_delete":
            return twak.alert_delete(params["id"])
        if cmd_type == "erc20_approve":
            return twak.erc20_approve(params["token"], params["spender"], params["amount"])
        if cmd_type == "erc20_revoke":
            return twak.erc20_revoke(params["token"], params["spender"])
        if cmd_type == "x402_request":
            return twak.x402_request(
                params["url"], params["max_payment"],
                method=params.get("method", "POST"),
                body=params.get("body"),
            )
        if cmd_type == "withdraw":
            to_addr = params.get("to_address", "")
            amount  = float(params.get("amount", 0))
            token   = params.get("token", "USDT")
            # Validate before calling TWAK — irreversible on-chain tx
            if not re.match(r"^0x[0-9a-fA-F]{40}$", to_addr):
                raise ValueError(f"invalid BSC address: {to_addr!r}")
            if amount <= 0:
                raise ValueError(f"amount must be > 0, got {amount}")
            result = twak.transfer(to_addr, amount, token, chain="bsc")
            tx_hash = result.get("hash") or result.get("txHash") or ""
            return {
                "tx_hash": tx_hash,
                "explorer": result.get("explorer", ""),
                "amount": amount,
                "token": token,
                "to": to_addr,
            }
        raise ValueError(f"unknown command_type: {cmd_type!r}")
    except KeyError as e:
        raise ValueError(f"command {cmd_type!r} missing required param: {e}") from e
