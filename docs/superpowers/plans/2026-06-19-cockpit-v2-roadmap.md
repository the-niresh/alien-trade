# Cockpit v2 — Roadmap (10-item batch, 2026-06-19)

> **What this is:** an index/roadmap that locks the decisions from the 2026-06-19 review, applies the win-gate to each item, and breaks the work into independent workstreams. Trivial items are fully specified inline (do them now). Large workstreams get a one-line "detailed plan to be written" pointer — ask Claude to expand any one into a full bite-sized `superpowers:writing-plans` document before handing to Sonnet.
>
> **Freeze:** Jun 21. **Live window:** Jun 22–28. Today: Jun 19. Sequence by win-value, not by item number.

## Locked decisions (from the review)

| # | Decision | Chosen |
|---|----------|--------|
| 2 | Wallet model | **Real per-user wallets** — but see ⚠️ below; deferred post-freeze, spike-gated |
| 7 | Multi-symbol | **UI/chart toggle only** across ETH/CAKE/UNI/LINK/AAVE; agent keeps trading its chosen symbol |
| 1 | Intelligence + sponsors | **Dedicated showcase view** (judge-facing) |
| 8 | Nav | **Top items + 'More' overflow**; mobile keeps 5, but make all views reachable |

### ⚠️ Item 2 conflict (must reconfirm before building)

"Real per-user wallets" overrides 4 locked decisions (`FRONTEND_PLAN.md:111`, `STEPS.md:353`, `AWAKE_SPRINT.md:73`, `VALIDATION_1H.md:45`) and the single-credential TWAK model (`agent/wallet.py`). Win-gate verdict: **NO** for the live window (zero Track-1 value, risks the registered competition wallet, 2 days to freeze). Handled as **Workstream F** — a post-Jun-28, flag-gated build that starts with a TWAK multi-wallet feasibility spike. Do **not** start it before the live window without explicit re-confirmation.

## Win-gate triage & priority

| Item | Workstream | Win-gate | Priority |
|------|-----------|----------|----------|
| 1 — Intelligence/sponsor showcase | **A** | **YES** — sells CMC/TWAK/BNB depth ($2k prizes) + Track-1 narrative | P0 |
| 3 — Portfolio icon · 4 — balance surfacing · 5 — realized-PnL chart | **B** | maybe — demo looks finished; #4 already largely done | P1 |
| 8 — nav declutter · 9 — tour fixes + per-tab tours | **C** | maybe — onboarding/demo polish; fixes a real mobile-reachability bug | P1 |
| 6 — KOL/listener tracker from twitter_handles.json | **D** | maybe — S3 sentiment depth, CMC social angle, judge-facing | P2 |
| 7 — symbol toggle (UI only) | **E** | maybe — looks multi-asset, low risk | P2 |
| 2 — per-user wallets | **F** | **NO (now)** — deferred, spike-gated | P3 (post-freeze) |
| 10 — optimizations | (folded into each) | maybe | ongoing |

**Recommended build order before freeze:** A → B → C → E → D. F after Jun 28.

---

## Workstream A — Intelligence & Sponsor Showcase (item 1) · P0

**Goal:** A dedicated, judge-facing **"Intelligence"** view that makes the sponsor stack and the LLM intelligence layer impossible to miss: *we use CoinMarketCap + Trust Wallet Agent Kit + BNB AI Agent SDK, and we built a self-learning intelligence layer (Hermes reflection + Karpathy AutoResearch + Second Brain) on top of them.*

**Why a new view:** `AgentsView` (CoPilot/Historian/Researcher/Reflector) and `PipelineView` exist but read as internal telemetry; nothing narrates the sponsor depth. `web/src/lib/sponsorRegistry.ts` already enumerates sponsor usage — reuse it.

**Files:**
- Create: `web/src/views/IntelligenceView.tsx` — the showcase.
- Create: `web/src/components/SponsorCard.tsx` — one card per sponsor (CMC / TWAK / BNB SDK) listing concrete usage + a live "calls today / last used" stat.
- Reuse: `web/src/lib/sponsorRegistry.ts` (verify/extend its entries), `convex/agentEvents.ts` (live activity), `AGENT_DEFS` from `AgentCard.tsx`.
- Modify: `web/src/components/SideNav.tsx` + `BottomNav.tsx` (add the nav entry — coordinate with Workstream C), `web/src/App.tsx` (route `case "intelligence"`).
- Backend (optional, only if a live "intelligence is ON" badge is wanted): surface `SECOND_BRAIN` flag + reflection/research counts via an existing query (`convex/reflections.ts`, `convex/agentEvents.ts`).

