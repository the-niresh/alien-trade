"""
LangGraph supervisor (Orchestrator) — the single chat/command entry to the Tier-1
advisory team. Off the hot path (locked decisions #1/#6): it OBSERVES the
deterministic loop via Convex and REACTS; it never makes or wraps a trade decision.

This is the 2-node scaffold (AGENT_TEAM_PLAN §8: "start with 2 nodes — Co-pilot +
Historian, prove graph + channel, then grow"). Routing through the single entry:

    user question              -> co_pilot   (history-flavoured -> historian)
    observed event (e.g.       -> historian  (record / look up prior lessons;
      position_closed)                         the Reflector/Researcher nodes land
                                               in the grow phase)

Every node emits exactly one AgentEvent to the Activity Channel (the glass cockpit).
A user "Pause Agents" control short-circuits the Tier-1 nodes here — Tier-0 trading
is a different process and is unaffected (failure-matrix §9.3).
"""
from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from agent.graph.contracts import (
    COPILOT,
    HISTORIAN,
    KIND_ANALYSIS,
    KIND_CONTROL,
    KIND_HANDOFF,
    KIND_OBSERVATION,
    REFLECTOR,
    RESEARCHER,
    AgentControl,
    AgentEvent,
)
from agent.secondbrain.schema import KIND_REFLECTION

_HISTORY_HINTS = (
    "lost before", "last time", " past ", "history", "learned",
    "have we", "previously", "mistake", "seen this before",
)
# Event kinds the supervisor reacts to (off the hot path — it observes Convex).
_RESEARCH_KINDS = ("research_tick", "schedule")
_CLOSE_KINDS = ("position_closed", "trade_closed")


class SupervisorState(TypedDict, total=False):
    input: str
    kind: str                      # "user" | an event kind ("position_closed", ...)
    symbol: str
    cycle_id: Optional[str]
    payload: dict                  # structured event data (trade close → reflect args)
    paused: bool
    route: str
    answer: str                    # co-pilot output
    analysis: str                  # historian output
    digests: list                  # researcher output (digest ids)
    lesson: str                    # reflector output
    from_reflection: bool          # set by reflector → historian confirms the write
    events: Annotated[list, operator.add]   # AgentEvents emitted this run


def route(state: SupervisorState) -> str:
    """Single entry → the right node (AGENT_TEAM_PLAN §4 routing):
      user question      → co_pilot   (history-flavoured → historian)
      schedule tick       → researcher
      trade-close event   → reflector  (→ historian.write via a graph edge)
      any other event     → historian"""
    kind = state.get("kind", "user")
    if kind == "user":
        q = (state.get("input") or "").lower()
        return "historian" if any(h in q for h in _HISTORY_HINTS) else "co_pilot"
    if kind in _RESEARCH_KINDS:
        return "researcher"
    if kind in _CLOSE_KINDS:
        return "reflector"
    return "historian"


