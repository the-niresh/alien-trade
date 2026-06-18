# Alien-Trade Productization — Design Spec

**Date:** 2026-06-18
**Author:** Nire + Claude
**Status:** Approved (design), pending implementation plan
**Freeze deadline:** 2026-06-21 12:00 UTC (submission lock) — ~3 days
**Scored window:** 2026-06-29 → 2026-07-05 (held-out, post-lock)

---

## 1. Purpose & Win-Gate Mapping

Improve the live Alien-Trade agent as a *product* without disturbing the deterministic
`/core` trade math or the working cockpit. Every workstream maps to a hackathon
rubric axis or a stackable $2k special prize. Nothing speculative reaches the scored
trade path without the risk engine as its backstop.

| Rubric axis (Track 1) | Covered by |
| --------------------- | ---------- |
| Returns | WS1 (exit rules lift risk-adjusted return), WS3 (bounded upside) |
| Drawdown | WS1 (hard ATR stop, trailing stop, daily-loss kill already present) |
| Risk-adjusted | WS1 |
| Rule adherence | WS1 (every risk decision emits a structured event → visible) |

| Special prize ($2k each) | Covered by |
| ------------------------ | ---------- |
| Best CMC Data & Signal | WS3 (social/KOL signal), WS4 (CMC signals + x402 legibility) |
| Best Trust Wallet Agent Kit | WS4 (TWAK self-custody signing legibility) |
| Best BNB AI Agent SDK | WS4 (`twak swap` execution legibility) |

Demo / narrative / judge-testability: WS2 (notification panel removes the Telegram dependency).

---

## 2. Constraints (locked — do not violate)

- **Deterministic `/core` trade math.** No LLM in signal computation or execution path.
- **Sim and live share `/core`.** No sim-only vs live-only code paths.
- **Scored path is spot-long-only on the eligible allowlist** (`ETH, CAKE, UNI, LINK, AAVE`).
  Only `twak swap` longs count toward PnL. BNB/BTC/BTCB are NOT eligible.
- **Drawdown-first objective.** Never optimize for raw return.
- **Out-of-sample only.** No in-sample selection of any new rule.
- **Additive only.** No edits to existing working cockpit views or Convex schema beyond
  additive event fields. No unrelated refactoring.

---

## 3. Existing Infrastructure (build on, do not duplicate)

| Capability | Where it already lives | State |
| ---------- | ---------------------- | ----- |
| Daily-loss kill, consecutive-loss breaker, vol-targeted sizing, Kelly cap, max-exposure, slippage abort, allowlist | `core/risk/{engine,guardrails,sizing}.py` | Working |
| Append-only event channel + reactive queries (`recent`, `latestPerAgent`) | `convex/agentEvents.ts` (table `agent_events`) | Working |
| Social/KOL pipeline (ingest, normalize, score, sources, watchlist) | `agent/social/` + `convex/social.ts` | Built as research input; NOT wired to execution |
| Sentiment signal (S3) | `core/signals/sentiment.py` | Working |
| CMC x402 micropayments | `agent/x402_provider.py` | Working |
| TWAK self-custody signing | `agent/twak_cli.py` | Working |
| Sonner toasts | wired in `web/src/App.tsx` (commit `3302f8f`) | Working |

**Net-new is small:** a hard ATR stop, a notification panel view, the social→execution
bridge (gated), and a sponsor-depth surface/doc.

---

## 4. Workstreams

### WS1 — Risk Hardening *(lands first; the seatbelt for WS3)*

**Goal:** improve drawdown + risk-adjusted + rule-adherence; this also IS the
"strategy edge" per the locked search direction (exit/risk rules, not entries).

- **Hard ATR stop-loss** per open position, enforced in `core/risk/`. Drops into
  `run_backtest`/`run_walk_forward` like the existing engine (it is itself a `StrategyFn`).
- **Trailing stop / take-profit** exit so winners lock gains (lifts risk-adjusted return
  without touching entries).
- **Structured risk events:** every block/stop/halt/size-cut emits a row to
  `agent_events` (`kind: "action"|"control"`) so "rule adherence" is demonstrable in the UI.
- **Validation:** all new exit rules backtested **out-of-sample / walk-forward** before
  shipping. No in-sample selection. Full cost model retained.

**Interfaces:** new exit logic is additive to `RiskEngine`; existing guardrail signature
(`GuardrailResult`) reused so callers learn WHY a position was closed.

**Done when:** ATR stop + trailing exit pass walk-forward without worsening OOS drawdown,
and every risk action appears as an `agent_events` row.

### WS2 — Notification Panel + Sonner Event Feed

**Goal:** product completeness + judge-testability. Makes Telegram optional (solves the
India-ban / "how will judges test it" problem — judges see everything in-cockpit).

- New `web/src/components/NotificationPanel.tsx` reading the existing
  `agentEvents.recent` reactive query (no backend change required).
- **Severity tiers** (info / trade / risk / critical) with a filter control.
- **Sonner toast** fires on new high-priority events (trade fill, risk halt, stop hit,
  KOL-triggered action). Debounced so a burst doesn't spam.
- Panel surfaces as a slide-over / dedicated nav entry consistent with existing
  mission-control HUD identity (`AppShell`, `SideNav`, shadcn `Sheet`).

**Interfaces:** read-only consumer of `agent_events`; no new Convex tables. Reuses the
existing event `kind` union; if a new severity field is needed it is **additive** to the
`append` mutation args (optional, defaulted).

**Done when:** every event written by WS1/WS3 appears live in the panel, and a
high-priority event raises a Sonner toast, with Telegram disabled.