**Approach / sections of the view:**
1. **Sponsor stack** — 3 `SponsorCard`s. Each: logo/wordmark, one-line "what it does for us," bullet list of concrete integration points (from `sponsorRegistry.ts`), and a live counter (e.g. "TWAK swaps executed", "CMC calls today", "x402 micropayments"). Pull counts from `agentEvents`/`audit`.
2. **Intelligence layer** — a labeled flow: *deterministic core (no LLM)* → *Hermes reflection loop* → *Karpathy AutoResearch* → *Second Brain (Upstash Vector)* → *co-pilot/regime narrative*. Show each node's live state (last reflection, last research digest, # memories) and an honest "ON/OFF" pill driven by `SECOND_BRAIN`.
3. **Architecture one-liner** banner: "LLM is OFF the trade hot path — decisions are deterministic Python; the LLM learns *around* the trade." (This is a locked architectural truth and a strong judge talking point.)

**Optimization (item 10):** if Second Brain stays `SECOND_BRAIN=0` for the live window, the view must degrade gracefully — show the layer as "armed, runs post-trade" rather than empty/broken.

**Risk:** low (read-only UI). Don't fabricate counts — wire to real `audit`/`agentEvents` rows or label as "capability."

**Detailed plan:** to be written (`2026-06-19-intelligence-showcase.md`).

---

## Workstream B — Portfolio polish (items 3, 4, 5) · P1

### B1 — Portfolio nav icon (item 3) · trivial, do now

The Portfolio nav uses a wallet glyph (`SideNav.tsx:17`), which collides with the Deposit/Withdraw wallet semantics. Swap to a portfolio glyph.

- Modify `web/src/components/SideNav.tsx`:
  - Line 9 import: add `PieChart` to the `lucide-react` import.
  - Line 17: change `{ view: "portfolio", icon: Wallet, label: "Portfolio" }` → `{ view: "portfolio", icon: PieChart, label: "Portfolio" }`.
- If `Wallet` becomes unused after this, leave it (Deposit/Withdraw use their own arrows; `Wallet` may still be referenced — verify with `tsc --noEmit`).
- Commit: `fix(nav): portfolio uses PieChart icon, not wallet glyph`.

### B2 — Balance surfacing (item 4) · mostly done

Already implemented: `WalletBalance` (rendered in `OverviewView.tsx:106`), Portfolio holdings table (`PortfolioView.tsx`), Deposit. **Gap:** balance/total isn't in the persistent header. Optional enhancement:
- Add a compact total-equity chip to `web/src/components/LiveHeader.tsx` (reads `api.walletState.get`, shows `usd(total_usd)` with a wallet-synced dot). Keep it behind the existing `overflow-hidden` header layout; hide on `max-sm`.

### B3 — Realized-PnL chart (item 5)

`EquityChart` plots **cumulative** PnL + drawdown. Add a **realized-PnL** chart to Portfolio (realized = closed-trade PnL over time, distinct from unrealized/marked equity).

- Check `convex/ledger.ts` + `convex/schema.ts:89` (`ledger` table) for a realized-PnL field. If `realized_pnl_usd` (or per-trade `pnl_usd` on closed sells) exists, plot its running sum; if not, derive from `convex/trades.ts` closed sells. **Add the query first** (`api.ledger.realizedHistory` or compute in a new `convex/portfolio.ts` query) — do not compute heavy aggregations in the component.
- Create `web/src/components/RealizedPnlChart.tsx` (mirror `EquityChart.tsx` recharts setup; single area/line for cumulative realized PnL, green/red by sign).
- Render in `PortfolioView.tsx` between "Cumulative PnL" panel and "Holdings".
- Empty state identical to `EquityChart`'s "awaiting telemetry".

**Risk:** medium — depends on whether realized PnL is already tracked. The detailed plan must resolve the data source first (TDD the Convex query).

**Detailed plan:** to be written (`2026-06-19-portfolio-polish.md`).

---

## Workstream C — Navigation & Tours (items 8, 9) · P1

### C1 — Desktop nav declutter + mobile reachability (item 8)

