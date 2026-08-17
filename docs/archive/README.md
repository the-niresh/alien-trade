# Archive

Nothing in here describes how the project works today. It is kept because it is the
real record of how it got built, and deleting it would make the git history harder to
read rather than easier.

## `contest-2026-06/`

Alien-Trade was originally built for a three-week hackathon in June 2026 (BNB Hack,
DoraHacks). These are the documents from that period:

| File | What it was |
|---|---|
| `PROJECT_PLAN.md` | The original build plan, organised around the contest deadline |
| `AWAKE_SPRINT.md`, `AWAKE_SPRINT_PLAN.md` | The final week's sprint notes |
| `STEPS.md`, `VPS_STEPS.md` | Ordered build and deploy runbooks |
| `LIVE_REHEARSAL.md` | Pre-launch rehearsal checklist |
| `CMC_COVERAGE.md` | Which CoinMarketCap fields were wired up |
| `SPONSOR_DEPTH.md`, `SPONSOR_TOOLS_INTEGRATION.md` | Notes on the three sponsor SDKs |
| `FROZEN_ALLOWLIST.txt` | The token list at feature freeze |
| `docs.md`, `full.md`, `llm.md` | Contest brief, an early project summary, and a design conversation |
| `vendor-api-notes/` | API notes for the three vendor SDKs (BNB Chain, CoinMarketCap, Trust Wallet) |

Two things in here are worth reading even now, because they are honest about what
failed:

- `AWAKE_SPRINT.md` describes the thesis-testing process that produced
  [`../THESIS_LEDGER.md`](../THESIS_LEDGER.md) — six trading ideas, all six rejected.
- `llm.md` is a working conversation about whether the strategy actually had an edge.
  The answer turned out to be no. See [`../results/EVALUATION.md`](../results/EVALUATION.md)
  for the measurement that settled it.

The contest framing has been removed from the code and from the top-level docs. It is
preserved here rather than rewritten, so the archive still reads as what it was.
