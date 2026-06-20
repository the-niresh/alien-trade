"""
Level-1 tool handoff chains + Level-2 Agent→Agent delegation.

Level-1 — chain programs: the orchestrator drives the LangGraph supervisor
through a named sequence of nodes (Researcher → Historian → CoPilot), threading
each node's output as the next node's input. Every hop emits one AgentEvent;
the combined trace becomes agent_runs.tool_calls[] in Convex — the Neural Mesh
"who-called-whom" graph.

Level-2 — Agent→Agent delegation: a spawned Agent may include other agent IDs
(format "agent:<_id>") in its allowed_tools. The orchestrator resolves the ID,
checks the delegation path for cycles, enforces MAX_DELEGATION_DEPTH, and runs
the sub-agent via the standard runner. Each delegation is one bounded hop.

Governed by locked decisions #1 (LLM off hot path) and #6 (failure = log,
never halt trading). Both levels cap hops (MAX_HOPS via supervisor), fail
gracefully (degrade chain on error, never raise), and emit visible events.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Level-2 delegation depth cap — keeps fan-out from exploding token spend.
MAX_DELEGATION_DEPTH: int = 2

# ── Level-1 chain definitions ─────────────────────────────────────────────────


@dataclass(frozen=True)
class ChainStep:
    """One hop in a Level-1 handoff chain."""
    tool_name: str        # symbolic label (written to tool_calls[] trace)
    supervisor_kind: str  # kind routed into supervisor.handle()


# Supervisor state key that carries the useful text output for each node.
_OUTPUT_KEYS: dict[str, str] = {
    "researcher": "answer",
    "historian":  "analysis",
    "reflector":  "lesson",
    "copilot":    "answer",
}

# Named chains — two canonical patterns from the spec (§5.1).
CHAINS: dict[str, list[ChainStep]] = {
    # "Is this a setup we should take?" — Researcher gathers data, Historian
    # checks for past losses, CoPilot synthesises a one-paragraph call.
    "setup_scorer": [
        ChainStep("researcher", "schedule"),
        ChainStep("historian",  "user"),
        ChainStep("copilot",    "user"),
    ],
    # "Learn from what just happened" — Reflector extracts a lesson,
    # Historian stores + confirms it reached long-term memory.
    "learn_from_trade": [
        ChainStep("reflector", "position_closed"),
        ChainStep("historian",  "user"),
    ],
}


def run_chain(
    chain_name: str,
    *,
    supervisor,
    symbol: str = "",
    goal: str = "",
    cycle_id: Optional[str] = None,
) -> dict:
    """Level-1: execute a named handoff chain through the LangGraph supervisor.

    Returns:
        {ok, chain, tool_calls[], events[], combined{}, summary}

    A failing step degrades (that step's output = empty string) but the chain
    continues — failure-matrix §9.3: Tier-1 never halts trading.
    """
    steps = CHAINS.get(chain_name)
    if not steps:
        return {
            "ok": False,
            "error": f"unknown chain: {chain_name!r}",
            "chain": chain_name,
            "tool_calls": [],
            "events": [],
            "combined": {},
            "summary": "",
        }

    text = goal or symbol
    tool_calls: list[dict] = []
    all_events: list = []
    combined: dict[str, str] = {}

    for step in steps:
        try:
            state = supervisor.handle(
                text,
                kind=step.supervisor_kind,
                symbol=symbol,
                cycle_id=cycle_id or "",
            )
            events = state.get("events", [])
            all_events.extend(events)

            out_key = _OUTPUT_KEYS.get(step.tool_name, "answer")
            step_summary = (state.get(out_key) or "").strip()[:200]
            tool_calls.append({"tool": step.tool_name, "summary": step_summary})
            combined[step.tool_name] = step_summary

            # Thread this step's output as input to the next step.
            if step_summary:
                text = step_summary
        except Exception as exc:  # noqa: BLE001 — degrade, never raise
            err_msg = f"{type(exc).__name__}: {exc}"[:200]
            tool_calls.append({"tool": step.tool_name, "error": err_msg})
            # text stays unchanged — next step uses the previous good output.

    combined_summary = " → ".join(v for v in combined.values() if v)
    return {
        "ok": True,
        "chain": chain_name,
        "tool_calls": tool_calls,
        "events": all_events,
        "combined": combined,
        "summary": combined_summary[:600],
    }


# ── Level-2 Agent→Agent delegation ───────────────────────────────────────────


def delegate(
    from_agent_id: str,
    to_agent_id: str,
    *,
    registry,
    delegation_path: Optional[list[str]] = None,
    depth: int = 0,
    twak,
    skills,
    bridge,
    client,
    loop_fn=None,
) -> dict:
    """Level-2: run to_agent_id as a sub-agent of from_agent_id.

    Guards:
    - Cycle: rejects if to_agent_id already appears in the current delegation path.
    - Depth: rejects if depth >= MAX_DELEGATION_DEPTH.
    - Not-found: rejects if the delegated agent record does not exist.

    On success, runs the sub-agent via runner.run_agent() and returns its dict
    result (ok, summary, tool_calls). On rejection, returns ok=False with a
    descriptive error — never raises.
    """
    path = list(delegation_path or [from_agent_id])

    # Cycle guard.
    if to_agent_id in path:
        return {
            "ok": False,
            "error": f"delegation cycle: {path} → {to_agent_id}",
            "summary": "delegation rejected (cycle)",
            "tool_calls": [],
        }

    # Depth guard.
    if depth >= MAX_DELEGATION_DEPTH:
        return {
            "ok": False,
            "error": f"delegation depth cap ({MAX_DELEGATION_DEPTH}) reached",
            "summary": "delegation rejected (depth cap)",
            "tool_calls": [],
        }

    # Resolve the delegated agent record.
    to_rec = None
    try:
        to_rec = registry.get(to_agent_id)
    except Exception:  # noqa: BLE001
        pass
    if to_rec is None:
        return {
            "ok": False,
            "error": f"delegated agent {to_agent_id!r} not found",
            "summary": "delegation rejected (not found)",
            "tool_calls": [],
        }

    from agent.agents.runner import run_agent  # local import — avoids circular

    run_kwargs: dict = {"twak": twak, "skills": skills, "bridge": bridge, "client": client}
    if loop_fn is not None:
        run_kwargs["loop_fn"] = loop_fn

    return run_agent(to_rec, **run_kwargs)


# ── Delegation path helpers (used by tests + registry) ───────────────────────


def is_agent_tool(tool_name: str) -> bool:
    """True for Level-2 delegation tools ('agent:<id>' format)."""
    return tool_name.startswith("agent:")


def agent_id_from_tool(tool_name: str) -> str:
    """Extract the agent ID from an 'agent:<id>' tool string."""
    return tool_name[len("agent:"):]
