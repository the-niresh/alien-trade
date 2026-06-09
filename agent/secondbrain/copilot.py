"""
Co-pilot — grounded Q&A over the Second Brain.

Answers "why this trade?", "what regime are we in?", "what did the last 2 years
teach us about this setup?" by retrieving from all three memory kinds
(reflections + institutional + research), folding in live Convex state (recent
decisions + ledger), and asking the LLM to answer **only from the supplied
context** with sources. Cheap by design: tier-routed (T1 default) and
cache-backed, so a repeated question is free.

Off the hot path — never touches the trade decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agent.secondbrain.llm import ClaudeClient
from agent.secondbrain.schema import (
    KIND_INSTITUTIONAL, KIND_REFLECTION, KIND_RESEARCH, MemoryHit,
)
from agent.secondbrain.vector import VectorStore
from agent.skills import (
    SkillContext,
    SkillHub,
    detect_symbol,
    params_from_schema,
    route_curated,
    skill_summary,
)

_COPILOT_SYSTEM = (
    "You are Alien-Trade's co-pilot. Answer the operator's question using ONLY the "
    "MEMORY and LIVE STATE provided. Be concise and specific; cite which memories "
    "support your answer. If the context doesn't cover it, say so plainly."
)


@dataclass
class CoPilot:
    vector: VectorStore
    llm: ClaudeClient
    bridge: Optional[object] = None
    # CMC Skill Hub (Tier-2 dynamic find_skill->execute). None/offline → the
    # co-pilot answers from memory + live state only (offline-first, unchanged).
    skills: Optional[SkillHub] = None

    def ask(self, question: str, *, tier: str = "T1", per_kind: int = 3) -> dict:
        hits = self._retrieve(question, per_kind)
        live = self._live_state()
        skill_lines = self._skill_evidence(question)
        prompt = self._build_prompt(question, hits, live, skill_lines)
        res = self.llm.complete(prompt, system=_COPILOT_SYSTEM, tier=tier, max_tokens=400)
        return {
            "question": question,
            "answer": res.text,
            "sources": [{"id": h.id, "kind": h.metadata.get("kind"),
                         "score": round(h.score, 3), "text": h.text} for h in hits],
            "skills": skill_lines,
            "grounded": bool(hits) or bool(live) or bool(skill_lines),
            "stub": res.stub,
        }

    # ── live CMC skills (Tier-2 dynamic discovery) ─────────────────────────────

    def _skill_evidence(self, question: str, *, top_k: int = 3, max_skills: int = 2) -> list[str]:
        """Live CMC skill reads for an open-ended question. Curated-first: if the
        question maps to pinned skills (known-good params), run those; only fall
        back to dynamic find_skill for the long tail (best-effort params, fragile).
        Guarded throughout — a skill failing is advisory, never breaks an answer
        (failure-matrix). Empty when offline or nothing usable comes back."""
        if self.skills is None or not self.skills.enabled:
            return []
        symbol = detect_symbol(question)

        # Tier 1 — curated (reliable). Reuse the hub's pinned param-builders.
        curated = route_curated(question)[:max_skills]
        if curated:
            ctx = SkillContext(symbol=symbol)
            out = []
            for key in curated:
                try:
                    brief = skill_summary(self.skills.run_curated(key, ctx), key)
                except Exception:  # noqa: BLE001 — advisory only
                    brief = ""
                if brief:
                    out.append(brief)
            if out:
                return out

        # Tier 2 — dynamic discovery for questions no curated skill covers.
        return self._dynamic_evidence(question, symbol, top_k=top_k, max_skills=max_skills)

    def _dynamic_evidence(self, question, symbol, *, top_k, max_skills) -> list[str]:
        out: list[str] = []
        for cand in self.skills.find_skill(question, top_k=top_k):
            if len(out) >= max_skills:
                break
            name = cand.get("uniqueName")
            if not name:
                continue
            try:
                params = params_from_schema(cand.get("inputSchema", {}), question, symbol)
                brief = skill_summary(self.skills.execute_skill(name, params), name)
            except Exception:  # noqa: BLE001 — advisory only
                brief = ""
            if brief:
                out.append(brief)
        return out

    # ── retrieval ────────────────────────────────────────────────────────────────

    def _retrieve(self, question: str, per_kind: int) -> list[MemoryHit]:
        hits: list[MemoryHit] = []
        for kind in (KIND_REFLECTION, KIND_INSTITUTIONAL, KIND_RESEARCH):
            hits.extend(self.vector.query(question, top_k=per_kind, kind=kind))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits

    def _live_state(self) -> str:
        b = self.bridge
        if b is None or not getattr(b, "enabled", False):
            return ""
        lines = []
        try:
            led = b.latest_ledger()
            if led:
                lines.append(f"ledger: cum PnL ${led.get('cumulative_pnl_usd', 0):.2f}, "
                             f"drawdown {led.get('current_drawdown_pct', 0):.2%}")
            for d in (b.recent_decisions(limit=5) or []):
                lines.append(f"decision {d.get('regime')}/{d.get('risk_verdict')} "
                             f"@ {d.get('timestamp_ms')}: {d.get('risk_reason', '')}")
        except Exception as e:  # noqa: BLE001
            lines.append(f"(live state unavailable: {e})")
        return "\n".join(lines)

    @staticmethod
    def _build_prompt(question: str, hits: list[MemoryHit], live: str,
                      skill_lines: Optional[list[str]] = None) -> str:
        mem = "\n".join(
            f"- [{h.metadata.get('kind', '?')}] {h.text} "
            f"(outcome={h.metadata.get('outcome_label', 'n/a')})"
            for h in hits
        ) or "(no relevant memories found)"
        live_block = live or "(no live state available)"
        skills_block = "\n".join(skill_lines) if skill_lines else "(no live CMC skill reads)"
        return (f"MEMORY:\n{mem}\n\nLIVE STATE:\n{live_block}\n\n"
                f"LIVE CMC SKILLS:\n{skills_block}\n\n"
                f"QUESTION: {question}\n\nAnswer:")


def main(argv: list[str] | None = None) -> None:
    import argparse
    import sys
    from pathlib import Path

    from dotenv import load_dotenv

    # LLM answers can contain non-cp1252 chars; never let a print crash the CLI.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    load_dotenv(Path(__file__).resolve().parents[2] / ".env.local")

    ap = argparse.ArgumentParser(description="Second-Brain co-pilot — ask one question")
    ap.add_argument("question", nargs="+", help="the question to ask")
    args = ap.parse_args(argv)

    from agent.secondbrain.builder import build_second_brain
    sb = build_second_brain()
    pilot = sb.copilot()
    out = pilot.ask(" ".join(args.question))
    print(f"\n  A: {out['answer']}\n")
    if out["sources"]:
        print("  sources:")
        for s in out["sources"]:
            print(f"   - [{s['kind']}] {s['text'][:90]}  (score {s['score']})")
    sb.close()


if __name__ == "__main__":
    main()
