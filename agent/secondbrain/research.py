"""
Karpathy AutoResearch loop (async, off the hot path).

A supervisor spawns a research sub-agent that *self-directs*: it inspects the
current market, decides what it doesn't understand (regime anomalies, social
spikes, OI/price divergence), gathers data (CMC live quote + recent bars),
synthesises a "market research digest" via the LLM, and stores each digest in
the Second Brain (Upstash Vector, kind="research"). The regime narrative and the
co-pilot both read these digests later.

This is the supervisor → sub-agent pattern (locked decision #4 / #6). It is
implemented in plain, testable Python so it runs offline; the same shape drops
onto a LangGraph supervisor when that lands. The sub-agent makes NO trade
decision — it only researches and writes memory.

Run:  core/.venv/Scripts/python.exe -m agent.secondbrain.research --symbol BNB
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backtest.engine import Bar
from backtest.regime import detect_regime

from agent.secondbrain.llm import ClaudeClient
from agent.secondbrain.schema import KIND_RESEARCH, ResearchDigest
from agent.secondbrain.vector import VectorStore
from agent.skills import SkillContext, SkillHub, skill_summary
from risk.forecast import confidence_from_regime as _confidence_from_regime

# Curated skills pulled each research cycle to ground the digest in the orthogonal
# CMC signals (S2/S3/regime) that price action alone can't show. Small + bounded:
# these are paid, off-hot-path calls. Override via ResearchAgent.skill_keys.
_DEFAULT_SKILL_KEYS = ("market_regime", "funding_regime", "kol_sentiment")

_DIGEST_SYSTEM = (
    "You are a crypto market research analyst. Given a specific question and the "
    "current market context, write a concise (max 4 sentences) digest: the likely "
    "explanation, what to watch next, and the trading implication. No preamble."
)


@dataclass
class ResearchAgent:
    """The self-directing sub-agent: identify unknowns → gather → synthesise."""
    llm: ClaudeClient
    symbol: str = "BNB"
    # CMC Skill Hub (Tier-1 curated reads enrich the context). None/offline →
    # the agent works exactly as before on price + live quote (offline-first).
    skills: Optional[SkillHub] = None
    skill_keys: tuple[str, ...] = _DEFAULT_SKILL_KEYS

    def identify_unknowns(self, history: list[Bar]) -> list[str]:
        """Decide what to research from the current data. Always returns ≥1 item
        (the baseline regime question) so a cycle is never empty."""
        qs: list[str] = []
        regime = detect_regime(history).value if history else "unknown"
        qs.append(f"What defines the current {regime} regime on {self.symbol} and "
                  f"what is the highest-probability path from here?")

        if len(history) >= 25:
            recent = detect_regime(history[-15:]).value
            if recent != regime:
                qs.append(f"Regime anomaly: {self.symbol} shifted {regime}→{recent} "
                          f"recently — distribution top, or healthy consolidation?")
            last = history[-1]
            # Extended CMC fields (social/OI) wire in via cmc_client; act on them
            # when non-zero so the digest is data-driven, not boilerplate.
            if abs(last.social_score) > 0.0:
                qs.append(f"Social attention on {self.symbol} is spiking "
                          f"(score {last.social_score:.2f}) — sentiment-led move or noise?")
            if last.open_interest > 0.0 and last.net_flow != 0.0:
                qs.append(f"{self.symbol} OI/flow divergence (OI {last.open_interest:.0f}, "
                          f"flow {last.net_flow:.0f}) — accumulation or a crowded trade?")
        return qs

    def gather_context(self, history: list[Bar]) -> str:
        """Pull live CMC context + recent price action (guarded — works offline)."""
        lines = []
        try:
            from data.cmc_client import CMCClient
            with CMCClient() as cmc:
                q = cmc.fetch_quote_live(self.symbol)
            lines.append(f"CMC live: ${q['price']:.2f}, 24h {q['percent_change_24h']:+.2f}%, "
                         f"vol ${q['volume_24h']:,.0f}")
        except Exception as e:  # noqa: BLE001 — CMC optional; bars are enough
            lines.append(f"CMC live unavailable ({e}); using recent bars only.")
        if history:
            closes = [b.close for b in history[-10:]]
            lines.append(f"last 10 closes: {[round(c, 2) for c in closes]}")
            lines.append(f"regime: {detect_regime(history).value}")
        lines.extend(self._skill_evidence())
        return "\n".join(lines)

    def _skill_evidence(self) -> list[str]:
        """Curated CMC skill reads (funding regime, sentiment, market regime) as
        compact one-liners. Each call is guarded — a skill failing is advisory and
        must never break a research cycle (failure-matrix). Empty when offline."""
        if self.skills is None or not self.skills.enabled:
            return []
        ctx = SkillContext(symbol=self.symbol)
        out: list[str] = []
        for key in self.skill_keys:
            try:
                brief = _skill_brief(key, self.skills.run_curated(key, ctx))
            except Exception:  # noqa: BLE001 — advisory only
                brief = ""
            if brief:
                out.append(brief)
        return out

    def synthesise(self, question: str, context: str) -> str:
        prompt = f"Question: {question}\n\nMarket context:\n{context}\n\nDigest:"
        return self.llm.complete(prompt, system=_DIGEST_SYSTEM, tier="T1", max_tokens=300).text


@dataclass
class ResearchSupervisor:
    vector: VectorStore
    llm: ClaudeClient
    symbol: str = "BNB"
    skills: Optional[SkillHub] = None
    agent: ResearchAgent = field(init=False)

    def __post_init__(self) -> None:
        self.agent = ResearchAgent(llm=self.llm, symbol=self.symbol, skills=self.skills)

    def run_cycle(self, history: Optional[list[Bar]] = None, *, max_questions: int = 3) -> list[ResearchDigest]:
        """One full AutoResearch cycle: spawn sub-agent → research → store digests."""
        if history is None:
            history = self._fetch_history()
        ctx = self.agent.gather_context(history)
        questions = self.agent.identify_unknowns(history)[:max_questions]

        ts = history[-1].timestamp if history else 0
        digests: list[ResearchDigest] = []
        for idx, q in enumerate(questions):
            findings = self.agent.synthesise(q, ctx)
            d = ResearchDigest(
                id=f"research-{self.symbol}-{ts}-{idx}",
                timestamp_ms=ts, question=q, findings=findings,
                tags=[self.symbol, "autoresearch"],
            )
            self.vector.upsert(id=d.id, text=f"{q}\n{findings}", metadata={
                "kind": KIND_RESEARCH, "symbol": self.symbol,
                "question": q, "findings": findings, "timestamp_ms": ts,
            })
            digests.append(d)
        return digests

    def _fetch_history(self) -> list[Bar]:
        try:
            from data.binance_client import BinanceClient
            with BinanceClient() as c:
                return c.fetch_recent_bars(self.symbol, interval="1h", limit=200)
        except Exception as e:  # noqa: BLE001
            print(f"[research] could not fetch bars: {e}")
            return []


def confidence_from_history(history: list[Bar]) -> float:
    """Deterministic confidence from the current regime. Returns NEUTRAL (1.0)
    when history is empty so an empty research cycle can't silently shrink size."""
    if not history:
        return 1.0
    return _confidence_from_regime(detect_regime(history).value)


