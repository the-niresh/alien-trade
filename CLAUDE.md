# Alien-Trade — Claude Instructions

## Self-check before every response

Before sending any message, verify: **does this response fully address what the user asked?**
If not, complete the missing part first, then respond.

---

## Self-check before every implementation (the win gate)

Before writing any feature or logic, ask: **"Will this feature or logic win the hackathon?!"**
Answer with exactly one of: **yes / no / maybe**.

- **yes** or **maybe** → build it. (Necessary hygiene that protects the score counts as
  **maybe** — e.g. the cockpit control-token gate: it doesn't score points, but shipping it
  avoids losing them and feeds the TWAK self-custody story. Maybe ⇒ go.)
- **no** → do **not** build it. Log the skip in one line.

If you find yourself answering **"no" to many candidate items in a row**, stop building.
That is the signal the current plan has run out of winning moves: **brainstorm** (use the
brainstorming skill), then come back to Nire with a *different* winning strategy rather than
grinding low-value work. Winning means one of: a validated, low-drawdown edge (Track 1
rubric: returns / drawdown / risk-adjusted / rule-adherence) **or** depth that lands a
stackable $2k special prize (CMC / TWAK / BNB SDK) **or** the honest falsification-log +
capital-preservation submission. Map every "yes/maybe" to one of those; if it maps to none,
it's a "no."

---

## Project Overview

**Alien-Trade** is an autonomous BSC trading agent built for **BNB Hack 2026 (DoraHacks)**.

| Key fact             | Value                                                                                               |
| -------------------- | --------------------------------------------------------------------------------------------------- |
| Primary goal         | **Win Track 1** — autonomous trading scored on risk-adjusted PnL + drawdown (Jun 22–28 live window) |
| Secondary goal       | Track 2 strategy skill (free byproduct of the backtest engine)                                      |
| Special prizes       | 3 × $2k: CMC / TWAK / BNB SDK deep usage                                                            |
| Build deadline       | **Jun 21, 2026** (feature freeze)                                                                   |
| Live trading window  | **Jun 22–28, 2026**                                                                                 |
| Submission / judging | Jun 29 – Jul 5, 2026                                                                                |
| Today                | Jun 6, 2026 — ~15 build days left                                                                   |

---

## Monorepo Layout

```
alien-trade/
  core/       # ★ THE CROWN JEWEL — strategy + signals + backtest/sim engine (Python)
  agent/      # live runtime: FastAPI + LangGraph (imports /core, zero duplicate logic)
  web/        # React + Vite + shadcn/ui + Tailwind + PWA
  convex/     # Convex schema + functions (real-time state bus + UI bridge)
  jobs/       # Trigger.dev scheduled tasks
  docs/       # STRATEGY.md, BACKTEST.md, ARCHITECTURE.md, etc.
```

---

## Tech Stack

| Layer               | Tech                                                                         |
| ------------------- | ---------------------------------------------------------------------------- |
| Strategy + Sim core | Python (numpy/pandas/Polars)                                                 |
| Live orchestration  | FastAPI + LangGraph (supervisor pattern)                                     |
| Data                | CMC Agent Hub — OHLCV + funding/OI + social/sentiment + on-chain flow        |
| Execution           | BNB AI Agent SDK — PancakeSwap spot + perps                                  |
| Signing             | Trust Wallet Agent Kit (TWAK) — self-custody, keys never in code             |
| Real-time state     | Convex — trades, decisions, ledger, audit, config, risk_state                |
| Background jobs     | Trigger.dev — scheduled loops, retries, dead-letter                          |
| Cache + Vector      | Upstash Redis + Upstash Vector — semantic cache + Second Brain index         |
| Frontend            | React + Vite + shadcn/ui + Tailwind + vite-plugin-pwa                        |
| LLM                 | Claude (tier-routed) — regime narrative, reflection, co-pilot (off hot path) |

---

## Architectural Decisions (locked — do not revisit without user confirmation)

### 1. LLM is OFF the trade hot path

The trade decision is deterministic Python in `/core`. The LLM earns its place only in:

- Regime narrative (after the deterministic detector runs)
- Post-trade reflection (async)
- Mistake-avoidance lookup (Second Brain query)
- Co-pilot chat (on demand)

Never suggest putting LLM calls in the signal computation or execution path.

### 2. Sim and live share the same `/core` code

No "sim version" vs "live version." The live agent imports `/core` directly. If they diverge, the sim is worthless. Enforce this in every code suggestion.

### 3. Hermes self-learning loop is required

After every trade, the reflection agent emits a structured reflection `{signals, regime, outcome, lesson}` → compressed and stored in Upstash Vector. Before every trade, mistake-avoidance queries Vector: "have we lost on this setup before?" → block or reduce size. This is the Hermes Agent (Nous Research) pattern applied directly. Agent improves over time without any change to `/core` strategy code.

### 4. Karpathy AutoResearch loop is required

