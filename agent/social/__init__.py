"""
Social ingestion layer — "bring your own KOL list, the agent watches them."

A user-curated watchlist of traders/channels across multiple platforms is
ingested through swappable source adapters, normalised to one `SocialPost`
shape, and reduced (OFF the trade hot path) to a bounded, timestamped
`SentimentReading` — the deterministic feature that feeds signal S3. Raw posts
also fuel the Second Brain researcher + co-pilot.

Design rules (inherited from AGENT_TEAM_PLAN.md):
  - Contracts-first: every adapter emits the same `SocialPost` (schema.py).
  - Failure-isolated: one source failing never blocks the others (§9.3).
  - LLM off the hot path: scoring is deterministic; any LLM enrichment is async.
  - Swappable adapters: platforms register behind one `SocialSource` interface.
"""