Desktop sidebar = 13 items (`SideNav.tsx`); mobile = 5 (`BottomNav.tsx`) and **can't reach** deposit/withdraw/portfolio/positions/pipeline/logs/notifications/docs — a real bug.

**Approach (chosen: top items + 'More' overflow):**
- Define a single source of truth for nav grouping (e.g. `web/src/lib/nav.ts`): `PRIMARY` (≈6: overview, trackers, chart, portfolio, intelligence, controls) and `MORE` (the rest).
- Desktop `SideNav`: render `PRIMARY` in the rail; add a "More" button opening a popover/sheet (shadcn `Sheet` or a simple popover) listing `MORE` items. Keep tour/copilot/theme footer buttons.
- Mobile `BottomNav`: keep 4 primary + a 5th **"More"** tab opening a `Sheet` with every remaining view — this fixes the reachability bug. (Currently the 5 are overview/trackers/chart/agents/controls; swap `agents` out for `portfolio` in the primary 4 and make tab 5 = More, per importance.)
- Keep `data-tour` attributes intact for the tour.

### C2 — Tour fixes + per-tab tours (item 9)

**Bug:** the "Kill Switch" tour step targets `[data-tour="brand"]` (`tour.ts:33`) — it highlights the logo, not the kill switch.
- Add `data-tour="killswitch"` to the `KillSwitch` instance in `LiveHeader.tsx:147` (and/or `AppShell.tsx:62`).
- Point `tour.ts` step 2 `element` to `[data-tour="killswitch"]`.

**Per-tab contextual tours:** start a tour scoped to the active view.
- Refactor `lib/tour.ts` from one `startTour()` to a registry: `TOURS: Record<View, TourStep[]>` + `startTour(view?: View)`. If `view` has a registered tour, run it; else run the global welcome tour.
- Author short tours for the high-value views: `overview`, `portfolio`, `chart`, `controls`, `intelligence`, `trackers`, `deposit`. Each step targets a `data-tour="…"` element inside that view (add the attributes as part of this workstream).
- Wire the SideNav "Start tour" button (`SideNav.tsx:101 onTour`) to pass the **current** view: `onTour={() => startTour(activeView)}` (thread `activeView` into the handler in `App.tsx`).
- Keep the first-run global tour + post-trade tour as-is.

**Note on item 9 wording ("button doesn't go near the kill button"):** interpreted as *the tour's kill-switch step doesn't point at the kill switch* — fixed by C2. If you instead meant the **Start-tour button should physically sit next to the kill switch in the header**, say so and I'll move the trigger from the SideNav footer into `LiveHeader` beside `KillSwitch`.

**Risk:** low. Mostly additive.

**Detailed plan:** to be written (`2026-06-19-nav-and-tours.md`).

---

## Workstream D — KOL / Listener tracker (item 6) · P2