The master LangGraph supervisor spawns a research sub-agent every N hours (async, off hot path). The sub-agent self-directs: identifies what it doesn't know (regime anomalies, social spikes, OI divergence) → queries CMC MCP + on-chain data → synthesizes a structured "market research digest" → stores in Second Brain (Upstash Vector). Both the regime detector and co-pilot query this digest. This is Karpathy's AutoResearch pattern applied to market research.

### 5. 2-year historical pre-load is required

Before go-live, run a one-time ingestion pipeline over 2 years of CMC historical data (OHLCV + funding/OI + social + on-chain). Walk-forward labels each period: `{regime, dominant_signal, outcome}`. These insights are stored as institutional memory in Upstash Vector. The agent must not be blank at launch — 2 years of context is the starting point.

### 6. Master agent (LangGraph supervisor) is for the Second Brain layer only

Sub-agents: research agent (CMC data fetch), strategist agent (regime analysis), reflection agent (post-trade learning), co-pilot agent (user queries). None of these agents make the buy/sell decision.

### 4. PWA instead of React Native mobile app

Decision: no native mobile app, no app store submission. Reasons: 16-day timeline, Apple/Google financial app review friction, rejection risk.

Mobile access via:

- Python `qrcode` lib renders ASCII QR in terminal after onboarding
- QR points to the hosted React + Vite PWA
- `vite-plugin-pwa` adds service worker + manifest → installs on home screen like a native app
- Convex real-time layer handles all mobile ↔ agent state sync — no separate webhook server

### 5. Convex is the webhook/real-time bus

Do not suggest separate webhook servers or websocket infrastructure. Convex reactive queries handle all live state (kill switch, risk caps, PnL, decisions) between the web app and the agent.

### 6. Drawdown-first optimization objective

```
maximize  Sortino_oos  −  λ * max_drawdown_oos
```

Never suggest optimizing for raw return. The judging rubric rewards risk-adjusted, low-drawdown performance over a 7-day window.

### 7. Anti-overfitting is non-negotiable

- Out-of-sample numbers only — never report or select on in-sample
- Walk-forward validation always
- 2–3 signals max, minimal knobs
- Full cost model (gas, slippage, fees, funding) in every backtest

---

## Signal Library (the alpha)

| Signal            | Source                    | Role                                             |
| ----------------- | ------------------------- | ------------------------------------------------ |
| S1 Momentum/Trend | CMC OHLCV                 | Backbone — EMA cross + ROC, ATR-normalized       |
| S2 Derivatives    | CMC funding rate + OI     | Contrarian on extremes; OI confirms/denies trend |
| S3 Sentiment      | CMC social + KOL          | Rate-of-change of attention, not absolute level  |
| S4 On-chain flow  | CMC exchange flow + whale | Net outflow = accumulation = bullish precursor   |

Start with S1 + S2 + one of S3/S4. Add the third only if it improves out-of-sample Sortino.

---

## Sponsor Layers — How They're Used

### L1: CMC Agent Hub

- Historical data pipeline → feeds backtest engine (all 4 signal types)
- Live feed with same fields → live trading loop
- CMC MCP server as a LangGraph tool for the Second Brain / co-pilot
- x402 micropayments on every CMC data call from the agent runtime

### L2: TWAK (Trust Wallet Agent Kit)

- ALL transaction signing goes through TWAK — zero raw keys in code or logs
- Covers: spot swaps, perp orders, token approvals (with amount limits)
- Multi-step sequences (e.g. margin deposit + open perp) each signed via TWAK
- Auth: `TW_ACCESS_ID` + `TW_HMAC_SECRET` (no separate wallet address — wallet managed via credentials)

### L3: BNB AI Agent SDK

> **Scoring ruling (organizer, locked):** only `twak swap` transactions count toward
> PnL — see `reference-hackathon-rules`. So the scored agent is **spot-long-only**.
> Perps (Aster/PancakeSwap) are NOT `twak swap` calls and would not count; the `raw`
> BNB-SDK signer path (`OnchainExecutor`) is dev/testnet only. Also: BNB/BTC/BTCB are
> NOT in the eligible-token list — trade the curated allowlist (ETH/CAKE/UNI/LINK/AAVE).

- Spot swaps via `twak swap` (self-custody) for long positions — the only scored path
- ~~Perps for shorts~~ — dropped from the scored path (not a `twak swap`; see ruling above)
- Slippage simulation before every send (simulate-before-send pattern)
- Gas estimation from real fills → feeds the cost model in the backtest engine
- On-chain receipt as the ledger source of truth (real fill price, real gas paid)

---

## Build Phases (current status)

| Phase                               | Dates     | Status      |
| ----------------------------------- | --------- | ----------- |
| 0 — Foundations                     | Jun 5–6   | In progress |
| 1 — Data Pipeline + Execution Spike | Jun 6–8   | Not started |
| 2 — Backtest / Sim Engine ★         | Jun 8–12  | Not started |
| 3 — Strategy & Signals ★            | Jun 11–15 | Not started |
| 4 — Risk Engine ★                   | Jun 13–16 | Not started |
| 5 — Live Runtime + Execution        | Jun 15–18 | Not started |
| 6 — Second Brain + LLM layer        | Jun 16–19 | Not started |
| 7 — Paper Rehearsal + Mainnet       | Jun 18–21 | Not started |
| Live window                         | Jun 22–28 | —           |

