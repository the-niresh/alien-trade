"""
LangGraph supervisor (Orchestrator) - the single chat/command entry to the Tier-1
advisory team. Off the hot path (locked decisions #1/#6): it OBSERVES the
deterministic loop via Convex and REACTS; it never makes or wraps a trade decision.

This is the 2-node scaffold (AGENT_TEAM_PLAN §8: "start with 2 nodes - Co-pilot +
Historian, prove graph + channel, then grow"). Routing through the single entry:

    user question              -> co_pilot   (history-flavoured -> historian)
    observed event (e.g.       -> historian  (record / look up prior lessons;
      position_closed)                         the Reflector/Researcher nodes land
                                               in the grow phase)

Every node emits exactly one AgentEvent to the Activity Channel (the glass cockpit).
A user "Pause Agents" control short-circuits the Tier-1 nodes here - Tier-0 trading
is a different process and is unaffected (failure-matrix §9.3).

8.10: Each call is budgeted (MAX_HOPS) to prevent runaway token spend. The Researcher
dedupes within a 90-min window per symbol; the Reflector dedupes per cycle_id so
Trigger.dev retries can't write duplicate lessons.

8.14: Every node wraps its body in _emit_failure on exception rather than swallowing
silently - the operator sees failures in the cockpit without having to grep logs.
"""
from __future__ import annotations

import operator
import time
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
_RESEARCH_KINDS = ("research_tick", "schedule")
_CLOSE_KINDS = ("position_closed", "trade_closed")

