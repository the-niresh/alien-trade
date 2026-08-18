"""
Dreamer - nightly consolidation of the Second Brain.

Fired at 02:00 UTC by jobs/src/dreamer.ts → POST /dreamer on the agent server.
Never raises: if any phase errors, it logs, skips that phase, and continues.
Returns a summary dict so the server endpoint can echo it back to Trigger.dev.

Phases:
  1. Dedupe reflections  - cosine ≥ 0.92 pairs → keep highest-confidence,
                           soft-delete dups in both Vector + Convex.
  2. Forecast calibration scoring - bucket win-rates (high/med/low) logged to
                           Convex via ConvexBridge.
  3. Age out stale research - re-upsert research docs > 48h old with stale=True
                           so co-pilot + avoidance skip them.
  4. Nightly digest       - one ResearchDigest summarising top lessons +
                           forecast score + memory counts stored in Second Brain.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from agent.secondbrain.schema import KIND_RESEARCH, ResearchDigest
from agent.secondbrain.vector import VectorStore
from agent.secondbrain.llm import ClaudeClient

if TYPE_CHECKING:
    from agent.convex_bridge import ConvexBridge

_DEDUPE_THRESHOLD = 0.92   # cosine similarity above which two reflections are "the same"
_STALE_RESEARCH_MS = 48 * 3_600_000   # 48 h

_NIGHTLY_SYSTEM = (
    "You are a concise market-learning summariser. Given the top trade lessons, "
    "forecast accuracy bucket, and memory stats, write a 3-sentence nightly brief: "
    "what the agent learned, how reliable its forecast has been, and the one thing "
    "to watch tomorrow. No preamble. Plain text."
)


@dataclass
class DreamerResult:
    reflections_checked: int = 0
    reflections_deduped: int = 0
    research_aged: int = 0
    forecast_summary: dict = field(default_factory=dict)
    nightly_digest_id: Optional[str] = None
    errors: list[str] = field(default_factory=list)


@dataclass
class Dreamer:
    vector: VectorStore
    llm: ClaudeClient
    bridge: "ConvexBridge"

    def run(self) -> DreamerResult:
        result = DreamerResult()
        self._dedupe_reflections(result)
        self._score_forecast(result)
        self._age_stale_research(result)
        self._write_nightly_digest(result)
        return result

    # ── phase 1: dedupe reflections ───────────────────────────────────────────

    def _dedupe_reflections(self, result: DreamerResult) -> None:
        try:
            rows = self.bridge.recent_reflections(limit=100)
            # Skip already-stale rows
            rows = [r for r in rows if not r.get("stale")]
            result.reflections_checked = len(rows)
            if len(rows) < 2:
                return

            # Build an id→lesson index; compare each lesson against all later ones.
            seen_ids: set[str] = set()
            for i, row in enumerate(rows):
                if row["_id"] in seen_ids:
                    continue
                lesson_i = row.get("lesson", "")
                if not lesson_i:
                    continue
                for row_j in rows[i + 1:]:
                    if row_j["_id"] in seen_ids:
                        continue
                    lesson_j = row_j.get("lesson", "")
                    if not lesson_j:
                        continue
                    sim = self._similarity(lesson_i, lesson_j)
                    if sim >= _DEDUPE_THRESHOLD:
                        # Keep the row with higher |PnL| (more informative outcome);
                        # soft-delete the other from both Convex and Vector.
                        keep, drop = (
                            (row, row_j)
                            if abs(row.get("outcome_pnl_usd", 0)) >= abs(row_j.get("outcome_pnl_usd", 0))
                            else (row_j, row)
                        )
                        seen_ids.add(drop["_id"])
                        self._soft_delete(drop)
                        result.reflections_deduped += 1
        except Exception as e:  # noqa: BLE001
            result.errors.append(f"dedupe: {e}")

    def _similarity(self, a: str, b: str) -> float:
        """Cosine similarity via Vector query (offline → Jaccard via in-memory store)."""
        if not a or not b:
            return 0.0
        try:
            hits = self.vector.query(a, top_k=5)
            for h in hits:
                if h.text and h.text.strip() == b.strip():
                    return h.score
            # Not found in top-5 → below threshold
            return 0.0
        except Exception:  # noqa: BLE001
            # Fallback: simple token Jaccard
            from agent.secondbrain.vector import _jaccard, _tokens
            return _jaccard(_tokens(a), _tokens(b))

    def _soft_delete(self, row: dict) -> None:
        try:
            self.bridge.soft_delete_reflection(row["_id"])
        except Exception:  # noqa: BLE001
            pass
        # Also mark stale in Vector so avoidance lookups skip it
        vid = row.get("vector_id")
        if vid:
            try:
                meta = {k: v for k, v in row.items()
                        if k not in {"_id", "_creationTime"}}
                meta["stale"] = True
                self.vector.upsert(vid, meta.get("lesson", ""), meta)
            except Exception:  # noqa: BLE001
                pass

    # ── phase 2: forecast calibration ────────────────────────────────────────

    def _score_forecast(self, result: DreamerResult) -> None:
        try:
            summary = self.bridge.get_forecast_calibration_summary()
            result.forecast_summary = summary
        except Exception as e:  # noqa: BLE001
            result.errors.append(f"forecast_score: {e}")

    # ── phase 3: age out stale research ──────────────────────────────────────

    def _age_stale_research(self, result: DreamerResult) -> None:
        """Re-upsert research docs older than 48 h with stale=True so co-pilot
        and avoidance lookups skip them. Works by querying Vector for recent
        research, then checking timestamps client-side."""
        try:
            now_ms = int(time.time() * 1000)
            hits = self.vector.query("market research digest", top_k=50, kind=KIND_RESEARCH)
            for h in hits:
                ts = int(h.metadata.get("timestamp_ms", now_ms))
                if now_ms - ts > _STALE_RESEARCH_MS and not h.metadata.get("stale"):
                    meta = dict(h.metadata)
                    meta["stale"] = True
                    self.vector.upsert(h.id, h.text, meta)
                    result.research_aged += 1
        except Exception as e:  # noqa: BLE001
            result.errors.append(f"age_research: {e}")

    # ── phase 4: nightly digest ───────────────────────────────────────────────

    def _write_nightly_digest(self, result: DreamerResult) -> None:
        try:
            top_lessons = self._top_lessons()
            fs = result.forecast_summary
            context = (
                f"Top lessons this cycle:\n{top_lessons}\n\n"
                f"Forecast calibration:\n{json.dumps(fs, indent=2)}\n\n"
                f"Reflections checked: {result.reflections_checked}, "
                f"deduped: {result.reflections_deduped}, "
                f"research aged: {result.research_aged}"
            )
            answer = self.llm.complete(
                context, system=_NIGHTLY_SYSTEM, tier="T1", max_tokens=200,
            ).text
            ts_ms = int(time.time() * 1000)
            did = f"dreamer-nightly-{ts_ms}"
            self.vector.upsert(did, f"nightly brief\n{answer}", {
                "kind": KIND_RESEARCH,
                "question": "nightly",
                "findings": answer,
                "timestamp_ms": ts_ms,
                "tags": ["nightly", "dreamer"],
            })
            result.nightly_digest_id = did
        except Exception as e:  # noqa: BLE001
            result.errors.append(f"nightly_digest: {e}")

    def _top_lessons(self) -> str:
        try:
            rows = self.bridge.recent_reflections(limit=20)
            # Skip stale; sort by |PnL| descending - most impactful first
            active = [r for r in rows if not r.get("stale") and r.get("lesson")]
            active.sort(key=lambda r: abs(r.get("outcome_pnl_usd", 0)), reverse=True)
            lines = [f"- [{r['outcome_label']}] {r['lesson']}" for r in active[:5]]
            return "\n".join(lines) if lines else "(no reflections yet)"
        except Exception:  # noqa: BLE001
            return "(could not fetch lessons)"