---

## Key Files

| File                   | Purpose                                                       |
| ---------------------- | ------------------------------------------------------------- |
| `docs/PROJECT_PLAN.md` | Full plan, architecture, phases, risk register                |
| `docs/STRATEGY.md`     | Signal spec, combination logic, regime detection, risk engine |
| `docs/STEPS.md`        | Ordered build runbook with checkboxes                         |
| `CLAUDE.md`            | This file — instructions + locked decisions                   |

---

## Dev Commands (reference)

| Command                                                     | Where to run               | What it does                                              |
| ----------------------------------------------------------- | -------------------------- | --------------------------------------------------------- |
| `bunx convex dev`                                           | repo root (`alien-trade/`) | Start Convex dev server — looks for `convex/` folder here |
| `cd core && .\.venv\Scripts\python.exe -m pytest tests/ -v` | repo root                  | Run `/core` backtest tests                                |
| `cd core && uv pip install -e .`                            | `core/`                    | Re-install after pyproject.toml changes                   |

---

## Live Ops — deployed on this VPS (2026-06-11)

**Key fact:** Claude Code runs **ON the target VPS** (`76.13.243.12`, host `ai`,
Ubuntu 24.04, root). Deploy is **local — no SSH**. The repo runs in place at
`/root/claude/projects/alien-trade` with the `core/.venv` Python (`uv`-built).
`.env.local` is loaded by `agent/config.py` via an absolute path, so cwd doesn't matter.

### Running services (systemd, all `enabled` = survive reboot)

| Unit                   | What it does                                                              | Logs |
| ---------------------- | ------------------------------------------------------------------------ | ---- |
| `alien-trade.service`  | 24/7 paper runtime, 1 h cadence, autopilot on, `Restart=always`          | `/var/log/alien-trade.log` |
| `alien-cockpit.service`| Cockpit PWA (Vite) on `0.0.0.0:4173` → reads Convex `festive-newt-1`      | `/var/log/alien-cockpit.log` |
| `alien-digest.timer`   | Fires `python -m agent.digest` hourly at `:07` → Telegram summary         | `/var/log/alien-digest.log` |

### Operating commands

```bash
systemctl status alien-trade --no-pager        # is the agent running?
tail -f /var/log/alien-trade.log               # live decision/audit lines (JSON)
systemctl restart alien-trade                   # after a git pull / .env.local change
core/.venv/bin/python -m agent.digest --stdout  # preview the hourly digest now
systemctl list-timers alien-digest --no-pager   # when does the next digest fire?
```

### Cockpit + alerts

- **UI:** http://76.13.243.12:4173/ (VPS). Production build is `vite build` only
  (`bun run build`); `tsc -b` moved to `bun run typecheck` (was blocking on non-fatal
  `noImplicitAny`). Vercel-ready (`web/vercel.json`) — deploy needs `vercel login`.
- **Telegram:** the agent's built-in two-way bot (`agent/notify.py`, wired in
  `runtime.py`) sends per-event alerts (equity-floor / kill-switch / autopilot-bank)
  and accepts `/status /halt /resume /pause`. Set `TELEGRAM_BOT_TOKEN` +
  `TELEGRAM_CHAT_ID` in `.env.local`, then `systemctl restart alien-trade`. The hourly
  `agent/digest.py` uses the same creds. Absent creds → both no-op (digest prints to log).

### Known follow-ups

- Stale ledger rows from earlier local runs are still in Convex (equity ≈ $9,831,
  drawdown −1.92%). Reset before the clean 8-day corpus if a fresh start is wanted.
- Second Brain (Hermes reflection / co-pilot) is OFF (`SECOND_BRAIN=0`): `cd core &&
  uv pip install langgraph anthropic upstash-redis upstash-vector`, flip the unit to
  `SECOND_BRAIN=1`, restart. Upstash + Anthropic keys are already in `.env.local`.
- `core/data/parquet/` historical files are absent → 4 `TestDataLoader` tests fail
  (data-availability only; 176/180 logic tests pass). Live loop uses the Binance feed.

---

## What NOT to Suggest

- LLM calls in the signal computation or trade execution path
- Native React Native mobile app or app store submission
- Separate webhook server (Convex handles it)
- In-sample backtest numbers as a decision basis
- Optimizing for raw return over risk-adjusted return
- Different code paths for sim vs live
- More than 2–3 trading signals (overfit risk)
- Frictionless backtests (no cost model)

<!-- convex-ai-start -->

This project uses [Convex](https://convex.dev) as its backend.

When working on Convex code, **always read
`convex/_generated/ai/guidelines.md` first** for important guidelines on
how to correctly use Convex APIs and patterns. The file contains rules that
override what you may have learned about Convex from training data.

Convex agent skills for common tasks can be installed by running
`npx convex ai-files install`.

<!-- convex-ai-end -->
