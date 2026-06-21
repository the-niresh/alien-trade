# Spec — Autonomous AI Trading Concierge + Product Surface

**Date:** 2026-06-19
**Author:** Nire (design w/ Claude)
**Target builder:** Sonnet
**Status:** Approved design → ready to plan/build
**Freeze:** Jun 21, 2026 (live window Jun 22–28)

---

## 0. Read this first

This is a **live mainnet trading agent**. Two rules override everything below:

1. **LLM stays off the buy/sell hot path** (locked decision #1). The chat concierge
   NEVER decides a trade. It only mutates **config / commands / feedback**; the
   deterministic `/core` loop reads those and acts. The model *proposes* an action;
   a **token-gated Convex mutation** *executes* it.
2. **All writes are token-gated** (`withToken(...)` on the client, `assertControlToken`
   on the server). Money-moving or risk-changing actions require an explicit in-chat
   **confirmation card**. Withdraw double-confirms the destination address.

If a change would violate either rule, stop and flag it.

---

## 1. The reframe

We already have the autonomous *trader*: the deterministic `/core` loop running live on
the VPS (`alien-trade.service`). This work builds the autonomous *product surface*
around it — the entry point, an action-taking chat, and the trackers / deposit /
withdraw panels that make autonomy usable and visible.

**"Remembers and acts next time without asking"** needs **no new memory subsystem**.
A preference written to `config` / `config.autopilot` is read by the loop **every
cycle, permanently**. A `trade_feedback` row feeds mistake-avoidance. That IS the memory.

---

## 2. Existing plumbing the concierge reuses (do not rebuild)

| Need | Convex API (already exists) | Notes |
|------|------------------------------|-------|
| Read live config | `api.config.get` (query) | risk caps, mode, strategy, autopilot |
| Halt / resume | `api.config.setHalted` + `api.agentControl.set` | mirror both (see `App.tsx onKillToggle`) |
| Risk caps / size | `api.config.updateLimits` (mutation) | token-gated |
| Strategy pick | `api.config.setStrategy` (mutation) | momentum\|contrarian\|balanced\|defensive |
| Profit-taking / principal protect | `api.config.setAutopilot` (mutation) | `autopilot` object on config |
| Mark setup good/bad | `api.feedback.record` (mutation) | feeds `core/risk/feedback.py` |
| TWAK-signed ops queue | `api.agentCommands.enqueue` (mutation) + `api.agentCommands.list` (query) | `command_type` + `params` JSON |
| Open positions | `api.positions.open` / `api.positions.all` (queries) | qty≠0 = ongoing |
| Q&A | `api.copilot.ask` (action) → agent `POST /copilot` | extend with optional `action` |
| Wallet balances | `api.walletState.*` | balances only; **address must be added** (§7) |

`api.agentCommands.enqueue` signature (real): `{ control_token, command_type, params (JSON string), queued_by? }`.

---

## 3. Units to build (8)

### Unit 1 — `StartTradingCTA` (entry point)
- Prominent **"Start Trading with AI"** primary button.
- Placement: Overview hero / empty state (primary), plus keep the existing sidenav bot
  icon as the persistent entry. Match the visual weight of the reference
  `trade with ai.png` CTA.
- Behavior:
  - First run (`!hasTourBeenSeen()`) → run onboarding tour, then open concierge chat
    with suggestion cards.
  - Returning → open concierge chat directly.
- Files: new `web/src/components/StartTradingCTA.tsx`; wire from `OverviewView.tsx` and
  `App.tsx` (reuse `setCopilotOpen`, `startTour`).

### Unit 2 — Concierge chat (the heart)
Upgrade `CoPilotDrawer` + the `/copilot` flow from Q&A into a **tool-using concierge**.

**Action model (client-authoritative execution):**
- The chat can propose a `ProposedAction`:
  ```ts
  type ProposedAction =
    | { type: "set_strategy"; params: { strategy_name: string }; summary: string }
    | { type: "update_limits"; params: { max_position_usd?: number; daily_loss_limit_usd?: number; max_drawdown_pct?: number; equity_floor?: number }; summary: string }
    | { type: "set_autopilot"; params: { /* matches config.autopilot shape */ }; summary: string }
    | { type: "halt" | "resume"; params: {}; summary: string }
    | { type: "mark_setup"; params: { setup_key: string; cycle_id: string; symbol: string; label: "good" | "bad"; note?: string }; summary: string }
    | { type: "withdraw"; params: { to_address: string; amount: number; token: string }; summary: string }
    | { type: "deposit_info"; params: {}; summary: string };   // just surfaces the deposit panel
  ```
- **HITL:** any action EXCEPT a read-only answer renders an **action confirmation card**
  in the message stream (summary + Confirm / Cancel). On **Confirm**, the client calls
  the matching token-gated mutation (table in §2). On **Cancel**, nothing executes.
  - `withdraw` adds a second confirmation showing the full destination address verbatim.
- **Where intents come from (reliability tiers):**
  1. **Suggestion cards (Unit 3) → deterministic `ProposedAction` built client-side.**
     The demo path must NOT depend on the LLM or the agent server being up.
  2. **Free text → `api.copilot.ask`.** Extend agent `POST /copilot` to optionally
     return `action: ProposedAction | null` alongside `answer`. If the agent is offline
     or returns no action, fall back to a small **client-side deterministic grammar**
     for the common verbs ("go conservative/defensive", "halt", "resume",
     "take profit", "set size to $N", "withdraw N USDT to 0x…").
- **Memory:** once a `ProposedAction` writes to `config`/`autopilot`, the loop honors it
  every cycle — that is the "acts next time" behavior. No extra storage in v1.
- Files: `web/src/components/CoPilotDrawer.tsx` (render action cards + confirm flow);
  new `web/src/lib/concierge.ts` (deterministic intent grammar + `ProposedAction`→mutation
  router, pure + unit-tested); agent `/copilot` endpoint (add optional `action`).

### Unit 3 — Suggestion cards
Replace the four Q&A chips (`CHIPS` in `CoPilotDrawer.tsx`) on the empty state with
**action starters** mirroring `chat window.png`:
- "🛡️ Start a conservative run" → proposes `set_strategy: defensive` (+ sensible caps).
- "🎚️ Adjust risk & size" → opens a guided mini-flow → `update_limits`.
- "💰 Take some profit" → proposes `set_autopilot` (profit target) or a `withdraw` draft.
- "📊 Check performance" → read-only answer (reuse Q&A path; routes to scorecard summary).
- "➕ Type my own…" → focuses the input.

Each card with a side effect goes through the Unit 2 confirmation card.

### Unit 4 — `TrackersView` (ongoing / to-do)
New view (`trackers.png`). New `View` value `"trackers"` in `SideNav.tsx` + render in `App.tsx`.
- **Ongoing:** open positions (`api.positions.open`, qty≠0) + running commands
  (`api.agentCommands.list` where `status` ∈ {running}).
- **To-do / Pending:** queued commands (`status === "queued"`) + the next planned action
  from the latest `api.decisions.*` (target_position / verdict).
- Read-only. Empty state: "No active trades — the agent is watching the market."
- Files: new `web/src/views/TrackersView.tsx`; reuse `PositionCard`.

### Unit 5 — Deposit panel
Self-custody deposit (`deposit.png`):
- Tabs/sections: **Deposit** (wallet address QR + copy) and **Buy** (onramp link-out).
- Wallet address from a query (§7), never hardcoded.
- "Buy crypto" = external onramp link in v1 (full provider integration is follow-up, §9).
- Files: new `web/src/views/DepositView.tsx` (or a modal opened from the header
  `Deposit`-style button + from the "deposit_info" action). Reuse the `qrcode` lib
  already imported in `App.tsx`.

### Unit 6 — Withdraw
- Form: token, amount, destination address → HITL confirm (with address echo) →
  `api.agentCommands.enqueue({ command_type: "withdraw", params: JSON.stringify({ to_address, amount, token }) })`.
- **Backend:** add a `withdraw` handler to the existing **agent command worker** (the
  loop that drains `agent_commands`; locate it under `agent/` — it already handles other
  `command_type`s). It must:
  - validate the address + amount,
  - sign/send the transfer via TWAK (`agent/twak_cli.py`),
  - write the result/tx hash back via `api.agentCommands.updateStatus`,
  - append an `audit` + `agent_events` row.
- Validate params with zod on the client before enqueue.

### Unit 7 — Post-trade tour
- Second driver.js tour in `web/src/lib/tour.ts`: `startPostTradeTour()` covering
  "take profit", "withdraw", and "read your tracker".
- Trigger: when the live `trades` count goes **0 → 1** (watch `api.trades.*`), once,
  guarded by its own localStorage key (`alien-trade:posttrade-tour-seen-v1`). Replayable
  from the tour button.

### Unit 8 — Logo fix
- The clipped logo is in `LiveHeader.tsx:42` (`<img src="/logo.png" className="logo-blend w-7 h-7" />`).
- Fix sizing/aspect so the full mark shows (likely `object-contain` + correct box, or a
  wider box). Verify against `docs/logo.png`. Also confirm the pairing-screen logo
  (`App.tsx:93`, `w-20 h-20`) renders fully.

---

## 4. Data flow (concierge action)

```
User clicks suggestion card / types text
        │
        ├─ suggestion card → deterministic ProposedAction (concierge.ts)
        └─ free text → api.copilot.ask → agent /copilot → { answer, action? }
                                   │ (offline/no action) → deterministic grammar fallback
        ▼
ProposedAction?  ── no ──▶ render assistant answer (read-only)
        │ yes
        ▼
Render ACTION CONFIRMATION CARD (summary, Confirm/Cancel; withdraw: + address echo)
        │ Confirm
        ▼
Client calls token-gated mutation (config.* | agentControl.set | feedback.record | agentCommands.enqueue)
        ▼
Convex state changes → /core loop reads next cycle → trackers/overview update reactively
```

The LLM never touches execution. It maps language → a structured proposal; Convex
mutations are the only thing that mutates state.

---

## 5. File-change summary

**New (web):** `components/StartTradingCTA.tsx`, `views/TrackersView.tsx`,
`views/DepositView.tsx`, `lib/concierge.ts` (+ `lib/concierge.test.ts`).
**Edit (web):** `components/CoPilotDrawer.tsx`, `components/SideNav.tsx`,
`components/LiveHeader.tsx`, `views/OverviewView.tsx`, `lib/tour.ts`, `App.tsx`.
**Edit (convex):** add wallet-address query (§7); confirm `agentCommands` covers withdraw enqueue.
**Edit (agent):** `/copilot` endpoint (optional `action`); command worker `withdraw` handler.

Keep every new file < 400 lines; extract helpers if a view grows.

---

## 6. HITL confirmation contract (explicit)

- **No confirmation:** read-only answers, opening the deposit panel.
- **Single confirmation:** `set_strategy`, `update_limits`, `set_autopilot`, `halt`,
  `resume`, `mark_setup`.
- **Double confirmation (address echo):** `withdraw`.
- Confirmation cards must show the **exact resulting state** ("size $4 → $8",
  "strategy contrarian → defensive"), not a vague paraphrase.

---

## 7. Wallet address source (must fix — no hardcoding)

`wallet_state` has balances but no address. Add a query that returns the self-custody
address from the environment (the agent already knows it; e.g. `WALLET_ADDRESS` /
derivable via TWAK). Options, in order of preference:
1. Add `address` to the `wallet_state` row written by the agent each cycle, expose via
   `api.walletState`.
2. New `convex/wallet.ts` query reading `process.env.WALLET_ADDRESS`.

The cockpit reads the address from this query for Deposit (QR) and to pre-fill nothing in
Withdraw (the user types/pastes the destination). Address from CLAUDE.md for reference
only: `0x485Ec1b615369d8a6dFb452471C4994f2e4d062d` — **do not hardcode it in the UI.**

---

## 8. Testing

- **Unit (Vitest):**
  - `concierge.ts`: text → `ProposedAction` for each verb; unknown text → null (read-only).
  - `ProposedAction` → correct mutation + args mapping.
  - withdraw param validation (zod): rejects bad address / non-positive amount.
  - Trackers categorization: positions/commands bucketed into ongoing vs to-do.
- **Backend:** withdraw command handler — happy path (status→done, tx hash) and
  validation failure (status→failed, error set), TWAK call mocked.
- **Manual / demo:** Start CTA → tour → suggestion card → confirmation card → confirm →
  config/tracker update; offline-agent fallback still lets the demo path work.

Respect repo testing norms (`core/.venv` pytest for Python, web Vitest where configured).

---

## 9. Sequencing (freeze-aware) & out of scope

**Build order:**
1. **Spine (demo-critical):** Unit 8 (logo) → Unit 1 (CTA) → Units 2+3 (concierge +
   suggestion cards + HITL, config/halt/feedback actions only) → Unit 4 (Trackers) →
   Unit 7 (post-trade tour).
2. **Money movement (self-custody story):** Unit 5 (Deposit) → Unit 6 (Withdraw incl.
   backend handler).

**Out of scope / explicit "no" (would fail the win-gate or isn't feasible by Jun 21):**
- Real fiat onramp/provider integration — v1 is a link-out only.
- KOL/wallet trackers, Twitter/social feeds, "spawn multiple bots", Yield, Rewards tabs
  (these belong to a multi-bot sniper, not our single autonomous agent).
- Any path that lets the chat place/close trades without the deterministic loop.

---

## 10. Win-gate mapping

- Concierge + Trackers + Start CTA → the **autonomous-agent demo narrative** (yes).
- Deposit/Withdraw via TWAK-signed commands → **TWAK self-custody $2k story** (maybe → go).
- Logo + tours → demo polish that protects the score (maybe → go).
- Everything respects locked decisions #1, #2, #6 and the drawdown-first objective.