### WS3 — X/KOL Auto-Trade *(bounded; depends on WS1)*

**Goal:** the requested "full auto-trade on signals," kept inside the scoring rules so it
actually counts and inside the risk engine so it cannot blow drawdown.

- **Watchlist** of X/KOL accounts (scaffolded: `agent/social/watchlist.example.json`).
- **Pipeline (existing `agent/social/`):** ingest → normalize → classify.
- **Classification off the hot path:** LLM (or rules) classifies an update as
  bullish / bearish / neutral about a specific token. The classification is produced
  *before* and *outside* the deterministic execution step (classify-then-gate). A
  **deterministic fallback** (keyword/score-based) runs if the X API or LLM is unavailable,
  so the agent never crashes during the scored window.
- **Allowlist filter:** only updates about `ETH/CAKE/UNI/LINK/AAVE` can act. Updates about
  ineligible tokens (BTC/BNB/etc.) are logged but never traded.
- **Action mapping (scoring-safe):**
  - Bullish on eligible token → **open a `twak swap` spot-long**, sized by the risk engine,
    with the WS1 hard stop attached.
  - Bearish on a token we hold → **reduce/close** that long (capital preservation). Never
    opens a short (shorts are not `twak swap`, do not score).
  - Neutral / ineligible → no trade; logged only.
- **Risk-gated:** every X-triggered entry passes the same `check_guardrails` +
  daily-loss + exposure + sizing path as any other signal. The X signal cannot bypass any cap.
- **Observability:** every X decision (including "saw it, didn't trade, here's why") logs to
  `agent_events` → visible in WS2 panel.

**Interfaces:** social pipeline emits a normalized `{account, token, stance, confidence, ts}`
intent; a thin bridge converts an eligible+confident intent into a candidate order that is
handed to `RiskEngine`. The bridge owns allowlist + stance→action mapping; the risk engine
owns sizing + caps + stop. Clear separation: social layer never sizes or sends; risk engine
never parses tweets.

**Done when:** a bullish KOL update about an eligible token produces a risk-sized,
stop-protected `twak swap` long that appears in the ledger and the notification panel; an
update about an ineligible token is logged-not-traded; X API outage degrades to the
deterministic fallback without crashing the loop.

### WS4 — Sponsor-Depth Legibility *(special prizes; low code)*

**Goal:** make the three sponsor integrations *legible* to judges — three stackable $2k prizes.

- One **sponsor-integration page** (cockpit view) + matching **doc** mapping real code paths:
  - **CMC:** signals (S1–S4) + x402 micropayments (`x402_provider.py`) + social/KOL (WS3).
  - **TWAK:** self-custody signing for every swap (`twak_cli.py`), keys never in code/logs.
  - **BNB SDK:** `twak swap` spot execution + on-chain receipt as ledger source of truth.
- Each integration shown *live* in the cockpit (e.g., last x402 payment, last TWAK-signed tx,
  last on-chain receipt) so a judge sees it working, not just reads about it.

**Interfaces:** read-only views over existing Convex tables (`ledger`, `trades`,
`walletState`) + a static doc. No new execution code.

**Done when:** a judge can open one screen and see all three sponsor capabilities in use,
each linked to a real on-chain / payment artifact.

---

## 5. Build Order & Dependencies

```
WS1 (risk hardening) ──┬──> WS3 (X auto-trade, needs the seatbelt)
                       │
WS2 (panel) ───────────┤   (consumes events from WS1 + WS3)
                       │
WS4 (sponsor depth) ───┘   (independent; interleave anytime)
```

1. **WS1 first** — non-negotiable. WS3 is unsafe without it.
2. **WS2 next** — gives immediate visibility into WS1's new events and is the demo backbone.
3. **WS3** — the headline feature, now seatbelted.
4. **WS4** — interleave; mostly artifacts/views, can land in parallel with any of the above.

---

## 6. Testing & Verification

- **WS1:** walk-forward / OOS backtest of ATR + trailing exits; assert OOS max-drawdown does
  not worsen vs current baseline. Unit tests for stop trigger + trailing ratchet.
- **WS2:** component renders from a mocked `agent_events` slice; toast fires once per
  high-priority event (debounce verified).
- **WS3:** unit tests for stance→action mapping, allowlist filter (ineligible token →
  no order), and fallback-on-outage. Integration: a synthetic bullish update produces a
  risk-sized candidate order; a bearish update on a non-held token is a no-op.
- **WS4:** view renders from real Convex rows; doc links resolve to real files.
- **Regression guard:** existing `core/` tests stay green; sim/live share `/core`.

---

## 7. Risks & Mitigations

| Risk | Mitigation |
| ---- | ---------- |
| X auto-trade blows drawdown in scored window | Risk engine gate + hard stop + daily-loss kill (WS1 ships first) |
| Unvalidated entry signal overfits | Bounded size; allowlist-only; bearish can only de-risk; OOS-validated stops cap downside |
| X API / LLM outage mid-window | Deterministic fallback classifier; loop degrades, never crashes |
| Notification spam | Severity tiers + Sonner debounce |
| Scope creep in 3 days | Strict WS order; WS4 is mostly artifacts; no refactoring |
| Touching working code | Additive-only rule; no schema/view rewrites; `/core` math untouched |

---

## 8. Explicit Non-Goals (YAGNI)

- No LLM in the deterministic execution path.
- No shorts / perps in the scored path.
- No native mobile app (PWA only).
- No separate webhook server (Convex is the bus).
- No rewrite of existing cockpit views or Convex schema.
- No trading of ineligible tokens regardless of KOL hype.