# Hard ceiling on hops per supervisor call (8.10 - prevents runaway token spend).
MAX_HOPS: int = 4
# Research tick dedupe: skip if the same symbol was researched within this window.
_RESEARCH_DEDUPE_SECS: float = 90 * 60  # 90 minutes


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
    confidence: float              # researcher forecast confidence (0..1)
    lesson: str                    # reflector output
    from_reflection: bool          # set by reflector → historian confirms the write
    events: Annotated[list, operator.add]   # AgentEvents emitted this run
    hops: Annotated[int, operator.add]      # hop counter; each node adds 1


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
        # 8.10 in-memory dedupe state (resets on server restart - acceptable for the
        # live window; a fresh research after restart is a feature, not a bug).
        self._last_research_ts: dict = {}      # symbol -> float (epoch seconds)
        self._reflected_cycle_ids: set = set() # cycle_ids already reflected this session

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
            "paused": control.agents_paused, "events": [], "hops": 0,
        }
        return self.graph.invoke(state)

    # ── nodes ────────────────────────────────────────────────────────────────────

    def _co_pilot_node(self, state: SupervisorState) -> dict:
        if state.get("paused"):
            return self._paused(COPILOT, state)
        if state.get("hops", 0) >= MAX_HOPS:
            return self._budget_exceeded(COPILOT, state)
        try:
            out = self._copilot.ask(state.get("input", ""))
        except Exception as exc:  # noqa: BLE001
            evt = self._emit_failure(state, COPILOT, exc)
            return {"route": "co_pilot", "answer": "", "events": [evt], "hops": 1}
        answer = out.get("answer", "")
        evt = self._emit(AgentEvent(
            agent=COPILOT, kind=KIND_ANALYSIS, headline=_one_line(answer),
            cycle_id=state.get("cycle_id"),
            detail={"grounded": out.get("grounded"),
                    "skills": out.get("skills", []),
                    "n_sources": len(out.get("sources", []))},
        ))
        return {"route": "co_pilot", "answer": answer, "events": [evt], "hops": 1}

    def _researcher_node(self, state: SupervisorState) -> dict:
        if state.get("paused"):
            return self._paused(RESEARCHER, state)
        if state.get("hops", 0) >= MAX_HOPS:
            return self._budget_exceeded(RESEARCHER, state)
        symbol = state.get("symbol") or "ETH"
        # 8.10 research-tick dedupe: skip if the same symbol ran within 90 min
        now = time.time()
        last_ts = self._last_research_ts.get(symbol, 0.0)
        if now - last_ts < _RESEARCH_DEDUPE_SECS:
            age_min = round((now - last_ts) / 60, 1)
            evt = self._emit(AgentEvent(
                agent=RESEARCHER, kind=KIND_CONTROL,
                headline=(f"Research tick skipped for {symbol} - ran {age_min} min ago "
                          f"(dedupe window: 90 min)"),
                cycle_id=state.get("cycle_id"),
                detail={"symbol": symbol, "last_research_age_min": age_min,
                        "dedupe_window_min": 90},
            ))
            return {"route": "researcher", "digests": [], "confidence": 1.0,
                    "events": [evt], "hops": 1}
        # 8.15: get all eligible symbols from Convex config, filter per-symbol dedupe
        symbols_to_research = self._filter_dedupe(symbol, state)

        digests = []
        confidence = 1.0
        try:
            sup = self.sb.research(symbol)  # primary symbol for compat
            if len(symbols_to_research) > 1:
                digests = sup.run_cycle(symbols=symbols_to_research)
            else:
                history = sup._fetch_history()
                digests = sup.run_cycle(history=history)
                from agent.secondbrain.research import confidence_from_history
                confidence = confidence_from_history(history)
                self._write_forecast(symbol, confidence, history)
            # Mark all processed symbols as recently researched
            now = time.time()
            for sym in symbols_to_research:
                self._last_research_ts[sym] = now
        except Exception as exc:  # noqa: BLE001
            evt_fail = self._emit_failure(state, RESEARCHER, exc)
            return {"route": "researcher", "digests": [], "confidence": 1.0,
                    "events": [evt_fail], "hops": 1}
        headline = (f"AutoResearch produced {len(digests)} digest(s), confidence={confidence:.2f}"
                    if digests else "AutoResearch cycle produced no digests")
        evts = [self._emit(AgentEvent(
            agent=RESEARCHER, kind=KIND_OBSERVATION, headline=_one_line(headline),
            cycle_id=state.get("cycle_id"),
            detail={"n_digests": len(digests), "confidence": round(confidence, 4),
                    "questions": [getattr(d, "question", "") for d in digests[:3]]},
            refs=[getattr(d, "id", "") for d in digests[:3]],
        ))]
        # 8.13: emit a visible observation for each low-confidence digest
        for d in digests:
            if getattr(d, "low_confidence", False):
                evts.append(self._emit(AgentEvent(
                    agent=RESEARCHER, kind=KIND_OBSERVATION,
                    headline=f"Researcher: low-confidence digest flagged for {symbol}",
                    cycle_id=state.get("cycle_id"),
                    detail={"digest_id": getattr(d, "id", ""),
                            "question": getattr(d, "question", "")[:100]},
                    refs=[getattr(d, "id", "")],
                )))
        return {"route": "researcher", "digests": [getattr(d, "id", "") for d in digests],
                "confidence": confidence, "events": evts, "hops": 1}

    def _reflector_node(self, state: SupervisorState) -> dict:
        if state.get("paused"):
            return self._paused(REFLECTOR, state)
        if state.get("hops", 0) >= MAX_HOPS:
            return self._budget_exceeded(REFLECTOR, state)
        p = state.get("payload") or {}
        cycle_id = state.get("cycle_id") or p.get("cycle_id", "")
        # 8.10 reflection dedupe: idempotent on cycle_id so Trigger.dev retries
        # don't write duplicate lessons for the same trade close event.
        if cycle_id and cycle_id in self._reflected_cycle_ids:
            evt = self._emit(AgentEvent(
                agent=REFLECTOR, kind=KIND_CONTROL,
                headline=(f"Reflection skipped - already reflected for "
                          f"cycle {cycle_id[-12:]}"),
                cycle_id=cycle_id,
                detail={"cycle_id": cycle_id, "reason": "duplicate cycle_id"},
            ))
            return {"route": "reflector", "lesson": "", "from_reflection": False,
                    "events": [evt], "hops": 1}
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
            if cycle_id:
                self._reflected_cycle_ids.add(cycle_id)
        except Exception as exc:  # noqa: BLE001
            evt_fail = self._emit_failure(state, REFLECTOR, exc)
            return {"route": "reflector", "lesson": "", "from_reflection": True,
                    "events": [evt_fail], "hops": 1}
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
                "events": [evt], "hops": 1}

    def _historian_node(self, state: SupervisorState) -> dict:
        if state.get("paused"):
            return self._paused(HISTORIAN, state)
        if state.get("hops", 0) >= MAX_HOPS:
            return self._budget_exceeded(HISTORIAN, state)
        # Write-confirmation path: the Reflector just stored a lesson → acknowledge it.
        if state.get("from_reflection"):
            lesson = state.get("lesson", "")
            analysis = (f"Lesson recorded to memory: {lesson[:140]}" if lesson
                        else "Reflection received; no lesson to record.")
            evt = self._emit(AgentEvent(
                agent=HISTORIAN, kind=KIND_ANALYSIS, headline=_one_line(analysis),
                cycle_id=state.get("cycle_id"), detail={"wrote_reflection": bool(lesson)},
            ))
            return {"route": "historian", "analysis": analysis, "events": [evt], "hops": 1}
        query_text = state.get("input") or state.get("symbol") or ""
        hits = []
        try:
            hits = self.sb.vector.query(query_text, top_k=5, kind=KIND_REFLECTION)
        except Exception as exc:  # noqa: BLE001
            evt_fail = self._emit_failure(state, HISTORIAN, exc)
            return {"route": "historian", "analysis": "No prior lessons (vector error).",
                    "events": [evt_fail], "hops": 1}
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
        return {"route": "historian", "analysis": analysis, "events": [evt], "hops": 1}

    # ── helpers ────────────────────────────────────────────────────────────────

    def _filter_dedupe(self, primary: str, state: SupervisorState) -> list[str]:
        """8.15: build the per-symbol research list, filtering out symbols whose
        last research run was within the 90-min dedupe window. The primary symbol
        (loop's active token) is always included first. Falls back to [primary]
        when the bridge is unavailable."""
        now = time.time()
        try:
            allowlist = (self.bridge.get_token_allowlist()
                         if self.bridge is not None else [primary])
        except Exception:  # noqa: BLE001
            allowlist = [primary]
        # Deduplicate: skip symbols already researched within the window
        result = []
        for sym in ([primary] + [s for s in allowlist if s != primary]):
            last = self._last_research_ts.get(sym, 0.0)
            if now - last >= _RESEARCH_DEDUPE_SECS:
                result.append(sym)
        return result or [primary]   # always research at least the primary

    def _write_forecast(self, symbol: str, confidence: float, history: list) -> None:
        """Write the Researcher's deterministic confidence to forecast_state.
        Failure is swallowed - Researcher is Tier-1 (failure-matrix §9.3)."""
        if self.bridge is None:
            return
        try:
            from agent.graph.contracts import DEFAULT_FORECAST_TTL_MS, ForecastState
            from backtest.regime import detect_regime
            reason = (f"regime={detect_regime(history).value}" if history
                      else "no history available")
            fs = ForecastState(symbol=symbol, confidence=confidence,
                               reason=reason, ttl_ms=DEFAULT_FORECAST_TTL_MS)
            self.bridge.set_forecast_state(fs)
        except Exception:  # noqa: BLE001
            pass

    def _paused(self, agent: str, state: SupervisorState) -> dict:
        evt = self._emit(AgentEvent(
            agent=agent, kind=KIND_CONTROL,
            headline=f"{agent} skipped - agents paused by user",
            cycle_id=state.get("cycle_id"), detail={"paused": True},
        ))
        return {"route": agent, "events": [evt], "hops": 1}

    def _budget_exceeded(self, agent_name: str, state: SupervisorState) -> dict:
        """8.10: Hard cap on hops per supervisor call - prevents runaway token spend."""
        evt = self._emit(AgentEvent(
            agent=agent_name, kind=KIND_CONTROL,
            headline=f"{agent_name}: budget exceeded ({MAX_HOPS} hops) - skipping",
            cycle_id=state.get("cycle_id"),
            detail={"hops": state.get("hops", 0), "max_hops": MAX_HOPS},
        ))
        return {"route": agent_name, "events": [evt], "hops": 1}

    def _emit_failure(self, state: SupervisorState, agent_name: str,
                      error: Exception) -> AgentEvent:
        """8.14: Replace bare except-pass with a visible failure event in the channel.
        The operator sees failures in the cockpit without having to grep logs."""
        return self._emit(AgentEvent(
            agent=agent_name, kind=KIND_CONTROL,
            headline=f"{agent_name} failed: {type(error).__name__}",
            cycle_id=state.get("cycle_id"),
            detail={"error": str(error)[:200], "error_type": type(error).__name__},
        ))

    def _emit(self, event: AgentEvent) -> AgentEvent:
        """Write one trace to the channel. A channel-write failure is swallowed -
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

    ap = argparse.ArgumentParser(description="LangGraph supervisor - one message")
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
