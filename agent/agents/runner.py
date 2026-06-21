"""Run one user-spawned Agent as a bounded tool-loop. Off the trade hot path.
Never raises: any failure is captured as an error run + agent_events row
(no-silent-failure, per the 2026-06-20 outage)."""
from __future__ import annotations

import time

from agent.copilot_agent import run_read_loop


def _goal_prompt(rec: dict) -> str:
    tools = ", ".join(rec.get("allowed_tools") or []) or "(no tools)"
    return (
        f"You are '{rec['name']}', an expert autonomous agent and orchestrator. "
        f"You have access to these Agent Tools: {tools}. "
        f"You may call any of them multiple times and in any combination to fully "
        f"accomplish your mandate — you are the decision-maker, not just a retrieval bot. "
        f"Your mandate: {rec['goal']}. "
        f"Reason carefully, use your tools to gather all relevant data, synthesize a "
        f"decision or finding, and report concisely: what you found, your conclusion, "
        f"and whether the user should be notified."
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
