# Alien-Trade — Build Steps (Track-1-First Runbook)

> Ordered, checkable steps. Companion to `PROJECT_PLAN.md` and `STRATEGY.md`.
> **Goal: win Track 1 on risk-adjusted PnL + drawdown.** The backtest engine and the strategy are the crown jewels — everything else serves them.
> Rule: a thin end-to-end slice (signal → sim → testnet trade) must work by Day 6.

Legend: 🔴 blocker / must-pass · 🟡 important · 🟢 polish · ⏱ timebox · ★ wins-the-track

---

## STEP 0 — Foundations (Jun 5–6)

- [x] 🔴 Monorepo layout created: `core/signals core/backtest core/exec core/risk core/data agent/ web/ convex/ jobs/ docs/`. Planning docs moved to `docs/`. `CLAUDE.md` stays at root.
- [x] 🔴 Secrets: `.gitignore` (covers `.env.local`, raw data, pycache, node_modules). `.env.example` with all keys: CMC, TWAK, BNB SDK, Upstash Redis+Vector, Convex, Trigger.dev, LLM, x402, TRADING_MODE, TOKEN_ALLOWLIST.
- [x] 🔴 Provision Convex ✅, Upstash Redis ✅, Upstash Vector ✅ (BAAI/bge-small-en-v1.5, Cosine). Trigger.dev deferred to Step 5.
- [x] 🔴 Convex schema v0: `trades, decisions, reflections, ledger, audit, config, risk_state, signals` — deployed. `convex ^1.40.0` in package.json. Run `bunx convex dev` from repo root to keep schema live.
- [x] 🔴 `/core` test harness: `core/backtest/engine.py` + `core/tests/test_backtest_harness.py` — **6/6 passing**. Tests: no-look-ahead, cost deduction, metrics keys, mark-to-market, uptrend return.
- [x] 🔴 `core/pyproject.toml` Python env: uv venv created at `core/.venv`, all deps installed. Run tests: `cd core && .\.venv\Scripts\python.exe -m pytest tests/ -v`

### Provisioning checklist
- [x] `uv` v0.11.19
- [x] `.env.local` created and filled (CMC pending, TWAK: TW_ACCESS_ID + TW_HMAC_SECRET, Upstash done, Convex done)
- [x] Convex deployed — schema live
- [x] Upstash Redis provisioned
- [x] Upstash Vector provisioned (BAAI/bge-small-en-v1.5, 384 dims, Cosine)
- [x] Trigger.dev provisioned — `TRIGGER_API_KEY` in `.env.local`

- ✅ **Exit:** repo boots; `/core` runs a dummy backtest; all 3 sponsor SDKs install + authenticate.

---

## STEP 1 — Data Pipeline + Execution Spike (Jun 6–8)  *(de-risk both ends)*

- [x] 🔴 ★ **OHLCV HISTORICAL** — `core/data/binance_client.py`: 2-year daily for BNB/BTC/ETH cached to `core/data/parquet/`. Schema matches Bar exactly. CMC OHLCV endpoint returns 403 (needs Pro tier) — **blocker: upgrade CMC key or confirm Agent Hub endpoint covers historical**. Binance is the working fallback.
- [x] 🔴 **CMC LIVE feed** — `core/data/cmc_client.py`: live quotes working (BNB ~$572). Same fields as Bar (extended fields stubbed 0.0 until CMC Agent Hub endpoint confirmed). x402 header infra ready.
- [x] 🔴 **L3 BNB SDK** — `core/exec/bnb.py`: simulate-before-send pipeline, PancakeSwap V3 calldata encoding, BSC testnet RPC reachable (chain 97, gas 0.1 gwei). Signed broadcast wired — needs funded testnet wallet via TWAK to complete a live trade.
- [x] 🔴 **L2 TWAK** — `core/exec/twak.py`: HMAC-SHA256 signing utility built and tested. `TW_ACCESS_ID` + `TW_HMAC_SECRET` confirmed in env. Live API call pending TWAK endpoint confirmation.
- [ ] 🟡 Validate **x402** pay-per-call (X402_SECRET empty — get from CMC/TWAK portals).
- [x] 🟡 Every adapter: typed I/O, timeouts, error mapping, retry hooks (tenacity).
- ⏱ **Timebox 2.5 days.** SDK fights back → log blocker, ask in Builder Telegram, move on.
- ✅ **Exit:** historical dataset on disk (730 bars × 3 symbols); CMC live quote working; BNB exec + TWAK signing infra proven. **Actual on-chain testnet trade pending TWAK endpoint doc.**

