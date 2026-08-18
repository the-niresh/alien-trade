"""
Wallet Manager Agent - LLM with live tools that watches the real wallet.

Runs as a one-shot tool-use loop (Claude Haiku for cost). Called automatically
by the sustained-failure watchdog and optionally from the hourly digest.

Responsibilities:
  • Detect real-vs-ledger position mismatch (swap executed but no tx hash)
  • Diagnose why swaps are failing (low USDT, TWAK error, price impact)
  • Recommend concrete action: sell ETH back to USDT, halt, top up, wait
  • Optionally execute the recommended action (sell only, never a new buy)

CLI:
    python -m agent.wallet_manager              # diagnose + report via Telegram
    python -m agent.wallet_manager --stdout     # print instead of Telegram
    python -m agent.wallet_manager --fix        # diagnose + auto-execute sell if mismatch
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from typing import Any, Optional

log = logging.getLogger(__name__)

# ── Tool schemas ──────────────────────────────────────────────────────────────

TOOLS: list[dict] = [
    {
        "name": "get_real_wallet",
        "description": (
            "Fetch the live on-chain wallet balances via TWAK. "
            "Returns BNB (gas), USDT, and any token holdings with USD values."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_paper_ledger",
        "description": (
            "Read the agent's internal paper ledger: what the agent THINKS it holds. "
            "Returns units held, avg entry price, paper equity, and cumulative PnL."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_recent_failures",
        "description": (
            "Read the last N audit-log rows for 'error' events - swap failures, "
            "TWAK errors, and network problems. Helps diagnose why swaps are failing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "How many rows to return (default 20)",
                    "default": 20,
                }
            },
        },
    },
    {
        "name": "get_agent_config",
        "description": (
            "Read the current agent config: mode, strategy, position size, halted flag."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "sell_token_to_usdt",
        "description": (
            "Execute a real on-chain swap: sell the specified token back to USDT. "
            "Use this to realign a real ETH position when the ledger thinks we're flat. "
            "ONLY call this when you have confirmed real tokens in wallet that the ledger "
            "does not know about. Returns the tx hash or an error."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Token to sell (e.g. ETH, CAKE)",
                },
                "amount_usd": {
                    "type": "number",
                    "description": "USD value to sell (based on current price)",
                },
            },
            "required": ["symbol", "amount_usd"],
        },
    },
    {
        "name": "set_agent_halted",
        "description": (
            "Set the agent's kill switch. halted=true stops all trading; "
            "halted=false resumes. Use when the wallet is in a bad state and "
            "manual intervention is needed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "halted": {"type": "boolean"},
                "reason": {"type": "string"},
            },
            "required": ["halted"],
        },
    },
]

SYSTEM_PROMPT = """\
You are the Wallet Manager for an autonomous BSC trading agent (Alien-Trade).
Your job is to keep the agent's wallet healthy and aligned with its internal ledger.

Key facts:
- The agent trades ETH on BSC via TWAK (Trust Wallet Agent Kit) spot swaps
- Capital: a small wallet (~$5 USDT + BNB for gas)
- The paper ledger tracks what the agent THINKS it holds (may differ from reality)
- TWAK swaps sometimes execute on-chain but return no tx hash - the agent then
  thinks the trade failed but real tokens are sitting in the wallet

Your workflow:
1. Call get_real_wallet and get_paper_ledger in parallel to see both states
2. Call get_recent_failures to understand why swaps may be failing
3. Detect mismatches: real tokens held but ledger says flat, or USDT lower than expected
4. Decide the right action and explain clearly
5. If there is a mismatch (real ETH but ledger flat): call sell_token_to_usdt to realign
   - this gives the agent clean USDT capital to trade with
6. If USDT is critically low (< $0.10): recommend the operator top up; set_agent_halted(true)
7. If swap failures are a TWAK/network error: set_agent_halted(true) and explain

