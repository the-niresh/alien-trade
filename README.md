# Alien-Trade

> Autonomous BSC trading agent — BNB Hack 2026 (DoraHacks), Track 1 + Track 2 + 3× special prizes.
> Scored on **risk-adjusted PnL + max drawdown** over a live 7-day window (Jun 22–28, 2026).

---

## What it is

An autonomous on-chain agent that reads multi-signal market data, makes self-custody trades through Trust Wallet Agent Kit, learns from every outcome, and runs 24/7 without operator intervention.

The objective is not raw return. The scoring rubric rewards **Sortino − λ·max_drawdown**. Every design decision traces back to that: drawdown-first sizing, cash-default posture, walk-forward-validated signals only, and a self-learning loop that blocks re-entry on setups where the agent has lost before.

```
maximize  Sortino_oos − λ · max_drawdown_oos          (long-only, spot)
```

Only `twak swap` trades count toward scored PnL. Eligible tokens: `ETH, CAKE, UNI, LINK, AAVE`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       LangGraph Supervisor                           │
│  Researcher ──► Strategist ──► Reflector ──► Historian (Co-pilot)   │
└───────────────────────┬─────────────────────────────────────────────┘
                        │  advisory only — never on the trade path
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  /core — Deterministic Python                        │
│  S1 Momentum  S2 Derivatives  S3 Sentiment  S4 On-chain Flow        │
│  RegimeDetector ──► SignalCombiner ──► RiskEngine ──► Order         │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
          ┌─────────────▼──────────────┐
          │   TwakSwapExecutor (TWAK)  │  ← self-custody, zero raw keys
          │   simulate → sign → send   │
          └─────────────┬──────────────┘
                        │ on-chain receipt
          ┌─────────────▼──────────────┐
          │      Convex (real-time)    │  ← trades, decisions, ledger,
          │      state bus + UI bridge │     risk_state, config, audit
          └─────────────┬──────────────┘
                        │
          ┌─────────────▼──────────────┐
          │    Glass Cockpit (PWA)     │  ← React + Vite, installs on
          │    76.13.243.12:4173       │     home screen via service worker
          └────────────────────────────┘
```

**Core design rule:** the LLM never touches the trade decision. It earns its place in regime narrative, post-trade reflection, mistake-avoidance lookup, and co-pilot chat — all async, all off the hot path. Sim and live run the **same** `/core` code — no divergence.

---

## Signal stack

| Signal | Source | Role |
|--------|--------|------|
| S1 Momentum | Binance OHLCV | EMA cross + ROC, ATR-normalized |
| S2 Derivatives | Binance Futures (funding rate + OI) | Contrarian on extremes; OI confirms/denies |
| S3 Sentiment | CMC social + KOL via Skill Hub | Rate-of-change of attention |
| S4 On-chain flow | CMC exchange flow + whale | Net outflow = accumulation = bullish |

Walk-forward validated on 2 years of data. Out-of-sample only — no in-sample numbers anywhere in this repo.

---

## Sponsor integrations

### L1 — CoinMarketCap Agent Hub
- Live S3 + S4 signals via CMC Skill Hub (curated 8-skill loader + dynamic `find_skill` fallback)
- x402 micropayments on every live CMC data call (`POST /skill/signal_score` — $0.01 USDC on Base)
- Track 2 skill published to CMC Skills Marketplace (`unique_name: alien_trade_multi_signal_score`)
- Research agent queries CMC MCP for macro digests (Karpathy AutoResearch pattern)

### L2 — Trust Wallet Agent Kit (TWAK)
- ALL transaction signing through TWAK — zero raw private keys in code or logs
- Covers: spot swaps, token approvals with amount limits, multi-step sequences
- On-chain registration: `python -m agent.twak_cli compete_register`
- `TwakSwapExecutor`: simulate-before-send → sign via TWAK → broadcast → receipt

### L3 — BNB AI Agent SDK
- Spot swaps via `twak swap` (the only scored path per organizer ruling)
- Slippage simulation before every send
- Gas estimation from real fills feeds the backtest cost model
- On-chain receipt = ledger source of truth (real fill price, real gas paid)

---

## Self-learning loop (Hermes pattern)

After every trade:
```
fill receipt → ReflectionWriter → {signals, regime, outcome, lesson} → Upstash Vector
```

Before every trade:
```
"have we lost on this setup before?" → Vector similarity search → block or reduce size
```

The agent improves over the 7-day live window without touching `/core` strategy code. Two years of pre-loaded historical context (walk-forward labeled) means it starts with institutional memory, not a blank slate.

---

## Risk engine

- **Drawdown kill switch** — daily loss limit hard-stops all trading
- **Equity floor guard** — warns at 90%, halts at 80% of starting equity
- **Regime gate** — no long entries in CRASH or CHOP regimes
- **Vol-targeted sizing** — position size = `risk_budget / (ATR × price)`
- **Activity floor** — ≥1 `twak swap` per day (qualification requirement)
- **Cash-default posture** — holds USDT when no high-conviction setup; zero drawdown while flat
- **Simulate-before-send** — every order dry-runs through BNB SDK before signing

All caps are live-adjustable via the cockpit UI sliders without restarting the agent.

---

## Glass cockpit

Live at `http://76.13.243.12:4173` — installable as a PWA (add to home screen).