**Goal:** Turn `docs/twitter_handles.json` (50+ handles with `numListeners`, `numBoosts`) into a KOL/listener tracker UI, modeled on `docs/screenshots/social.png` (Manager/Trades/Monitor/**KOLs** tabs + a "Customize Feed / Twitter Alerts / Socials" right panel with handle / listeners / boosts columns).

**What "boosts" is:** unknown from the data alone — almost certainly an engagement/amplification weight (retweets/quote-amplification). The plan should display it as a raw "Boosts" metric and a derived **influence score** (e.g. `numListeners` × log(`numBoosts`)) for ranking, *without* claiming a precise definition.

**Files:**
- Ingest: a one-time loader (Convex mutation `convex/social.ts → importKolHandles` or a `jobs/` script) that reads `twitter_handles.json` into a new `kol_handles` table (`schema.ts`): `{ handle, num_listeners, num_boosts, task_id?, influence_score, tracked: boolean }`.
- Query: `convex/social.ts → listKolHandles` (sorted by influence/listeners, top-N).
- View: `web/src/views/TrackersView.tsx` already exists — add a **KOLs** sub-tab there (matches `social.png`'s Trackers→KOLs), OR a focused `KolTrackerView`. Columns: Handle · Listeners · Boosts · Influence · Track toggle.
- "Wire them as listeners": let the user **track** a handle (toggle) → tracked handles feed the existing S3 sentiment path (`convex/social.ts` sources/`addSource`). Confirm the agent's social ingest reads tracked handles.

**Open question for the detailed plan:** does the live agent currently consume a KOL list (loop.py `kol_intent` at `loop.py:687` suggests yes)? If so, wire "tracked" handles into that path; if not, the tracker is display-only for the demo (still fine, label honestly).

**Risk:** medium — depends on whether tracked handles actually flow into the signal. Don't imply live influence if it's display-only.

**Detailed plan:** to be written (`2026-06-19-kol-tracker.md`).

---

## Workstream E — Symbol toggle, UI only (item 7) · P2

**Goal:** A header/chart token selector across the **eligible** set **ETH / CAKE / UNI / LINK / AAVE** (`core/sweep.py:13`). **Not** BNB (gas-only) or SOL (not BSC). Agent keeps trading its chosen symbol — this is presentation only.

**Files:**
- `web/src/components/LiveHeader.tsx` — there's already a symbol `Select` fed by `api.symbolList.list`. **Problem:** `convex/symbolList.ts` derives symbols from **open positions only**, so the toggle is empty/ETH-only until positions exist. Change `symbolList.list` (or add `symbolList.eligible`) to return the static eligible allowlist `["ETH","CAKE","UNI","LINK","AAVE"]` (optionally unioned with symbols that have price ticks).
- `web/src/views/ChartView.tsx` + `PortfolioView.tsx` — ensure they respond to the selected symbol. Chart already has a Binance fallback for CAKE/UNI/LINK/AAVE (per CLAUDE.md history), so price data exists.
- Keep the selected symbol in `App.tsx` state (it already threads `selectedSymbol`/`onSymbolChange` into `LiveHeader`).

**Optimization (item 10):** ensure `priceTicks.forSymbol` / Binance fallback is hit for the non-ETH tokens so charts aren't perpetually "awaiting data" (this was a prior bug — verify it's covered).

**Risk:** low — no trade-path change. Be explicit in copy that the agent trades one symbol; the toggle is for viewing.

**Detailed plan:** to be written (`2026-06-19-symbol-toggle.md`).

---

## Workstream F — Per-user wallets (item 2) · P3 · POST-FREEZE, SPIKE-GATED

**Status:** deferred. Overrides 4 locked decisions and the win-gate (see ⚠️ above). Do not start before Jun 28 without explicit re-confirmation.

**Gate 0 — feasibility spike (must pass before any plan):**
- Determine whether TWAK supports multiple wallets under one `TW_ACCESS_ID`/`TW_HMAC_SECRET`, or whether each user needs their own TWAK account/credentials. `agent/wallet.py:63` shows `twak wallet create --password <pw>` exists — confirm whether created wallets are addressable independently and how signing selects among them.
- Decide the keys/custody model: self-custody means keys never touch our code — so per-user wallets imply per-user TWAK credentials or a TWAK-hosted multi-wallet. This is the crux.

**If the spike passes, the build (large):**
- Per-user identity/session (the cockpit is currently single-tenant, control-token paired).
- Wallet-scoped everything: `wallet_state`, `ledger`, `positions`, `trades`, `risk_state`, `agent_commands` all need a `wallet_id`/`user_id` dimension (schema migration).
- Isolation guarantee: the **registered competition wallet stays a separate, untouchable account** — per-user wallets must never be signable by the competition flow and vice-versa.
- Onboarding: "creating your self-custody wallet" flow → QR/address per user.

**Recommendation:** even when built, keep it behind a `MULTI_WALLET` flag, default OFF for any competition deployment.

**Detailed plan:** to be written only after Gate 0 (`2026-06-2x-per-user-wallets.md`).

---

## Optimizations (item 10) — folded in, not a separate workstream

Tracked per workstream above. Cross-cutting ones to watch:
- Non-ETH charts must not hang on "awaiting data" (Workstream E).
- Intelligence view must degrade gracefully when `SECOND_BRAIN=0` (Workstream A).
- Don't fabricate sponsor/intelligence counts — wire to real `audit`/`agentEvents` rows (Workstream A).
- New Convex queries (realized PnL, KOL list) must be indexed/bounded — no unbounded `.collect()` in hot queries (Workstreams B, D).

---

## Handoff

This roadmap locks scope and sequence. Each workstream A–E is independently shippable and has a named detailed-plan file to be written next. **Recommended:** I write the full bite-sized `superpowers:writing-plans` document for **Workstream A (Intelligence showcase, P0)** first, then B and C before the Jun 21 freeze. Tell me which workstream to detail first, or say "A then B then C" and I'll produce them in order.