class Supervisor:
    """Wraps a compiled StateGraph over the existing Second-Brain agents."""

    def __init__(self, sb, bridge=None):
        self.sb = sb                       # SecondBrain (vector, llm, copilot, skills)
        self.bridge = bridge
        self._copilot = sb.copilot()
        self.graph = self._build()

    def _build(self):
        g = StateGraph(SupervisorState)
        g.add_node("co_pilot", self._co_pilot_node)
        g.add_node("historian", self._historian_node)
        g.add_node("researcher", self._researcher_node)
        g.add_node("reflector", self._reflector_node)
        g.add_conditional_edges(START, route, {
            "co_pilot": "co_pilot", "historian": "historian",
            "researcher": "researcher", "reflector": "reflector",
        })
        g.add_edge("co_pilot", END)
        g.add_edge("researcher", END)
        g.add_edge("reflector", "historian")   # reflect → historian.write (confirm)
        g.add_edge("historian", END)
        return g.compile()

    # ── single entry ───────────────────────────────────────────────────────────

    def handle(self, text: str, *, kind: str = "user", symbol: str = "",
               cycle_id: Optional[str] = None, payload: Optional[dict] = None) -> dict:
        """Route one message/event through the graph and return the final state
        (answer/analysis + the events emitted). `payload` carries structured event
        data (e.g. a trade close → the reflect() args). Reads the pause control once."""
        control = self.bridge.get_agent_control() if self.bridge is not None else AgentControl()
        state: SupervisorState = {
            "input": text, "kind": kind, "symbol": symbol or "",
            "cycle_id": cycle_id, "payload": payload or {},
            "paused": control.agents_paused, "events": [],
        }
        return self.graph.invoke(state)

    # ── nodes ────────────────────────────────────────────────────────────────────

    def _co_pilot_node(self, state: SupervisorState) -> dict:
        if state.get("paused"):
            return self._paused(COPILOT, state)
        out = self._copilot.ask(state.get("input", ""))
        answer = out.get("answer", "")
        evt = self._emit(AgentEvent(
            agent=COPILOT, kind=KIND_ANALYSIS, headline=_one_line(answer),
            cycle_id=state.get("cycle_id"),
            detail={"grounded": out.get("grounded"),
                    "skills": out.get("skills", []),
                    "n_sources": len(out.get("sources", []))},
        ))
        return {"route": "co_pilot", "answer": answer, "events": [evt]}

    def _researcher_node(self, state: SupervisorState) -> dict:
        if state.get("paused"):
            return self._paused(RESEARCHER, state)
        digests = []
        try:
            sup = self.sb.research(state.get("symbol") or "ETH")
            digests = sup.run_cycle()
        except Exception:  # noqa: BLE001 — advisory; a failed cycle never halts trading
            digests = []
        headline = (f"AutoResearch produced {len(digests)} digest(s)"
                    if digests else "AutoResearch cycle produced no digests")
        evt = self._emit(AgentEvent(
            agent=RESEARCHER, kind=KIND_OBSERVATION, headline=_one_line(headline),
            cycle_id=state.get("cycle_id"),
            detail={"n_digests": len(digests),
                    "questions": [getattr(d, "question", "") for d in digests[:3]]},
            refs=[getattr(d, "id", "") for d in digests[:3]],
        ))
        return {"route": "researcher", "digests": [getattr(d, "id", "") for d in digests],
                "events": [evt]}

    def _reflector_node(self, state: SupervisorState) -> dict:
        if state.get("paused"):
            return self._paused(REFLECTOR, state)
        p = state.get("payload") or {}
        cycle_id = state.get("cycle_id") or p.get("cycle_id", "")
        lesson, ref_id = "", ""
        try:
            r = self.sb.reflection_writer.reflect(
                cycle_id=cycle_id, trade_id=p.get("trade_id"),
                timestamp_ms=p.get("timestamp_ms", 0), regime=p.get("regime", ""),
                side=p.get("side", ""), signals=p.get("signals", {}),
                realized_pnl=p.get("realized_pnl", 0.0),
            )
            if r is not None:
                lesson = getattr(r, "lesson", "") or ""
                ref_id = f"refl-{cycle_id}"
        except Exception:  # noqa: BLE001 — advisory; reflection failing never halts trading
            lesson = ""
        evt = self._emit(AgentEvent(
            agent=REFLECTOR, kind=KIND_HANDOFF,
            headline=_one_line(f"Reflected on closed trade -> {lesson}" if lesson
                               else "Reflected on closed trade (no lesson stored)"),
            cycle_id=cycle_id,
            detail={"realized_pnl": p.get("realized_pnl"), "regime": p.get("regime"),
                    "side": p.get("side")},
            refs=[ref_id] if ref_id else [],
        ))
        # Hand to the Historian to confirm the lesson now lives in memory.
        return {"route": "reflector", "lesson": lesson, "from_reflection": True,
                "events": [evt]}

    def _historian_node(self, state: SupervisorState) -> dict:
        if state.get("paused"):
            return self._paused(HISTORIAN, state)
        # Write-confirmation path: the Reflector just stored a lesson → acknowledge it.
        if state.get("from_reflection"):
            lesson = state.get("lesson", "")
            analysis = (f"Lesson recorded to memory: {lesson[:140]}" if lesson
                        else "Reflection received; no lesson to record.")
            evt = self._emit(AgentEvent(
                agent=HISTORIAN, kind=KIND_ANALYSIS, headline=_one_line(analysis),
                cycle_id=state.get("cycle_id"), detail={"wrote_reflection": bool(lesson)},
            ))
            return {"route": "historian", "analysis": analysis, "events": [evt]}
        query_text = state.get("input") or state.get("symbol") or ""
        hits = []
        try:
            hits = self.sb.vector.query(query_text, top_k=5, kind=KIND_REFLECTION)
        except Exception:  # noqa: BLE001 — advisory; an empty history is fine
            hits = []
        if hits:
            analysis = (f"{len(hits)} past lesson(s) on this setup. "
                        f"Most similar: {hits[0].text[:140]}")
        else:
            analysis = "No prior lessons recorded for this setup."
        evt = self._emit(AgentEvent(
            agent=HISTORIAN, kind=KIND_ANALYSIS, headline=_one_line(analysis),
            cycle_id=state.get("cycle_id"),
            detail={"n_hits": len(hits), "symbol": state.get("symbol", "")},
            refs=[h.id for h in hits[:3]],
        ))
        return {"route": "historian", "analysis": analysis, "events": [evt]}

    # ── helpers ────────────────────────────────────────────────────────────────

    def _paused(self, agent: str, state: SupervisorState) -> dict:
        evt = self._emit(AgentEvent(
            agent=agent, kind=KIND_CONTROL,
            headline=f"{agent} skipped - agents paused by user",
            cycle_id=state.get("cycle_id"), detail={"paused": True},
        ))
        return {"route": agent, "events": [evt]}

    def _emit(self, event: AgentEvent) -> AgentEvent:
        """Write one trace to the channel. A channel-write failure is swallowed —
        observability must never break a node (failure-matrix)."""
        if self.bridge is not None:
            try:
                self.bridge.emit_event(event)
            except Exception:  # noqa: BLE001
                pass
        return event


def _one_line(text: str, n: int = 120) -> str:
    s = " ".join((text or "").split())
    return s if len(s) <= n else s[: n - 3] + "..."


def main(argv: Optional[list[str]] = None) -> None:
    import argparse
    import sys
    from pathlib import Path

    from dotenv import load_dotenv

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    load_dotenv(Path(__file__).resolve().parents[2] / ".env.local")

    ap = argparse.ArgumentParser(description="LangGraph supervisor — one message")
    ap.add_argument("message", nargs="+", help="user question or event text")
    ap.add_argument("--kind", default="user", help="user | position_closed | ...")
    ap.add_argument("--symbol", default="ETH")
    args = ap.parse_args(argv)

    from agent.convex_bridge import ConvexBridge
    from agent.secondbrain.builder import build_second_brain

    import os
    sb = build_second_brain()
    bridge = ConvexBridge(url=os.environ.get("CONVEX_URL", ""))
    sup = Supervisor(sb, bridge=bridge)
    out = sup.handle(" ".join(args.message), kind=args.kind, symbol=args.symbol)
    print(f"\n  route   : {out.get('route')}")
    if out.get("answer"):
        print(f"  answer  : {out['answer']}")
    if out.get("analysis"):
        print(f"  history : {out['analysis']}")
    print(f"  events  : {len(out.get('events', []))} emitted to the channel")
    sb.close()


if __name__ == "__main__":
    main()
