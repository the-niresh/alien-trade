# Alien-Trade — Build Steps (Track-1-First Runbook)

> Ordered, checkable steps. Companion to `PROJECT_PLAN.md` and `STRATEGY.md`.
> **Goal: win Track 1 on risk-adjusted PnL + drawdown.** The backtest engine and the strategy are the crown jewels — everything else serves them.
> Rule: a thin end-to-end slice (signal → sim → testnet trade) must work by Day 6.

Legend: 🔴 blocker / must-pass · 🟡 important · 🟢 polish · ⏱ timebox · ★ wins-the-track

---

## ▶ RESUME HERE (Jun 9 — after break)

Steps 0–7 done. STEP 8 well underway: the **agent team is wired and skill-grounded**, the **goal scorecard** and **competition constraints** are in place. Full suite **281 passed, 1 skipped**. Nothing below needs funding except 8.6.

**Done this session (Jun 9):**
- **Goal scorecard** (`core/scorecard.py` + Convex `scorecard` table, doc `docs/GOAL.md`): objective `Sortino − 2·|maxDD|` + full scorecard (drawdown depth+duration, consistency, trade quality, cost ratio, exposure, autonomy, rule-adherence). Wired into the live loop (`DecisionLoop` pushes `scorecard:update` each cycle, guarded).
- **UI testnet/paper/LIVE toggle** (`web/`, `config.setTradingMode`) + **live mode read-back** in the loop (`_sync_trading_mode`, switches executor only while flat).
- **Eligible-token rebuild** (organizer rule: only `twak swap` counts; BNB/BTC/BTCB NOT eligible): allowlist `{ETH,CAKE,UNI,LINK,AAVE}`, default symbol **ETH**, perps dropped from scored path. **Activity floor** (`enforce_activity_floor`) for ≥1 trade/day. `twak compete register` wrapper. Rules captured in memory `reference-hackathon-rules`.
- **CMC re-tune tool** (`core/retune.py`, `--source cmc|binance`). ⚠️ result is the finding: S1-only on OHLCV is **negative OOS** — the edge is in S2/S3/S4 (CMC funding/OI/social/flow), which need the gated CMC plan + extended-field endpoints.
- **CMC Skill Hub** (`agent/skills/`): two-tier loader (curated 8 + dynamic `find_skill`), raw-httpx stateless MCP transport, live-verified. **Research + co-pilot now consume it** (curated-first, dynamic fallback).
- **LangGraph supervisor** (`agent/graph/supervisor.py`): all 4 advisory nodes (co_pilot, historian, researcher, reflector), single entry, channel emission + pause control. `agentEvents`/`agentControl` Convex fns **deployed**; channel verified live (reflector→historian wrote+confirmed a real lesson).