| Panel | What it shows |
|-------|---------------|
| Overview | Equity curve, drawdown, Sortino, win rate, regime badge |
| Positions | Open positions, entry price, unrealized PnL, sparklines |
| Agents | Live roster — Researcher / Strategist / Reflector / Historian with activity states |
| Controls | Kill switch (hold-to-confirm), risk-cap sliders, trading mode toggle, run triggers |
| Logs | Real-time decision + audit JSON feed |
| Co-pilot | Chat with the agent's Second Brain — cited answers from reflection history |

**Two-way Telegram control** — the agent sends per-event alerts (equity floor, kill-switch, daily summary) and responds to `/status` `/halt` `/resume` `/pause`.

---

## Quick start

```bash
bash install.sh
```

The wizard checks deps (Python ≥3.11, uv, bun, twak), writes `.env.local`, probes Convex, and prints launch instructions with a scannable QR for the cockpit.

**Manual:**

```bash
# Python core
cd core && uv venv && uv pip install -e . && .venv/bin/pytest tests/ -q

# Convex — keep running (real-time state bus)
bunx convex dev

# Cockpit
cd web && bun install && bun run dev

# Agent
python -m agent.runtime
```

**Reproduce the out-of-sample backtest report:**
```bash
cd core && .venv/bin/python -m report
```

---

## Live operations (VPS, 24/7)

| Unit | Role | Logs |
|------|------|------|
| `alien-trade.service` | 24/7 runtime, 1h cadence, autopilot on | `/var/log/alien-trade.log` |
| `alien-cockpit.service` | cockpit PWA on `:4173` | `/var/log/alien-cockpit.log` |
| `alien-digest.timer` | hourly Telegram digest | `/var/log/alien-digest.log` |

```bash
systemctl status alien-trade --no-pager
tail -f /var/log/alien-trade.log
systemctl restart alien-trade
```

---

## Monorepo

```
alien-trade/
  core/       # ★ strategy + signals + backtest/sim engine (Python)
  agent/      # live runtime: FastAPI + LangGraph (imports /core, no duplicate logic)
  web/        # React + Vite + shadcn/ui + Tailwind + PWA
  convex/     # schema + functions (real-time state bus)
  jobs/       # Trigger.dev scheduled tasks
  docs/       # STRATEGY.md, BACKTEST.md, ARCHITECTURE.md, STEPS.md
```

---

## Key docs

- [`docs/STRATEGY.md`](docs/STRATEGY.md) — signal spec, regime detection, anti-overfitting protocol
- [`docs/AWAKE_SPRINT.md`](docs/AWAKE_SPRINT.md) — sprint design + thesis-factory loop
- [`docs/VALIDATION_1H.md`](docs/VALIDATION_1H.md) — honest out-of-sample results
- [`docs/STEPS.md`](docs/STEPS.md) — full build runbook (every step, every decision)
- [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) — full architecture, phases, risk register

---

## Tracks + prizes

| Target | Evidence |
|--------|----------|
| **Track 1** — autonomous trading (PnL scored Jun 22–28) | Live agent on BSC mainnet, full Convex audit trail |
| **Track 2** — strategy skill | `POST /skill/signal_score` + CMC Marketplace manifest |
| **CMC special prize** | Skill Hub + x402 micropayments live on every data call |
| **TWAK special prize** | All signing via TWAK, `compete_register`, zero raw keys |
| **BNB SDK special prize** | Spot execution, simulate-before-send, on-chain receipt ledger |

---

## Compliance gates

- ✅ On-chain registration via `twak compete register` before Jun 22
- ✅ Only `twak swap` trades count toward PnL (organizer ruling, locked)
- ✅ Eligible tokens only: `{ETH, CAKE, UNI, LINK, AAVE}`
- ✅ Activity floor: ≥1 trade/day (`enforce_activity_floor`)
- ✅ Portfolio > $1 at all times (equity floor guard)