def _skill_brief(key: str, payload: dict) -> str:
    """Compact one-liner for a curated skill read (delegates to the shared
    summariser; kept as a thin local name the research agent + tests use)."""
    return skill_summary(payload, key)


def main(argv: list[str] | None = None) -> None:
    import argparse
    import os
    import sys
    from pathlib import Path

    from dotenv import load_dotenv

    # LLM digests can contain non-cp1252 chars; never let a print crash the CLI.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    load_dotenv(Path(__file__).resolve().parents[2] / ".env.local")

    ap = argparse.ArgumentParser(description="Karpathy AutoResearch — one cycle")
    ap.add_argument("--symbol", default="BNB")
    args = ap.parse_args(argv)

    from agent.secondbrain.builder import build_second_brain
    sb = build_second_brain()
    sup = sb.research(symbol=args.symbol)
    print(f"\n  AutoResearch cycle | symbol={args.symbol} | "
          f"vector={'on' if sb.vector.enabled else 'offline'} | "
          f"llm={'on' if sb.llm.enabled else 'stub'}")
    digests = sup.run_cycle()
    for d in digests:
        print(f"\n  Q: {d.question}\n  -> {d.findings}")
    print(f"\n  digests stored: {len(digests)}")
    print(f"  llm telemetry: {sb.telemetry.snapshot()}")
    sb.close()


if __name__ == "__main__":
    main()