### Step 1 blockers / open items
- ⚠️ **CMC OHLCV 403**: key needs Pro tier OR confirm `CMC_MCP_ENDPOINT` covers historical pulls
- ⚠️ **TWAK API endpoint**: confirm exact URL + sign format from TWAK portal/docs
- ⚠️ **BNB_SDK_API_KEY**: empty — if official BNB AI Agent SDK needs it, get from BNB portal
- ⚠️ **X402_SECRET**: empty — get shared secret from CMC/TWAK hackathon portal

---

## STEP 2 — Backtest / Simulation Engine (Jun 8–12) ★ **CENTERPIECE**

- [ ] 🔴 Event-driven backtester over the historical dataset. **Strict point-in-time access — zero look-ahead bias.**
- [ ] 🔴 **Cost model:** BSC gas, size-aware AMM slippage, swap fees, perp funding, fill latency. (A sim without costs lies.)
- [ ] 🔴 ★ **Walk-forward harness:** optimize on window N → validate on untouched window N+1 → roll. **Never report in-sample.**
- [ ] 🔴 **Metrics:** total return, Sharpe, **Sortino**, **max drawdown**, **Calmar**, win rate, turnover, **rule-adherence score** (mirror judging rubric).
- [ ] 🟡 Regime-sliced reporting: trend / chop / high-vol / crash evaluated separately.
- [ ] 🟡 Deterministic + seeded; one command reproduces a full report from clean clone.
- ✅ **Exit:** run any strategy through walk-forward and print **honest out-of-sample, cost-inclusive** metrics.

---

## STEP 3 — Strategy & Signals (the alpha) (Jun 11–15)  *(overlaps Step 2)*

- [ ] 🔴 ★ Implement signal library (see `STRATEGY.md`), each independently testable:
  - [ ] momentum / trend (price TA)
  - [ ] sentiment / social (CMC)
  - [ ] derivatives: funding rate + open interest (CMC)
  - [ ] on-chain flow (CMC)
- [ ] 🔴 **Regime detector** (trend vs chop vs high-vol) — deterministic first.
- [ ] 🔴 ★ Combine **2–3 orthogonal signals** into one strategy. Resist extra knobs.
- [ ] 🔴 Walk-forward optimize; select for **parameter stability**, not the peak.
- [ ] 🟡 Per-signal attribution: which signal contributes which edge (kill dead weight).
- ✅ **Exit:** strategy with **positive, stable, out-of-sample** risk-adjusted returns net of costs across regimes.

---

## STEP 4 — Drawdown-First Risk Engine (Jun 13–16)  ★

- [ ] 🔴 **Position sizing:** volatility targeting / capped fractional-Kelly (size down as vol rises).
- [ ] 🔴 **Hard guardrails (code):** per-trade cap, **daily-loss → halt**, max open exposure, slippage cap, token allowlist.
- [ ] 🔴 **Regime gating:** size down / sit out in bad or uncertain regimes.
- [ ] 🟡 **Mistake-avoidance:** "lost on this exact setup before?" lookup → block/penalize.
- [ ] 🔴 ★ Re-run walk-forward with **objective = risk-adjusted return − hard drawdown penalty** (not raw return).
- ✅ **Exit:** risk engine cuts max drawdown in sim at minimal return cost; daily-loss kill verified.

---

## STEP 5 — Live Runtime + Execution Reliability (Jun 15–18)

- [ ] 🔴 Live decision loop importing the **same `/core` strategy** (no duplicate logic) on the live feed.
- [ ] 🔴 **Executor:** simulate-before-send → sign (TWAK) → send (BNB) → on-chain confirm → ledger reconcile. **Idempotency keys.**
- [ ] 🔴 **Trigger.dev:** scheduled scan, trade-status monitor, reflection job. Retries+backoff, dead-letter, alerts.
- [ ] 🔴 **Kill switch:** UI → Convex `config.halted` → agent halts within one cycle. Circuit breaker.
- [ ] 🟡 **Web dashboard (PWA):** React + Vite + `vite-plugin-pwa` — mobile-responsive; manifest + service worker so it installs on home screen. No app store needed.
- [ ] 🟡 **QR code in terminal:** after onboarding, Python `qrcode` lib renders ASCII QR pointing to the hosted PWA URL. User scans → mobile dashboard loads instantly.
- [ ] 🟡 **Mobile controls via Convex:** kill switch, risk cap adjustments, PnL/drawdown live view all go through Convex real-time — no separate webhook server required.
- [ ] 🟡 Every cycle writes a `decision` row (data snapshot, signals, regime, sizing, verdict, outcome).
- [ ] 🟡 **Chaos test:** kill switch mid-trade, failed tx, API timeout, risk veto → no double-execution.
- ✅ **Exit:** live testnet trade matches what the sim would have done; failure modes clean.

