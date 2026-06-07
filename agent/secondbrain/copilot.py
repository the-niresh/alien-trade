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

    def ask(self, question: str, *, tier: str = "T1", per_kind: int = 3) -> dict:
        hits = self._retrieve(question, per_kind)
        live = self._live_state()
        prompt = self._build_prompt(question, hits, live)
        res = self.llm.complete(prompt, system=_COPILOT_SYSTEM, tier=tier, max_tokens=400)
        return {
            "question": question,
            "answer": res.text,
            "sources": [{"id": h.id, "kind": h.metadata.get("kind"),
                         "score": round(h.score, 3), "text": h.text} for h in hits],
            "grounded": bool(hits) or bool(live),
            "stub": res.stub,
        }

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
    def _build_prompt(question: str, hits: list[MemoryHit], live: str) -> str:
        mem = "\n".join(
            f"- [{h.metadata.get('kind', '?')}] {h.text} "
            f"(outcome={h.metadata.get('outcome_label', 'n/a')})"
            for h in hits
        ) or "(no relevant memories found)"
        live_block = live or "(no live state available)"
        return (f"MEMORY:\n{mem}\n\nLIVE STATE:\n{live_block}\n\n"
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