**Next actions when back — in priority order:**
1. **8.3 finish — observe→react trigger** (small, high value): a Trigger.dev watcher (or a Convex-polling loop) that fires `Supervisor.handle()` on `position_closed` events + schedule ticks, so the team is self-driving instead of manually invoked. → see `agent/graph/supervisor.py`, `jobs/src/`.
2. **8.5 — PWA glass cockpit** (demo value for judges + special prizes): read-only agent-chat rendering of `agent_events` (grouped by cycle, newest-first via `agentEvents:recent`) + the three stop controls writing `agent_control` (`agentControl:set`: Stop response / Pause Agents / Kill Switch, confirm-gated).
3. **8.4 — Option-B forecast bridge** (gives the Researcher teeth): shrink-only, decay-to-neutral multiplier in `core/risk/` (can't enlarge size; sim/live parity test). Researcher writes a confidence float → `forecast_state`; Risk Officer reads it as a size shrink. Contract already exists (`ForecastState` in `contracts.py`).
4. **8.2 — social S3 bridge** (★ activates the sentiment signal): `convex/social.ts` (watchlist CRUD + agent-write posts/sentiment) → `sentiment_state` → live loop reads it into the bar's `social_score` (point-in-time, parity test) → Trigger.dev ingest schedule.
5. **★ Strategy re-tune on CMC data** (blocks confidence in live params): needs the CMC historical plan + wiring funding/OI/social/flow into `cmc_client._parse_ohlcv`, then `core/retune.py --source cmc`. Until then params are unvalidated on the real signal set.
6. **Compliance before Jun 22**: operator runs `twak compete register` + DoraHacks submission (see COMPETITION COMPLIANCE section). Step-7 carryover: mainnet sanity trade (wallet funding) + demo video.

> Convex deploy reminder: keep `bunx convex dev` running so new functions (`scorecard`, `agentEvents`, `agentControl`) stay live. Run tests with `core/.venv/Scripts/python.exe -m pytest agent/tests core/tests -q`.

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

- [x] 🔴 ★ **OHLCV HISTORICAL** — `core/data/binance_client.py`: 2-year daily for BNB/BTC/ETH on disk in `core/data/parquet/`. Schema matches Bar exactly. Binance klines = primary historical source (free, reliable, no auth). CMC used for live signals only.
- [x] 🔴 **CMC LIVE feed** — `core/data/cmc_client.py`: live quotes working (BNB ~$572). Same fields as Bar (extended fields stubbed 0.0 until CMC Agent Hub endpoint confirmed). x402 header infra ready.
- [x] 🔴 **L3 BNB SDK** — `core/exec/bnb.py`: simulate-before-send pipeline, PancakeSwap V3 calldata encoding, BSC testnet RPC reachable (chain 97, gas 0.1 gwei). Signed broadcast wired — needs funded testnet wallet via TWAK to complete a live trade.
- [x] 🔴 **L2 TWAK** — `core/exec/twak.py`: HMAC-SHA256 signing utility built and tested. `TW_ACCESS_ID` + `TW_HMAC_SECRET` confirmed in env. Live API call pending TWAK endpoint confirmation.
- [x] 🟡 **x402 pay-per-call** implemented: `core/data/cmc_client.py` uses full x402 protocol (HTTP 402 → EthAccountSigner → retry) via `x402[evm,httpx]` v2.12. Set `X402_PRIVATE_KEY` (dedicated micropayment wallet, USDC on Base eip155:8453) to activate. Falls back to plain `CMC_API_KEY` auth when key is absent. `X402_NETWORK` overrides default network.
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

- [x] 🔴 Event-driven backtester over the historical dataset. **Strict point-in-time access — zero look-ahead bias.**
- [x] 🔴 **Cost model:** BSC gas, size-aware AMM slippage, swap fees, perp funding, fill latency. (A sim without costs lies.)
- [x] 🔴 ★ **Walk-forward harness:** optimize on window N → validate on untouched window N+1 → roll. **Never report in-sample.**
- [x] 🔴 **Metrics:** total return, Sharpe, **Sortino**, **max drawdown**, **Calmar**, win rate, turnover, **rule-adherence score** (mirror judging rubric).
- [x] 🟡 Regime-sliced reporting: trend / chop / high-vol / crash evaluated separately.
- [x] 🟡 Deterministic + seeded; one command reproduces a full report from clean clone. → `cd core && .venv/Scripts/python.exe -m report` (walk-forward OOS + regime breakdown, costs on).
- ✅ **Exit:** run any strategy through walk-forward and print **honest out-of-sample, cost-inclusive** metrics.

---

## STEP 3 — Strategy & Signals (the alpha) (Jun 11–15)  *(overlaps Step 2)*

- [x] 🔴 ★ Implement signal library (see `STRATEGY.md`), each independently testable:
  - [x] momentum / trend (price TA)
  - [x] sentiment / social (CMC)
  - [x] derivatives: funding rate + open interest (CMC)
  - [x] on-chain flow (CMC)
- [x] 🔴 **Regime detector** (trend vs chop vs high-vol) — deterministic first.
- [x] 🔴 ★ Combine **2–3 orthogonal signals** into one strategy. Resist extra knobs.
- [x] 🔴 Walk-forward optimize; select for **parameter stability**, not the peak.
- [x] 🟡 Per-signal attribution: which signal contributes which edge (kill dead weight).
- ✅ **Exit:** strategy with **positive, stable, out-of-sample** risk-adjusted returns net of costs across regimes.

---

## STEP 4 — Drawdown-First Risk Engine (Jun 13–16)  ★

- [x] 🔴 **Position sizing:** volatility targeting / capped fractional-Kelly (size down as vol rises).
- [x] 🔴 **Hard guardrails (code):** per-trade cap, **daily-loss → halt**, max open exposure, slippage cap, token allowlist.
- [x] 🔴 **Regime gating:** size down / sit out in bad or uncertain regimes.
- [x] 🟡 **Mistake-avoidance:** "lost on this exact setup before?" lookup → block/penalize. *(Step 6 — `agent/secondbrain/avoidance.py`, Upstash Vector; pure lookup, no LLM on the hot path)*
- [x] 🔴 ★ Re-run walk-forward with **objective = risk-adjusted return − hard drawdown penalty** (not raw return).
- ✅ **Exit:** risk engine cuts max drawdown in sim at minimal return cost; daily-loss kill verified.

---

## STEP 5 — Live Runtime + Execution Reliability (Jun 15–18)

- [x] 🔴 Live decision loop importing the **same `/core` strategy** (no duplicate logic) on the live feed. `agent/loop.py` calls the RiskEngine-wrapped core; **sim/live parity proven** (paper loop == backtest fill-for-fill + equity, `agent/tests/test_live_runtime.py`).
- [x] 🔴 **Executor:** simulate-before-send → sign (TWAK) → send (BNB) → on-chain confirm → ledger reconcile. **Idempotency keys** (cycle_id) block double-execution. `agent/executor.py` (`PaperExecutor` + `OnchainExecutor`).
- [x] 🔴 **Trigger.dev:** `jobs/src/decisionLoop.ts` (hourly scan), `tradeMonitor.ts` (1-min watchdog), `reflection.ts` (post-trade, Step-6 seam). Retries+backoff+dead-letter via `trigger.config.ts`; idempotent.
- [x] 🔴 **Kill switch:** UI → Convex `config.halted` → agent halts within one cycle (`config.ts:setHalted`/`isHalted`, checked first every cycle). Circuit breaker surfaced in `risk_state`.
- [x] 🟡 **Web dashboard (PWA):** `web/` React + Vite + `vite-plugin-pwa` (manifest + service worker). Reads Convex reactive state; kill-switch toggle; decisions feed.
- [x] 🟡 **QR code in terminal:** `agent/qr.py` renders an ASCII QR for `PWA_URL` on startup (graceful fallback if `qrcode` absent).
- [x] 🟡 **Mobile controls via Convex:** kill switch + caps + PnL/drawdown all flow through Convex real-time (`config`, `riskState`, `ledger`, `decisions`) — no separate webhook server.
- [x] 🟡 Every cycle writes a `decision` row (signals, regime, target, verdict, sizing, trade link) — idempotent on cycle_id.
- [x] 🟡 **Chaos test:** kill switch, failed tx, broadcast error, RPC timeout, reverted tx, slippage-cap reject, risk veto, replayed cycle → no double-execution. 17/17 green.
- ✅ **Exit:** paper loop reconciles to the sim fill-for-fill; failure modes return clean reports (no crash, no double-trade). Live testnet trade still pending a funded wallet (Step 1 carry-over); `--dry-run` simulate-before-send path verified via mocks.

### Step 5 verification (Jun 7)
- Convex bus deployed + seeded; `config:isHalted` live. Paper smoke (`agent/smoke.py`, 250 BNB bars) wrote real `decisions`/`trades`/`ledger`/`risk_state` rows to `festive-newt-1` — verified via Convex query.
- `core/.venv/Scripts/python.exe -m pytest agent/tests -v` → 26 passed (parity + chaos + twak executor + crash-recovery).

### Step 5 hardening (Jun 7) — wallet + AgentForge learnings
- **Self-custody execution wired:** `agent/twak_cli.py` + `TwakSwapExecutor` use the `twak` CLI (route + sign on-device + broadcast); BNB SDK confirms the receipt. `EXECUTION_BACKEND=twak` (default) keeps **zero raw keys** in code. `python -m agent.wallet` verifies the connection. Wallet creation/funding is operator-run (faucet for testnet, small capital for mainnet) — twak swap is mainnet, paper covers pre-mainnet.
- **Crash-state recovery (AgentForge Lesson 11):** `agent/recovery.py` + `--recover` rebuild ledger + RiskEngine + executor idempotency set from the Convex event log on restart → a restart mid-position cannot double-trade or mis-account. `RiskEngine.restore()` replays trades through the internal tracker.
- AgentForge cross-check: we already satisfy its safety-in-code, policy-loop, structured-result, and test-the-boundaries lessons. Deferred to Phase 6 (LLM layer): untrusted-content wrapping for CMC/social/web data, subagent guardrails (scoped tools/max_turns/timeout), context compaction.

---

## STEP 6 — Second Brain + LLM Layer (Jun 16–19)  *(small, off hot path)*

> All in `agent/secondbrain/`. Offline-first (in-memory vector + stub LLM) so the loop, tests, and a laptop demo run with zero network; live against Upstash Vector + Redis + Anthropic. The LLM is **off the trade hot path** — the only Second-Brain call on the cycle path is the mistake-avoidance vector lookup, which never invokes the LLM.

- [x] 🔴 **Hermes self-learning loop:**
  - After every trade: `reflection.py::ReflectionWriter` emits `{signals, regime, outcome, lesson}` → lesson compressed by Haiku (T0, deterministic fallback offline) → embedded under the *setup key* in Upstash Vector + Convex `reflections` row. Fired by the loop on a closing (sell) fill.
  - Before every trade: `avoidance.py::VectorMistakeAvoidance` (implements `brain.MistakeAvoidance`) queries Vector — "lost on this setup before?" → block (≥75% loss-rate) or halve size (≥50%). Deterministic, fail-open, no LLM.
  - Zero changes to `/core` strategy code. Sim/live parity preserved (avoidance/reflection are a live-only overlay; default-off when no keys).
- [x] 🔴 **2-year historical pre-load (one-time, before go-live):**
  - `preload.py` walks the 2-year dataset; labels each point-in-time slice `{regime, dominant_signal, outcome}` (outcome = forward return) → institutional memory in Upstash Vector. `python -m agent.secondbrain.preload`.
- [x] 🔴 **Karpathy AutoResearch loop (async):**
  - `research.py::ResearchSupervisor` spawns a self-directing `ResearchAgent` sub-agent (supervisor pattern, LangGraph-ready): identifies unknowns (regime anomalies, social spikes, OI/flow divergence) → queries CMC live + recent bars → synthesizes a digest (Sonnet T1) → stores in Second Brain. `python -m agent.secondbrain.research`.
- [x] 🟡 **Token optimization:** model router T0/T1/T2 (`llm.py`), Redis response cache (`cache.py`), `max_tokens` caps, optional structured outputs (`output_config.format`).
- [x] 🟡 **Cost telemetry:** `telemetry.py` per-call `{tier, in/out tokens, cost, cache_hit, latency}` + running **$ saved vs naive all-Opus baseline**. Surfaced at `GET /telemetry`.
- [x] 🔴 **Co-pilot chat** grounded in Second Brain (`copilot.py`): retrieves across reflections + institutional + research, folds in live Convex state, answers with sources. `python -m agent.secondbrain.copilot "<q>"` / `POST /copilot`.
- ✅ **Exit:** co-pilot answers cheaply from memory; a stored reflection demonstrably changes a later decision (block/penalize, tested); 2-year institutional memory is queryable; AutoResearch loop runs one full cycle end-to-end.

### Step 6 verification (Jun 7)
- `core/.venv/Scripts/python.exe -m pytest agent/tests core/tests` → **167 passed, 1 skipped** (25 new Second-Brain tests; parity + chaos + recovery unbroken).
- **Live smoke** (real services): Upstash Vector upsert→embed→query (score 1.0); Anthropic Haiku call OK; Redis cache hit on repeat; telemetry shows $ saved vs Opus.
- **Live loops:** AutoResearch wrote a real BNB chop-regime digest (CMC live $595, Sonnet T1); 2-year pre-load wrote institutional memories to Vector; co-pilot answered grounded over institutional + research memory, citing sources (and correctly refused to hallucinate a setup not in memory).
- Convex `reflections` (record/recent/byOutcome) deployed to `festive-newt-1`.
- Wiring: `runtime.build_loop` injects `mistake_avoidance` + `reflection_writer` when enabled; `GET /telemetry`, `POST /copilot`, `POST /research` exposed. Toggle with `SECOND_BRAIN=0`.

---

## STEP 7 — Paper Rehearsal + Mainnet Readiness (Jun 18–21)

- [x] 🔴 ★ **Multi-day live PAPER run** on the real feed (no capital). `agent/rehearsal.py` reconciles sim vs live PAPER over the same window — **fill-for-fill, $0 equity drift** on both cached (500 bars) and the live Binance feed (200 bars). `run_forever` now survives unanticipated exceptions (logs + audits + continues) so a shadow-run doesn't die on the surprises it exists to surface. Leave it running on testnet to harvest + tune.
- [x] 🔴 Observability pass: **trace IDs** (`cycle_id`) + **structured JSON logs** (`agent/observability.py::jlog`, cp1252-safe) + **audit completeness** (rehearsal asserts one decision row per cycle).
- [x] 🔴 Security pass — **max-exposure invariant**: `guardrails.check_max_exposure` + enforced in `RiskEngine` on every buy → a stack of individually-legal buys can never pile past `max_open_exposure_pct` of equity (adversarial + property tests). Token allowlist already enforced; key handling = self-custody via `twak` (Step 5), zero raw keys.
- [ ] 🔴 Flip to **mainnet small capital**, conservative caps, one sanity trade. *(BLOCKED on wallet funding — user adding capital next; `--dry-run` path proven via mocks in Step 5.)*
- [ ] 🔴 Record **demo video**; finalize all docs.
- ✅ **Exit:** sim-vs-live reconciled ✓; "go-live ready" runbook — monitored, reversible. *(monitored ✓ / reversible ✓ via kill switch; mainnet sanity trade pending capital.)*

### Step 7 verification (Jun 8)
- `agent/rehearsal.py` reconciliation: cache 500 bars → 8 sim fills == 8 live fills, drift $0.00, 1 decision/cycle; live feed 200 bars → 1==1, drift $0.00. Both PASS.
- `pytest agent/tests core/tests` → **174 passed, 1 skipped** (+ max-exposure invariant, rehearsal reconcile, observability tests; parity unbroken).
- Wallet-independent Step-7 work complete; remaining items (mainnet sanity trade, x402 live settlement, demo) are gated on the wallet/endpoint and tracked for when funded.

---

## STEP 8 — Agent Team + Social Layer + Glass Cockpit (Jun 8+)

> The multi-agent productization. Refs: `AGENT_TEAM_PLAN.md`, `SOCIAL_LAYER.md`,
> `SPONSOR_TOOLS_INTEGRATION.md`, `FRONTEND_PLAN.md`, memory `reference-cmc-x402`.
> Build order is contracts-first; nothing here needs funding except 8.6.

### 8.1 Foundation (do first — no funds) ✅
- [x] 🔴 `agent/graph/contracts.py` — every inter-agent payload + the failure matrix (AGENT_TEAM_PLAN §9.2/§9.3) defined before wiring. Re-exports existing payloads (`AvoidanceVerdict`/`ResearchDigest`/`Reflection`/`SentimentReading`) as one canonical import site; defines `AgentEvent`/`ForecastState`/`AgentControl` (each `as_row()` matches its Convex columns); roster split into `TIER0_AGENTS`/`TIER1_AGENTS`; `FAILURE_MATRIX` enforces the governing rule in code (`FailurePolicy.__post_init__` rejects any Tier-1 policy claiming `halts_trade`). 13/13 tests in `agent/tests/test_agent_contracts.py`.
- [x] 🔴 Convex tables: `agent_events` (append-only chat/audit stream; by_cycle/by_ts/by_agent), `forecast_state` (Option-B bridge; by_symbol), `agent_control` (kill/pause/stop singleton, user-writable; by_key). Deployed to `festive-newt-1` — schema + indexes verified live.

### 8.2 Social layer — finish the wiring (ingestion already built + live)
- [x] 🔴 `agent/social/` ingestion: RSS + Farcaster **live**, Telegram + twscrape built+gated; deterministic sentiment scorer; 9/9 tests; one live pull verified.
- [x] 🟡 Convex schema `social_sources` / `social_posts` / `sentiment_state` added.
- [ ] 🔴 `convex/social.ts` — watchlist CRUD (user) + write posts/sentiment (agent).
- [ ] 🟡 Trigger.dev schedule for `agent.social.ingest` (every N min, off hot path).
- [ ] 🔴 ★ Bridge `sentiment_state` → core signal **S3** (point-in-time; parity test).
- [ ] 🟢 Optional async LLM enrichment (pump/manipulation + claim detection).

### 8.3 Orchestrator graph
- [x] 🔴 `agent/graph/supervisor.py` (LangGraph `StateGraph`) — **all 4 advisory nodes** (co_pilot, historian, researcher, reflector) with single entry `Supervisor.handle()`. Routing (§4): user→co_pilot (history-intent→historian); schedule tick→researcher; trade-close→reflector→historian.write (graph edge); other events→historian. Per-node AgentEvent emission + Pause-Agents short-circuit. langgraph in core venv. Live-verified: co_pilot grounded in live `funding_regime` skill; reflector→historian chain wrote+confirmed a real lesson, both events on the channel. Tests `agent/tests/test_supervisor.py` (16).
- [x] 🔴 Channel + control Convex fns: `convex/agentEvents.ts` (append/recent), `convex/agentControl.ts` (get/set); bridge `emit_event`/`recent_events`/`get_agent_control`. **Deployed** (`convex dev`) + channel verified live (events land + read back).
- [ ] 🟡 **Observe→react trigger**: a watcher (Trigger.dev) that polls Convex for `position_closed`/schedule ticks and calls `Supervisor.handle()` — currently `handle()` is invoked manually. Plus PWA channel view (8.5).

### 8.4 Option-B forecast bridge
- [ ] 🔴 `core/risk/` bounded multiplier (**shrink-only**, decays to neutral) + tests (can't enlarge; decay; sim/live parity). Researcher emits a deterministic confidence float → `forecast_state`.

### 8.5 Glass cockpit (PWA)
- [ ] 🟡 `emit_event` helper — every agent writes its trace.
- [ ] 🟡 Read-only agent chat rendering of `agent_events` (grouped by cycle).
- [ ] 🔴 Three stop controls writing `agent_control`: Stop response / Pause Agents / **Kill Switch** (confirm-gated; reuses existing `/halt`).

### 8.6 x402 go-live (only when funding) — see `reference-cmc-x402`
- [ ] 🔴 Route live quote to `/x402/v3/cryptocurrency/quotes/latest` when x402 on; keep historical on `/v2` + API key (no x402 historical endpoint exists).
- [ ] 🔴 Pay via **`twak x402` on the single Trust Wallet** (no burner, no raw key) OR the `X402_PRIVATE_KEY` burner. Fund **15 USDC on Base** (gasless, no ETH).
- [ ] 🔴 Verify one live `402 → sign → 200 → $0.01 settle`. x402 proven.

### 8.7 Sponsor depth (special-prize upside) — see `SPONSOR_TOOLS_INTEGRATION.md`
- [x] 🟡 **CMC Skill Hub loader built** — `agent/skills/` two-tier loader (curated registry of 8 signal-mapped skills + dynamic `find_skill`), raw-httpx MCP Streamable-HTTP transport (stateless, SSE), offline-first. Live-verified against `mcp.coinmarketcap.com/skill-hub`. Tests: `agent/tests/test_skill_hub.py` (16).
- [x] 🟡 **Research agent wired to the hub** — `ResearchAgent` pulls curated reads (market_regime/funding_regime/kol_sentiment) into `gather_context` each AutoResearch cycle → digests grounded in orthogonal CMC signals; guarded per-skill, offline-first. Live-verified. Tests: `agent/tests/test_research_skills.py` (7).
- [x] 🟡 **Co-pilot wired to the hub** — `_skill_evidence` is curated-first (keyword `route_curated` → pinned skills) with dynamic `find_skill` fallback for the long tail; evidence folds into the answer as a `LIVE CMC SKILLS:` block. Live-verified both tiers. Tests: `agent/tests/test_copilot_skills.py` (12). **Next:** LangGraph supervisor (8.3). Off the hot path (locked #1).
- [ ] 🟡 **Publish the Track-2 strategy as a CMC Skill** (Skills Marketplace + Track 2 + CMC prize in one).
- [ ] 🟢 **TWAK native x402 provider** — expose the regime/signal digest as a paid endpoint ("both sides of x402").

### 8.8 Dreamer (nightly consolidation)
- [ ] 🟢 Trigger.dev nightly job: review the day, score prior forecasts vs outcomes, dedupe/compress memory, write a nightly digest (AGENT_TEAM_PLAN §9.4).

- ✅ **Exit:** agent team visible in the cockpit; social sentiment feeding S3; forecast bridge shrinking size on cue; x402 live; sponsor depth documented.

---

## COMPETITION COMPLIANCE — register + qualify (before Jun 22)

> Source: memory `reference-hackathon-rules` (organizer rulings + DoraHacks page).
> These are hard gates — miss one and the live PnL doesn't count.

- [ ] 🔴 **On-chain registration before the window opens (Jun 22).** Operator runs `twak compete register` (wrapper: `TwakCli.compete_register()`; check with `compete_status()`) — or MCP `competition_register` → competition contract `0x212c61b9b72c95d95bf29cf032f5e5635629aed5` on BSC. Late entries are rejected. *(wrapper built; the actual run is operator/wallet-gated.)*
- [ ] 🔴 **DoraHacks submission** — submit the agent's BSC wallet address + a short strategy writeup (how the results were achieved).
- [x] 🔴 **Only `twak swap` trades count toward PnL** (organizer-locked, Gwen 6/8). Scored trades route through `TwakSwapExecutor`; the `raw` BNB-SDK path is dev/testnet only. Perps (Aster/PancakeSwap) are not `twak swap` → don't count → spot-long-only (CLAUDE.md L3 updated).
- [x] 🔴 **Eligible tokens only.** Allowlist = curated subset `{ETH,CAKE,UNI,LINK,AAVE}` of CMC's 149-token list; default symbol = **ETH**. **BNB/BTC/BTCB are NOT eligible** (removed). ⚠️ **Re-tune still owed on CMC data** — `core/retune.py` run on Binance OHLCV (S1-only, no funding/OI/social/flow) is **negative OOS** (WF return −4%, Sortino −0.15); the edge lives in the orthogonal CMC signals (S2/S3/S4), so re-run `retune.py` against CMC data before trusting any params.
- [x] 🔴 ★ **Activity floor: ≥ 1 trade/day.** Built: `DecisionLoop.enforce_activity_floor` forces one minimal compliance swap late in the day if nothing has traded (trims if holding, else tiny buy). Enable for live via `--activity-floor` / `ACTIVITY_FLOOR=1` (off in paper/rehearsal so sim parity holds). Still: hold non-zero in-scope assets at window start; never let the portfolio fall to ≤ $1 (that hour scores 0%).

---

## LIVE WINDOW — Operate (Jun 22–28)

- [ ] 🔴 **Feature freeze.** Tune **risk caps only**, never strategy logic.
- [ ] 🔴 Daily: review PnL + **drawdown** + rule adherence (all judged).
- [ ] 🔴 Daily: confirm **≥ 1 `twak swap` trade executed** (qualification floor) and portfolio > $1.
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