---

## STEP 6 — Second Brain + LLM Layer (Jun 16–19)  *(small, off hot path)*

- [ ] 🔴 **Hermes self-learning loop:**
  - After every trade: reflection agent emits structured reflection `{signals, regime, outcome, lesson}` → compressed → Upstash Vector.
  - Before every trade: mistake-avoidance queries Vector — "lost on this setup before?" → block or penalize size.
  - Agent improves over time. Zero changes to `/core` strategy code.
- [ ] 🔴 **2-year historical pre-load (one-time, before go-live):**
  - Run ingestion pipeline over the full 2-year CMC dataset (OHLCV + funding/OI + social + on-chain).
  - Walk-forward labels each period: `{regime, dominant_signal, outcome}`.
  - Store as institutional memory in Upstash Vector — agent is not blank at launch.
- [ ] 🔴 **Karpathy AutoResearch loop (async, every N hours):**
  - Master LangGraph supervisor spawns a research sub-agent.
  - Agent self-directs: identifies what it doesn't know (regime anomalies, social spikes, OI divergence) → queries CMC MCP + on-chain data → synthesizes a "market research digest" → stores in Second Brain.
  - Regime detector and co-pilot both query this digest.
- [ ] 🟡 **Token optimization:** model router (T0/T1/T2), semantic cache (Redis), structured outputs + `max_tokens`, prompt caching.
- [ ] 🟡 **Cost telemetry:** per-call `{tier, in/out tokens, cost, cache_hit, latency}`; running $ saved vs naive baseline.
- [ ] 🔴 **Co-pilot chat** grounded in Second Brain ("why this trade?", "what regime?", "what did the last 2 years teach us about this setup?").
- ✅ **Exit:** co-pilot answers cheaply from memory; a stored reflection demonstrably changes a later decision; 2-year institutional memory is queryable; AutoResearch loop runs one full cycle end-to-end.

---

## STEP 7 — Paper Rehearsal + Mainnet Readiness (Jun 18–21)

- [ ] 🔴 ★ **Multi-day live PAPER run** on the real feed (no capital). Does live track the sim? Reconcile drift.
- [ ] 🔴 Observability pass: trace IDs, structured logs, audit completeness.
- [ ] 🔴 Security pass: secrets, key handling, allowlists, **max-exposure invariant test**.
- [ ] 🔴 Flip to **mainnet small capital**, conservative caps, one sanity trade.
- [ ] 🔴 Record **demo video**; finalize all docs.
- ✅ **Exit:** sim-vs-live reconciled; "go-live ready" runbook — monitored, reversible.

---

## LIVE WINDOW — Operate (Jun 22–28)

- [ ] 🔴 **Feature freeze.** Tune **risk caps only**, never strategy logic.
- [ ] 🔴 Daily: review PnL + **drawdown** + rule adherence (all judged).
- [ ] 🟡 Confirm Trigger.dev jobs healthy; alerts wired to you.
- [ ] 🟢 Capture standout reflections + token-savings stats for the writeup.

---

## SUBMISSION (Jun 29 – Jul 5)

- [ ] 🔴 Track 1: live PnL, drawdown chart, audit trail, demo, docs.
- [ ] 🔴 Track 2 (free): strategy skill + walk-forward backtest report.
- [ ] 🔴 Special-prize evidence: CMC / TWAK / BNB SDK usage writeups.

---

## Daily Discipline

1. **Out-of-sample only.** In-sample numbers are lies you tell yourself.
2. **Sim and live run the same `/core` code.** If they diverge, the sim is worthless.
3. **Costs in every backtest.** Gas, slippage, fees, funding, latency.
4. **Fewer knobs.** Every parameter you add is overfit you'll pay for live.
5. **Drawdown is the score.** Tune risk to protect it, not just to be safe.
6. **Testnet → paper → mainnet. Simulate before send. Always.**
7. **Every decision auditable.** If it's not in Convex, it didn't happen.
