"""Run one user-spawned Agent as a bounded tool-loop. Off the trade hot path.
Never raises: any failure is captured as an error run + agent_events row
(no-silent-failure, per the 2026-06-20 outage)."""
from __future__ import annotations

import time

from agent.copilot_agent import run_read_loop


# What each Agent Tool is for — injected into the prompt so the level-1 researcher
# routes correctly instead of guessing from the bare tool name.
_TOOL_JOBS: dict[str, str] = {
    "get_wallet":       "live self-custody holdings + USD values",
    "get_price":        "live USD spot price for one token",
    "get_trending":     "ranked BNB-chain movers",
    "check_token_risk": "rug / contract safety for one token",
    "cmc_market_skill": "deep market data (OHLCV, funding/OI, sentiment, on-chain flow)",
    "get_agent_state":  "the main trader's PnL / drawdown / regime / last decisions",
    "create_agent":     "spawn a sub-agent (rarely needed)",
}


def _goal_prompt(rec: dict) -> str:
    names = rec.get("allowed_tools") or []
    if names:
        lines = "\n".join(
            f"  - {n:<16} {_TOOL_JOBS.get(n, 'specialized tool')}"
            for n in names
        )
    else:
        lines = "  (no tools granted)"
    return (
        f"You are '{rec['name']}', a specialized research agent in the Alien-Trade mesh.\n"
        f"Your tools and what each is for:\n{lines}\n"
        f"You are specialized at research with these tools: call them as many times and in "
        f"whatever combination it takes to ground your answer in live data — never guess when "
        f"a tool can tell you.\n"
        f"Your mandate: {rec['goal']}.\n"
        f"Work the mandate, then hand up a fast, decisive synthesis:\n"
        f"  (1) what you found (grounded in tool output),\n"
        f"  (2) your call in one line — act / wait / avoid, or the specific alert,\n"
        f"  (3) whether the operator should be notified now.\n"
        f"Be token-frugal: stop calling tools the moment you can answer. No padding."
    )


def run_agent(rec: dict, *, twak, skills, bridge, client, loop_fn=run_read_loop) -> dict:
    started = int(time.time() * 1000)
    agent_id = rec["_id"]
    try:
        result = loop_fn(_goal_prompt(rec), twak=twak, skills=skills, bridge=bridge,
                         client=client, max_turns=8)
        summary = result.get("answer", "")[:600]
        tool_calls = [{"tool": s["tool"], "args": str(s.get("args", {}))[:200]}
                      for s in result.get("sources", [])]
        ok = True
    except Exception as exc:  # no-silent-failure: capture, don't raise
        summary = f"agent run failed: {exc}"[:600]
        tool_calls, ok = [], False

    ended = int(time.time() * 1000)
    bridge.call("mutation", "agentRuns:record", {
        "agent_id": agent_id, "started_ms": started, "ended_ms": ended,
        "ok": ok, "summary": summary, "tool_calls": tool_calls,
    })
    bridge.append_event(
        agent=rec["name"],
        kind="analysis" if ok else "control",
        headline=summary.split("\n")[0][:120],
        detail="{}",
        refs=[],
    )
    return {"ok": ok, "summary": summary, "tool_calls": tool_calls}