Keep your final recommendation concise: what's wrong, what you did, what the operator should do.
Never invent data - only act on what the tools return."""


# ── Tool executor ─────────────────────────────────────────────────────────────

class WalletManagerTools:
    def __init__(
        self,
        bridge,
        twak,
        symbol: str = "ETH",
        chain: str = "bsc",
        mode: str = "mainnet",
        allow_sell: bool = False,
    ):
        self._bridge = bridge
        self._twak = twak
        self._symbol = symbol
        self._chain = chain
        self._mode = mode
        self._allow_sell = allow_sell

    def run(self, name: str, inputs: dict) -> Any:
        if name == "get_real_wallet":
            return self._get_real_wallet()
        if name == "get_paper_ledger":
            return self._get_paper_ledger()
        if name == "get_recent_failures":
            return self._get_recent_failures(inputs.get("limit", 20))
        if name == "get_agent_config":
            return self._get_agent_config()
        if name == "sell_token_to_usdt":
            return self._sell_token_to_usdt(
                inputs["symbol"], float(inputs["amount_usd"])
            )
        if name == "set_agent_halted":
            return self._set_agent_halted(inputs["halted"], inputs.get("reason", ""))
        raise ValueError(f"unknown tool: {name}")

    def _get_real_wallet(self) -> dict:
        try:
            bal = self._twak.balance(self._chain)
            tokens = {t["symbol"]: float(t["balance"]) for t in bal.get("tokens", [])}
            bnb = float(bal.get("available", 0))
            result = {
                "address": bal.get("address", ""),
                "bnb": bnb,
                "tokens": tokens,
            }
            # Enrich with USD prices
            try:
                eth = tokens.get("ETH", 0.0)
                usdt = tokens.get("USDT", 0.0)
                eth_price = float(self._twak.price("ETH", self._chain).get("priceUsd") or 0)
                bnb_price = float(self._twak.price("BNB", self._chain).get("priceUsd") or 650)
                result["eth_price_usd"] = round(eth_price, 2)
                result["bnb_price_usd"] = round(bnb_price, 2)
                result["usdt_usd"] = round(usdt, 4)
                result["eth_usd"] = round(eth * eth_price, 4)
                result["bnb_usd"] = round(bnb * bnb_price, 4)
                result["total_usd"] = round(usdt + eth * eth_price + bnb * bnb_price, 4)
            except Exception:
                pass
            return result
        except Exception as e:
            return {"error": str(e)}

    def _get_paper_ledger(self) -> dict:
        try:
            row = self._bridge.latest_ledger() or {}
            cfg = self._bridge.get_config() or {}
            rs = self._bridge._call("query", "riskState:get", {}) or {}
            return {
                "paper_equity_usd": row.get("peak_equity_usd"),
                "cumulative_pnl_usd": row.get("cumulative_pnl_usd"),
                "open_exposure_usd": rs.get("open_exposure_usd"),
                "current_drawdown_pct": rs.get("current_drawdown_pct"),
                "halted": cfg.get("halted", False),
                "mode": cfg.get("trading_mode", "unknown"),
                "strategy": cfg.get("strategy", "unknown"),
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_recent_failures(self, limit: int) -> list[dict]:
        try:
            rows = self._bridge._call("query", "audit:list", {"limit": limit}) or []
            return [r for r in rows if r.get("severity") in ("error", "warn")]
        except Exception as e:
            return [{"error": str(e)}]

    def _get_agent_config(self) -> dict:
        try:
            return self._bridge.get_config() or {}
        except Exception as e:
            return {"error": str(e)}

    def _sell_token_to_usdt(self, symbol: str, amount_usd: float) -> dict:
        if not self._allow_sell:
            return {"error": "sell not enabled - run with --fix flag or allow_sell=True"}
        if self._mode == "paper":
            return {"simulated": True, "symbol": symbol, "amount_usd": amount_usd,
                    "note": "paper mode - no real swap"}
        try:
            quote = self._twak.swap_quote(
                symbol, "USDT", usd=amount_usd,
                chain=self._chain, slippage=5.0,
            )
            result = self._twak.swap_execute(
                symbol, "USDT", usd=amount_usd,
                chain=self._chain, slippage=5.0,
            )
            return {
                "tx_hash": result.tx_hash,
                "symbol": symbol,
                "amount_usd": amount_usd,
                "price_impact_pct": quote.price_impact_pct,
                "ok": bool(result.tx_hash),
            }
        except Exception as e:
            return {"error": str(e)}

    def _set_agent_halted(self, halted: bool, reason: str) -> dict:
        try:
            self._bridge.set_halted(halted)
            return {"ok": True, "halted": halted, "reason": reason}
        except Exception as e:
            return {"error": str(e)}


# ── Agent loop ────────────────────────────────────────────────────────────────

def run_wallet_check(
    bridge=None,
    notifier=None,
    symbol: str = "ETH",
    mode: str = "mainnet",
    allow_sell: bool = False,
    stdout_only: bool = False,
) -> str:
    """Run one wallet-manager tool-use loop. Returns the agent's final text."""
    import anthropic
    from agent.config import AgentConfig
    from agent.twak_cli import TwakCli

    cfg = AgentConfig()
    if bridge is None:
        from agent.convex_bridge import ConvexBridge
        bridge = ConvexBridge(
            url=cfg.convex_url,
            control_token=os.environ.get("CONTROL_TOKEN", ""),
        )

    twak = TwakCli(chain="bsc")
    tools_runner = WalletManagerTools(
        bridge=bridge, twak=twak,
        symbol=symbol, chain="bsc", mode=mode,
        allow_sell=allow_sell,
    )

    client = anthropic.Anthropic()
    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"The trading agent is experiencing problems. Symbol: {symbol}, "
                f"mode: {mode}. Please diagnose the wallet state and take "
                f"appropriate action."
            ),
        }
    ]

    final_text = ""
    for _ in range(10):   # max 10 tool-use rounds (Haiku is fast + cheap)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Accumulate text
        for block in resp.content:
            if block.type == "text":
                final_text = block.text

        if resp.stop_reason == "end_turn":
            break

        # Process tool calls
        if resp.stop_reason != "tool_use":
            break

        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            try:
                result = tools_runner.run(block.name, block.input)
            except Exception as e:
                result = {"error": str(e)}
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user", "content": tool_results})

    # Emit an AgentEvent so the cockpit Agents tab shows live activity
    try:
        from agent.graph.contracts import AgentEvent, KIND_ANALYSIS, WALLET_MANAGER
        headline = (final_text[:120] + "…") if len(final_text) > 120 else final_text
        bridge.emit_event(AgentEvent(
            agent=WALLET_MANAGER,
            kind=KIND_ANALYSIS,
            headline=headline or "Wallet check complete.",
        ))
    except Exception:
        pass

    # Deliver the report
    report = f"WALLET MANAGER:\n{final_text}" if final_text else "Wallet manager: no diagnosis produced."

    if stdout_only:
        print(report)
    elif notifier is not None:
        notifier.send(report)
    else:
        try:
            from agent.notify import TelegramBot
            bot = TelegramBot()
            bot.send(report)
        except Exception:
            print(report)

    return final_text


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Alien-Trade wallet manager agent")
    ap.add_argument("--stdout", action="store_true", help="Print instead of Telegram")
    ap.add_argument("--fix", action="store_true", help="Allow sell to realign position")
    ap.add_argument("--symbol", default="ETH")
    ap.add_argument("--mode", default=None)
    args = ap.parse_args(argv)

    from agent.config import AgentConfig
    cfg = AgentConfig()
    mode = args.mode or cfg.mode

    run_wallet_check(
        symbol=args.symbol,
        mode=mode,
        allow_sell=args.fix,
        stdout_only=args.stdout,
    )


if __name__ == "__main__":
    main()
