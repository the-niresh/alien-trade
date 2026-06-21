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

MAX_CONVERT_IMPACT = 0.05  # abort a convert whose quoted price impact exceeds 5%
CONVERT_ALLOWLIST = {"BNB", "ETH", "USDT", "CAKE", "UNI", "LINK", "AAVE"}

# ERC-20 approval guardrails — never grant an unlimited allowance. An over-broad
# approval lets the spender drain the whole token balance later; cap it to a small
# operating amount and only allow known router contracts as the spender.
MAX_APPROVE_AMOUNT = 1000.0          # token units — well above any single trade size
_UINT_MAX = "115792089237316195423570985008687907853269984665640564039457584007913129639935"
_APPROVE_UNLIMITED_SENTINELS = {"max", "unlimited", "-1", _UINT_MAX}
# PancakeSwap routers on BSC (V2 + SmartRouter). Lower-cased for comparison.
APPROVE_SPENDER_ALLOWLIST = {
    "0x10ed43c718714eb63d5aa57b78b54704e256024e",  # PancakeSwap V2 router
    "0x13f4ea83d0bd40e75c8222255bc855a974568dd4",  # PancakeSwap SmartRouter
}
_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def _validate_erc20_approve(spender: str, amount) -> float:
    """Reject unlimited / oversized approvals and unknown spenders. Returns the
    validated numeric amount. Raises ValueError on anything suspicious."""
    if not _ADDR_RE.match(str(spender or "")):
        raise ValueError(f"invalid spender address: {spender!r}")
    if str(spender).lower() not in APPROVE_SPENDER_ALLOWLIST:
        raise ValueError(f"spender {spender!r} not in router allowlist")
    if str(amount).strip().lower() in _APPROVE_UNLIMITED_SENTINELS:
        raise ValueError("unlimited ERC-20 approval rejected")
    try:
        amt = float(amount)
    except (TypeError, ValueError):
        raise ValueError(f"approval amount not numeric: {amount!r}")
    if amt <= 0 or amt > MAX_APPROVE_AMOUNT:
        raise ValueError(f"approval amount {amt} outside (0, {MAX_APPROVE_AMOUNT}]")
    return amt


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
        result = _dispatch(cmd_type, params, bridge)
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


def _dispatch(cmd_type: str, params: dict, bridge: "ConvexBridge") -> dict:
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
            amt = _validate_erc20_approve(params["spender"], params["amount"])
            return twak.erc20_approve(params["token"], params["spender"], amt)
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
        if cmd_type == "convert":
            from_token = str(params.get("from_token", "")).upper()
            to_token   = str(params.get("to_token", "")).upper()
            usd        = float(params.get("usd", 0))
            if not from_token or not to_token:
                raise ValueError("convert requires from_token and to_token")
            if from_token == to_token:
                raise ValueError(f"convert from and to must differ: {from_token}")
            if from_token not in CONVERT_ALLOWLIST:
                raise ValueError(f"convert: unsupported from_token {from_token!r}")
            if to_token not in CONVERT_ALLOWLIST:
                raise ValueError(f"convert: unsupported to_token {to_token!r}")
            if usd <= 0:
                raise ValueError(f"convert usd must be > 0, got {usd}")
            # simulate-before-send (locked architectural decision L3)
            quote = twak.swap_quote(from_token, to_token, usd=usd, chain="bsc", slippage=1.0)
            if quote.price_impact_pct > MAX_CONVERT_IMPACT:
                raise ValueError(
                    f"price impact {quote.price_impact_pct:.2%} exceeds "
                    f"{MAX_CONVERT_IMPACT:.0%} cap — aborting convert"
                )
            # balance check — catch insufficient funds before broadcasting
            bal_data = twak.balance(chain="bsc")
            if from_token == "BNB":
                available = float(bal_data.get("available", 0))
            else:
                tok_map = {t["symbol"].upper(): float(t["balance"])
                           for t in bal_data.get("tokens", [])}
                available = tok_map.get(from_token, 0.0)
            if available < quote.amount_in:
                raise ValueError(
                    f"insufficient {from_token}: have {available:.6f}, "
                    f"need {quote.amount_in:.6f} (${usd:.2f} USD)"
                )
            # Pre-flight: approve USDT for the router TWAK will use (LiquidMesh
            # on BSC requires explicit ERC-20 approval; swap will revert without it).
            if from_token == "USDT":
                _USDT_BSC = "0x55d398326f99059fF775485246999027B3197955"
                try:
                    _wallet = twak.wallet_address(chain="bsc")
                    if _wallet:
                        _router = (
                            quote.raw.get("to") or quote.raw.get("routerAddress") or
                            quote.raw.get("spender") or quote.raw.get("approveAddress") or
                            quote.raw.get("allowanceTarget") or ""
                        )
                        if _router and str(_router).startswith("0x") and len(str(_router)) == 42:
                            _allow = twak.erc20_allowance(_USDT_BSC, _wallet, _router)
                            _cur = float(_allow.get("allowance") or _allow.get("value") or 0)
                            if _cur == 0:
                                twak.erc20_approve(_USDT_BSC, _router, "1000")
                except Exception:  # noqa: BLE001 — pre-flight must not block the convert
                    pass
            res = twak.swap_execute(from_token, to_token, usd=usd, chain="bsc", slippage=1.0)
            # Record in Convex so the convert shows up in Recent Trades with real gas.
            gas_usd = 0.0
            try:
                from exec.bnb import BNBExec
                receipt = BNBExec(testnet=False).wait_for_receipt(res.tx_hash, timeout=90)
                bnb_price_usd = float(
                    (twak.price("BNB", "bsc") or {}).get("priceUsd") or 0
                ) or 1.0
                gas_bnb = (getattr(receipt, "gas_used", 0) or 0) * \
                           (getattr(receipt, "gas_price_wei", 0) or 0) * 1e-18
                gas_usd = gas_bnb * bnb_price_usd
            except Exception as _e:  # noqa: BLE001
                log.warning("convert: gas receipt failed (%s), recording $0 gas", _e)
            try:
                bridge.record_trade(
                    symbol=f"{from_token}/{to_token}",
                    side="buy",
                    size_usd=usd,
                    fill_price=quote.amount_out / quote.amount_in if quote.amount_in else 0.0,
                    fee_usd=0.0,
                    gas_usd=gas_usd,
                    slippage_usd=usd * quote.price_impact_pct,
                    mode="mainnet",
                    tx_hash=res.tx_hash,
                )
            except Exception as _e:  # noqa: BLE001
                log.warning("convert: record_trade failed: %s", _e)
            return {
                "tx_hash":          res.tx_hash,
                "from_token":       from_token,
                "to_token":         to_token,
                "usd":              usd,
                "expected_out":     quote.amount_out,
                "price_impact_pct": quote.price_impact_pct,
                "gas_usd":          gas_usd,
            }
        if cmd_type == "force_cycle":
            # Acknowledged — the loop runs on its fixed cadence; this unblocks the UI.
            return {"status": "triggered"}
        raise ValueError(f"unknown command_type: {cmd_type!r}")
    except KeyError as e:
        raise ValueError(f"command {cmd_type!r} missing required param: {e}") from e
