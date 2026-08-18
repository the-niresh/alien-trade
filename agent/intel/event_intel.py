"""
Event Intelligence - deterministic scoring + risk-off detection over news headlines.

Pure-function scoring (a lexicon, not an LLM) so it is fast, free, reproducible, and
safe on the hot path. The output is bounded:
  - risk_severity in [0, 1]  : how dangerous the event is (hack/depeg/insolvency = 1.0)
  - sentiment      in [-1, 1]: bullish vs bearish tone (risk events drag it negative)

A digest with max_severity >= risk_off_threshold flips RISK-OFF, which the risk layer
can treat as a hard "sit out / shrink hard" - the difference between an agent that
sleeps through an exploit and one that steps aside. Everything is advisory and never
raises; with no Brave key the layer is a quiet no-op (sim/live parity).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from agent.intel.brave_client import BraveSearchClient, NewsItem

# ── Lexicons (severity weights for risk; counts for tone) ─────────────────────

# Critical = funds at risk / protocol broken -> hard risk-off.
CRITICAL_RISK = {
    "exploit": 1.0, "hacked": 1.0, "hack": 0.9, "drained": 1.0, "drain": 0.8,
    "stolen": 0.9, "breach": 0.9, "rug pull": 1.0, "rugpull": 1.0, "exit scam": 1.0,
    "depeg": 1.0, "depegged": 1.0, "insolvent": 1.0, "insolvency": 1.0,
    "bankruptcy": 1.0, "halt withdrawals": 1.0, "withdrawals halted": 1.0,
}
# Major = regulatory / legal / structural -> elevated risk.
MAJOR_RISK = {
    "lawsuit": 0.6, "sued": 0.6, "sec charges": 0.7, "investigation": 0.6,
    "subpoena": 0.6, "delisting": 0.7, "delisted": 0.7, "fraud": 0.7,
    "probe": 0.6, "banned": 0.6, "crackdown": 0.6,
}
# Minor = operational / technical wobble -> caution.
MINOR_RISK = {
    "outage": 0.4, "downtime": 0.4, "congestion": 0.35, "paused": 0.4,
    "vulnerability": 0.45, "glitch": 0.35, "liquidation cascade": 0.5,
    "whale dump": 0.4,
}
RISK_TERMS: dict[str, float] = {**MINOR_RISK, **MAJOR_RISK, **CRITICAL_RISK}

BULLISH = {
    "etf approval", "approved", "partnership", "integration", "listing", "listed",
    "upgrade", "mainnet", "rally", "surges", "surge", "record high", "all-time high",
    "adoption", "institutional", "bullish", "soars",
}
BEARISH = {
    "plunge", "crash", "dump", "sell-off", "selloff", "tumble", "slump",
    "bearish", "fears", "decline", "slides", "liquidated",
}

MARKET_RISK_QUERY = "crypto hack exploit depeg SEC lawsuit stablecoin"
DEFAULT_RISK_OFF_THRESHOLD = 0.6


# Allow common inflections on single-word terms (exploit->exploited, depeg->depegs)
# while a trailing \b still rejects unrelated words (hack !-> hackathon).
_INFLECT = r"(?:s|es|ed|d|ing|ged|ging)?"


def _has(term: str, text: str) -> bool:
    if " " in term:                      # multi-word phrase - match verbatim
        pat = r"\b" + re.escape(term) + r"\b"
    else:
        pat = r"\b" + re.escape(term) + _INFLECT + r"\b"
    return re.search(pat, text) is not None


@dataclass(frozen=True)
class HeadlineScore:
    sentiment: float          # [-1, 1]
    risk_severity: float      # [0, 1]
    matched: tuple[str, ...]  # risk terms that fired (for the audit trail)


def score_headline(text: str) -> HeadlineScore:
    """Deterministic lexicon score for one headline+description."""
    t = (text or "").lower()
    severity = 0.0
    matched: list[str] = []
    for term, w in RISK_TERMS.items():
        if _has(term, t):
            severity = max(severity, w)
            matched.append(term)
    bull = sum(1 for term in BULLISH if _has(term, t))
    bear = sum(1 for term in BEARISH if _has(term, t))
    # Risk events are inherently bearish; fold severity into tone.
    sentiment = max(-1.0, min(1.0, 0.34 * bull - 0.34 * bear - severity))
    return HeadlineScore(sentiment, severity, tuple(matched))


@dataclass
class EventDigest:
    symbol: str
    n_headlines: int
    sentiment: float          # mean tone in [-1, 1]
    max_severity: float       # worst risk in [0, 1]
    risk_off: bool
    headlines: list[dict] = field(default_factory=list)  # top items, audit/cockpit
    ts_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    def as_row(self) -> dict:
        return {
            "symbol": self.symbol, "n_headlines": self.n_headlines,
            "sentiment": round(self.sentiment, 4), "max_severity": round(self.max_severity, 4),
            "risk_off": self.risk_off, "headlines": self.headlines, "ts_ms": self.ts_ms,
        }


class EventIntel:
    """Scans news per symbol + a market-wide systemic-risk query, scores, and
    surfaces risk-off + sentiment. Emits to the cockpit channel and Telegram on
    significant events via injected callbacks (both optional, both fail-safe)."""

    def __init__(
        self,
        client: Optional[BraveSearchClient] = None,
        *,
        emit: Optional[Callable[..., None]] = None,     # emit(agent, kind, headline, detail)
        notify: Optional[Callable[[str], None]] = None,  # notify(text) -> Telegram
        log: Optional[Callable[..., None]] = None,       # jlog-compatible
        risk_off_threshold: float = DEFAULT_RISK_OFF_THRESHOLD,
    ):
        self.client = client if client is not None else BraveSearchClient()
        self._emit = emit
        self._notify = notify
        self._log = log
        self.risk_off_threshold = risk_off_threshold

    def _digest(self, symbol: str, items: list[NewsItem]) -> EventDigest:
        if not items:
            return EventDigest(symbol, 0, 0.0, 0.0, False)
        scored = [(it, score_headline(it.text)) for it in items]
        max_sev = max(s.risk_severity for _, s in scored)
        mean_sent = sum(s.sentiment for _, s in scored) / len(scored)
        top = sorted(scored, key=lambda x: (x[1].risk_severity, abs(x[1].sentiment)),
                     reverse=True)[:5]
        headlines = [{
            "title": it.title, "url": it.url, "source": it.source, "age": it.age,
            "severity": round(s.risk_severity, 3), "sentiment": round(s.sentiment, 3),
            "matched": list(s.matched),
        } for it, s in top]
        return EventDigest(symbol, len(items), mean_sent, max_sev,
                           max_sev >= self.risk_off_threshold, headlines)

    def scan(self, symbols: list[str], freshness: str = "pd") -> dict:
        """Scan all symbols + the market. Returns {"per_symbol": {...}, "market": EventDigest}.
        Logs every scan; alerts on any risk-off or high-severity digest."""
        per: dict[str, EventDigest] = {}
        for sym in symbols:
            items = self.client.news(f"{sym} crypto OR {sym} token", count=20, freshness=freshness)
            per[sym] = self._digest(sym, items)
        market = self._digest("MARKET", self.client.news(MARKET_RISK_QUERY, count=20, freshness=freshness))

        self._jlog("intel.scan", n_symbols=len(symbols),
                   market_risk_off=market.risk_off, market_severity=round(market.max_severity, 3),
                   risk_off_symbols=[s for s, d in per.items() if d.risk_off])
        for d in [*per.values(), market]:
            if d.risk_off or d.max_severity >= self.risk_off_threshold:
                self._alert(d)
        return {"per_symbol": per, "market": market}

    # ── side channels (all fail-safe) ───────────────────────────────────────
    def _alert(self, d: EventDigest) -> None:
        top = d.headlines[0]["title"] if d.headlines else ""
        headline = (f"RISK-OFF {d.symbol}: {top}" if d.risk_off
                    else f"Event watch {d.symbol} (sev {d.max_severity:.2f}): {top}")
        try:
            if self._emit:
                self._emit(agent="Scout", kind="observation", headline=headline,
                           detail=d.as_row())
        except Exception:
            pass
        try:
            if self._notify and d.risk_off:
                self._notify(f"⚠️ {headline}")
        except Exception:
            pass

    def _jlog(self, event: str, **fields) -> None:
        try:
            if self._log:
                self._log(event, **fields)
        except Exception:
            pass
