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
1. ~~**8.3 finish — observe→react trigger**~~ ✅ Done (Jun 9): `POST /supervisor`, `supervisorTick.ts` (2h cron → Researcher), `decisionLoop.ts` fires `position_closed` on sell fills. Agent team is self-driving. 288 passed.
2. ~~**8.5 — PWA glass cockpit + Equity Floor Guard**~~ ✅ Done (Jun 9): agent channel, 3 stop controls, equity floor guard + warning banners. 10 tests passing. ⚠️ Run `bunx convex dev` to push schema.
3. ~~**8.4 — Option-B forecast bridge**~~ ✅ Done (Jun 9): `core/risk/forecast.py` (decay_confidence + apply_forecast_multiplier + confidence_from_regime), `convex/forecastState.ts` (get/set), `DecisionLoop._apply_forecast` (shrink-only, Tier-1 safe), Researcher node writes confidence after each AutoResearch cycle. 31 tests passing. ⚠️ Run `bunx convex dev` to push forecastState.ts.
4. ~~**8.2 — social S3 bridge**~~ ✅ Done (Jun 10): `convex/social.ts` (getSentiment/setSentiment/writePosts/getSources/addSource/toggleSource), bridge get/set/record_social_posts, `DecisionLoop._inject_sentiment` stamps live score onto history[-1] before score_breakdown (offline→noop, parity), `POST /social/ingest` server endpoint, `jobs/src/socialIngest.ts` (30-min cron). 8 tests passing. ⚠️ Run `bunx convex dev` to push social.ts.
5. ~~**★ Strategy re-tune on CMC data**~~ ✅ Done (Jun 10): Wired real S2 signals (funding_rate + open_interest) from **Binance Futures public API** (fapi, free/no key) into `BinanceClient.enrich_s2()`. `fetch_ohlcv_historical(enrich_s2=True)` forward-fills funding rate from 8h settlements and aligns hourly OI snapshots. `retune.py --source binance` now tunes S1+S2 with real derivatives data. `BINANCE_FUTURES_BASE_URL` + `BINANCE_FUTURES_PAIRS` in constants. social_score/net_flow remain 0.0 until CMC Pro available. 9 new offline tests passing. ⚠️ Force-refresh cached parquet files with `--force-refresh` flag to get S2 data in existing bars.
6. **Compliance before Jun 22**: operator runs `twak compete register` + DoraHacks submission (see COMPETITION COMPLIANCE section). Step-7 carryover: mainnet sanity trade (wallet funding) + demo video.
7. ~~**8.9 — Telegram alert channel**~~ ✅ Done (Jun 10): full two-way `TelegramBot`; slash commands + inline approve/reject buttons; equity floor, kill-switch, daily summary wired. 19 tests passing.
8. ~~**8.10 — Supervisor budgets + dedupe**~~ ✅ Done (Jun 10): `MAX_HOPS=4` budget per call, `_last_research_ts` 90-min in-memory dedupe per symbol, `_reflected_cycle_ids` idempotency on `cycle_id`. 10 new tests passing.
9. ~~**8.11 — Degraded-mode observability**~~ ✅ Done (Jun 10): `DecisionLoop._check_staleness` (forecast >4h, sentiment >2h) emits `RiskGuard` `KIND_OBSERVATION` events on stale→fresh transitions; Signal Health row in cockpit (amber/green dots for Forecast+Sentiment). 10 new tests passing.

10. ~~**8.8 — Dreamer curator**~~ ✅ Done (Jun 10): `agent/secondbrain/dreamer.py` (dedupe reflections cosine≥0.92, forecast calibration bucket win-rates, age stale research >48h, nightly digest). `convex/forecastCalibration.ts` (record/recent/getSummary). `stale` field on `reflections` + `forecast_calibration` table in schema. `DecisionLoop._entry_forecast_confidence` + `_record_forecast_calibration` on sell fills. `POST /dreamer` endpoint. `jobs/src/dreamer.ts` (02:00 UTC cron). 12 tests passing. ⚠️ Run `bunx convex dev` to push schema + new Convex functions.
11. **Step 9 — Packaging** (after live window closes, before submission): `install.sh` onboarding wizard + Vercel PWA deploy + hosted agent endpoint. Lets judges reproduce the demo from a single curl command.
12. ~~**8.13 — Tier-1 self-eval rubrics**~~ ✅ Done (Jun 10): `ResearchAgent.synthesise` → LLM T0 rubric check, retry once, `ResearchDigest.low_confidence=True` if both fail + supervisor emits `KIND_OBSERVATION` event. `CoPilot.ask` → citation scan, prepends warning when uncited. `ReflectionWriter._eval_quality` → `_is_generic` check, rubric-injected retry, `Reflection.quality="low"` stored to Convex. `schema.py` + `convex/schema.ts` updated. 23 tests passing.
13. ~~**8.14 — Tier-1 failure visibility**~~ ✅ Done (already live): `_emit_failure` helper in supervisor.py emits `KIND_CONTROL` AgentEvent for every node exception; server.py endpoint also emits on failure.
14. ~~**8.15 — Researcher fan-out**~~ ✅ Done (Jun 10): `ResearchSupervisor.run_cycle(symbols=[...])` fans out via `ThreadPoolExecutor(max_workers=3)`; `_run_one(symbol)` writes per-symbol `forecast_state`. `supervisor._researcher_node` reads `bridge.get_token_allowlist()` + `_filter_dedupe` (per-symbol 90-min dedupe). `ConvexBridge.get_token_allowlist()` added. 14 tests passing. `test_second_brain.py` updated (removed `sup.agent` reference).
15. ~~**8.16 — Glass cockpit full build-out**~~ ✅ Done (Jun 10):
16. ~~**8.7 — Track-2 CMC Skill**~~ ✅ Done (Jun 10): `agent/skills/track2.py` + `agent/skills/skill_manifest.json` + `POST /skill/signal_score` + `GET /skill/manifest`. 26 tests. CMC Skills Marketplace manifest ready for submission (`unique_name: alien_trade_multi_signal_score`). framer-motion + recharts installed. Backend: `convex/copilot.ts` (ask action + addMessage mutation + messages query), `copilot_messages` table in schema, `reflections.mode` field + `wins` query, `agentEvents.latestPerAgent` roster query. Frontend full rewrite: animated AgentRoster (Framer Motion orbit + glow states per activity), CoPilot chat (Convex action + persisted thread), EquityChart (recharts ComposedChart area+line dual-axis), 3-panel cockpit grid (responsive → stacks on mobile), RiskSliders (live caps with commit-on-release), wins feed, signal health dots, all 8.5 controls preserved. TypeScript clean, Vite build green. ⚠️ Run `bunx convex dev` to push new schema + functions. premium UI on top of the functional 8.5 cockpit — animated agent roster + co-pilot chat (centerpiece), wins feed + equity/drawdown chart, risk-cap sliders + live log console, polish pass. Backend glue first (`copilot.ts` action + `copilot_messages`, latest-per-agent roster query, `mode` on reflections). See §8.16.

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

### 8.2 Social layer ✅
- [x] 🔴 `agent/social/` ingestion: RSS + Farcaster **live**, Telegram + twscrape built+gated; deterministic sentiment scorer; 9/9 tests; one live pull verified.
- [x] 🟡 Convex schema `social_sources` / `social_posts` / `sentiment_state` added.
- [x] 🔴 `convex/social.ts` — `getSentiment`/`setSentiment` (per-symbol upsert), `writePosts` (batch, deduped), `getSources`/`addSource`/`toggleSource` (watchlist CRUD). ⚠️ `bunx convex dev` to deploy.
- [x] 🟡 `jobs/src/socialIngest.ts` — 30-min cron → `POST /social/ingest`; failure swallowed (advisory).
- [x] 🔴 ★ `DecisionLoop._inject_sentiment` — reads `sentiment_state` from bridge, stamps score onto `history[-1]` via `dataclasses.replace` (point-in-time, immutable); offline/sim → noop (parity). `POST /social/ingest` writes back to Convex.
- [ ] 🟢 Optional async LLM enrichment (pump/manipulation + claim detection).

### 8.3 Orchestrator graph ✅
- [x] 🔴 `agent/graph/supervisor.py` (LangGraph `StateGraph`) — **all 4 advisory nodes** (co_pilot, historian, researcher, reflector) with single entry `Supervisor.handle()`. Routing (§4): user→co_pilot (history-intent→historian); schedule tick→researcher; trade-close→reflector→historian.write (graph edge); other events→historian. Per-node AgentEvent emission + Pause-Agents short-circuit. langgraph in core venv. Live-verified: co_pilot grounded in live `funding_regime` skill; reflector→historian chain wrote+confirmed a real lesson, both events on the channel. Tests `agent/tests/test_supervisor.py` (16).
- [x] 🔴 Channel + control Convex fns: `convex/agentEvents.ts` (append/recent), `convex/agentControl.ts` (get/set); bridge `emit_event`/`recent_events`/`get_agent_control`. **Deployed** (`convex dev`) + channel verified live (events land + read back).
- [x] 🟡 **Observe→react trigger**: `POST /supervisor` on `agent/server.py` (supervisor singleton, swallows all exceptions — advisory path never breaks the trading server). `jobs/src/supervisorTick.ts` fires every 2 h with `kind=research_tick` → Researcher. `jobs/src/decisionLoop.ts` fires `kind=position_closed` after every sell fill → Reflector→Historian chain. `_cycle_to_dict` now exposes `side` + `realized_pnl` fields. 9 tests in `agent/tests/test_supervisor_endpoint.py`. Agent team is now **self-driving**. Suite: **288 passed, 1 skipped**.

### 8.4 Option-B forecast bridge ✅
- [x] 🔴 `core/risk/forecast.py` — `decay_confidence` (linear decay to NEUTRAL), `apply_forecast_multiplier` (shrink-only, clamped to [FORECAST_FLOOR=0.5, 1.0]), `confidence_from_regime` (trend_up=1.0, chop=0.75, high_vol=0.65, trend_down=0.55). 31 tests: can't enlarge, decay, clamp, parity (offline→1.0), error-safe (Tier-1).
- [x] 🔴 `convex/forecastState.ts` — `get` (query by symbol) + `set` (upsert). ⚠️ Run `bunx convex dev` to deploy.
- [x] 🔴 `agent/convex_bridge.py` — `get_forecast_state(symbol)` + `set_forecast_state(forecast)`.
- [x] 🔴 `agent/loop.py::DecisionLoop._apply_forecast` — reads forecast, applies decay at bar.timestamp, shrink-only multiply; any exception swallowed (Tier-1 must never halt a trade).
- [x] 🔴 `agent/graph/supervisor.py::_researcher_node` — calls `_fetch_history()` before `run_cycle(history)`, computes `confidence_from_history`, writes `ForecastState` via `_write_forecast`. Failure swallowed.
- [x] 🟡 `agent/secondbrain/research.py::confidence_from_history` — deterministic: empty history → NEUTRAL (1.0).

### 8.5 Glass cockpit (PWA) + Equity Floor Guard ✅
- [x] 🟡 `emit_event` helper — RiskGuard agent emits `agent_events` warn/halt rows; supervisor nodes already emit per-event. Channel live.
- [x] 🟡 Read-only agent channel rendering of `agent_events` in `web/src/App.tsx` — newest-first list, agent badge + kind tag + headline + cycle slice; max 30 events.
- [x] 🔴 Three stop controls writing `agent_control`: **Kill Switch** (confirm-gated, writes both `config.setHalted` + `agentControl.set`), **Pause Agents** (toggle, confirm-gated), **Stop Response** (one-shot cancel, confirm-gated).
- [x] 🔴 **Equity Floor Guard** — `check_equity_floor()` + `EquityFloorCheck` in `core/risk/guardrails.py`; `get_equity_floor()` in `ConvexBridge`; `_check_equity_floor()` in `DecisionLoop.run_cycle()` (runs before kill-switch check, sets `config.halted` on breach, emits RiskGuard agent_event). `convex/schema.ts` + `convex/config.ts` updated with optional `equity_floor` field; `updateLimits` accepts it. PWA settings panel lets user set/disable the floor live (writes `config.updateLimits`). Warning banners: orange pre-alert at 120% of floor, red halt banner on breach — both driven by recent RiskGuard `agent_events`. Telegram hook point stubbed (8.9). 10 tests in `agent/tests/test_equity_floor.py` (all passing). ⚠️ Run `bunx convex dev` to push schema change to live Convex.

### 8.6 x402 go-live (only when funding) — see `reference-cmc-x402`
- [ ] 🔴 Route live quote to `/x402/v3/cryptocurrency/quotes/latest` when x402 on; keep historical on `/v2` + API key (no x402 historical endpoint exists).
- [ ] 🔴 Pay via **`twak x402` on the single Trust Wallet** (no burner, no raw key) OR the `X402_PRIVATE_KEY` burner. Fund **15 USDC on Base** (gasless, no ETH).
- [ ] 🔴 Verify one live `402 → sign → 200 → $0.01 settle`. x402 proven.

### 8.7 Sponsor depth (special-prize upside) — see `SPONSOR_TOOLS_INTEGRATION.md`
- [x] 🟡 **CMC Skill Hub loader built** — `agent/skills/` two-tier loader (curated registry of 8 signal-mapped skills + dynamic `find_skill`), raw-httpx MCP Streamable-HTTP transport (stateless, SSE), offline-first. Live-verified against `mcp.coinmarketcap.com/skill-hub`. Tests: `agent/tests/test_skill_hub.py` (16).
- [x] 🟡 **Research agent wired to the hub** — `ResearchAgent` pulls curated reads (market_regime/funding_regime/kol_sentiment) into `gather_context` each AutoResearch cycle → digests grounded in orthogonal CMC signals; guarded per-skill, offline-first. Live-verified. Tests: `agent/tests/test_research_skills.py` (7).
- [x] 🟡 **Co-pilot wired to the hub** — `_skill_evidence` is curated-first (keyword `route_curated` → pinned skills) with dynamic `find_skill` fallback for the long tail; evidence folds into the answer as a `LIVE CMC SKILLS:` block. Live-verified both tiers. Tests: `agent/tests/test_copilot_skills.py` (12). **Next:** LangGraph supervisor (8.3). Off the hot path (locked #1).
- [x] 🟡 **Publish Track-2 strategy as a CMC Skill** ✅ Done (Jun 10): `agent/skills/track2.py` (`SignalScoreSkill.compute()` — fetches Binance bars → runs /core `score_breakdown()` → returns structured JSON); `agent/skills/skill_manifest.json` (CMC Skills Marketplace manifest: unique_name `alien_trade_multi_signal_score`, full input/output schemas, strategy details, examples); `POST /skill/signal_score` + `GET /skill/manifest` on agent server. 26 tests passing. Judges can call the skill endpoint to get a live multi-signal score for any eligible token.
- [x] 🟢 **TWAK native x402 provider** ✅ Done (Jun 10): `agent/x402_provider.py` — `register(app, wallet_address?)` attaches `PaymentMiddlewareASGI` to `POST /skill/signal_score` ($0.01 USDC on Base eip155:8453, exact scheme, x402.org facilitator). Offline-first: no-op when `X402_WALLET_ADDRESS` absent. Wired in `agent/server.py` at startup. 19 tests. Set `X402_WALLET_ADDRESS` to activate.

### 8.8 Dreamer (nightly consolidation) — elevated scope (Hermes lesson)
> Elevated from 🟢 polish to 🟡 important: memory rot during the 7-day live window is a real
> risk. Without a curator, the Reflector writes redundant lessons and the Researcher stores
> overlapping digests, making avoidance lookups noisier over time.

- [ ] 🟡 Trigger.dev nightly job (`jobs/src/dreamer.ts`, fires at 02:00 UTC): calls `POST /dreamer` on the agent server.
- [ ] 🟡 `agent/secondbrain/dreamer.py::Dreamer.run()`:
  - **Dedupe reflections**: fetch recent `reflections` from Convex; embed + cluster near-identical lessons (cosine ≥ 0.92); keep the highest-confidence version, soft-delete duplicates.
  - **Score forecast quality**: for each closed trade, match entry-time `forecast_confidence` from `forecast_calibration` table → compute bucket win-rates (high/med/low confidence). Log back to Convex `forecast_calibration` summary row.
  - **Age out stale research**: mark any `ResearchDigest` older than 48h as `stale=True` in Upstash metadata; co-pilot and avoidance lookups skip stale docs.
  - **Nightly digest**: write a `ResearchDigest(question="nightly", answer=summary)` to Second Brain with top lessons, forecast score, and memory count.
- [ ] 🟡 `convex/schema.ts`: add `forecast_calibration` table (`cycle_id`, `symbol`, `forecast_confidence`, `regime`, `realized_pnl`, `ts_ms`). New `stale` field on `reflections`.
- [ ] 🟡 `DecisionLoop._finalise`: on every sell fill, append a `forecast_calibration` row (entry confidence snapshot + realized_pnl).
- ✅ **Exit:** after 24h of paper run, Dreamer produces a nightly digest; duplicate reflections are merged; forecast win-rate by confidence bucket is queryable.

### 8.9 Telegram Alert Channel ✅
> User-owned Telegram bot: operator creates a bot via @BotFather, drops `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in `.env.local`. Agent sends notifications — no third-party relay, no webhook server.

- [x] 🟡 `agent/notify.py` — `TelegramNotifier`: `send(text)` posts to `https://api.telegram.org/bot{token}/sendMessage`; graceful no-op + single warning log when token absent. No retry loop — fire-and-forget (alerts are best-effort).
- [x] 🟡 Wire alert events:
  - **Equity floor pre-alert** (`portfolio ≤ floor × 1.20`): wired in `DecisionLoop._check_equity_floor`.
  - **Equity floor halt** (`portfolio ≤ floor`): wired in `DecisionLoop._check_equity_floor`.
  - **Kill switch fired** (any source, rising-edge only, not double-fired with floor halt): wired in `DecisionLoop._finalise`.
  - **Daily PnL summary** (calendar-day rollover): wired in `DecisionLoop.run_cycle`; sends date, PnL, max DD, trades, rule-adherence score.
- [ ] 🟢 Onboarding wizard (Step 9) prompts for `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` as optional fields with setup instructions (create bot → get chat ID).
- ✅ **Exit:** operator receives equity-floor + kill-switch alerts in Telegram during the live window without polling the cockpit.

- ✅ **Exit (Step 8):** agent team visible in the cockpit; equity floor guard + Telegram alerts wired; social sentiment feeding S3; forecast bridge shrinking size on cue; x402 live; sponsor depth documented.

### 8.10 Supervisor Budgets + Dedupe (Hermes lesson — pre-live) ✅
> Autonomous loops degrade by looping, not just by being wrong. A research_tick that
> overlaps with itself burns tokens and fills the channel with noise. A Reflector called
> twice on the same close creates duplicate lessons. Budget + dedupe prevents both.

- [ ] 🟡 **Per-run budget** in `agent/graph/supervisor.py`: add `max_hops: int = 4` and `max_tool_calls: int = 8` to `SupervisorState`. Each node increments a counter; if exceeded, the node emits a `KIND_CONTROL` event ("budget exceeded — skipping") and routes to END. This hard-caps runaway token spend per supervisor call.
- [ ] 🟡 **Research-tick dedupe**: `agent/graph/supervisor.py::_researcher_node` checks Convex `agentControl` for `last_research_ts[symbol]`. If `now - last_research_ts < 90 min`, log and skip (return cached confidence). Write `last_research_ts` on successful completion.
- [ ] 🟡 **Reflection dedupe**: `agent/graph/supervisor.py::_reflector_node` checks `last_reflected_cycle_id` in `agentControl`. If the incoming `cycle_id` matches, skip (idempotent on same close event). Prevents Trigger.dev retries from doubling lessons.
- [ ] 🟢 **No-progress detection**: if `_researcher_node` produces a `ResearchDigest` whose `answer` hash matches the previous digest for the same symbol, emit a low-priority event and back off 4h before the next research tick.
- ✅ **Exit:** `/supervisor` called twice on the same close event writes exactly one reflection; research tick within a 90-min window is a no-op; budget counter prevents > 4 hops per call.

### 8.11 Degraded-Mode Observability (Hermes lesson — pre-live) ✅
> During the live window the operator needs to know: "is my sentiment stale?", "is my
> forecast stale?", "is the vector store offline?" A green cockpit over dead signals is
> worse than no cockpit — it hides the problem.

- [ ] 🟡 `agent/loop.py::DecisionLoop._check_staleness(bar)`: called each cycle, checks:
  - `forecast_age_ms = now - forecast_state.ts_ms` → stale if > 4h and Researcher should have run
  - `sentiment_age_ms = now - sentiment_state.ts_ms` → stale if > 2h
  - `vector_ok`: wraps `VectorMistakeAvoidance.health()` (one no-op query, cached 10min)
  Emits a `RiskGuard` `agent_event` with `kind=KIND_OBSERVATION` on first stale detection per source; clears on recovery. Never raises.
- [ ] 🟡 `web/src/App.tsx`: add a **Signal Health** row to the cockpit — colored dots (green / amber / red) for Forecast, Sentiment, Vector, and Convex bridge. Driven by filtering recent `agent_events` for `agent="RiskGuard"` staleness events.
- [ ] 🟡 **Telegram alert on staleness**: `TelegramBot.register_command("health", ...)` returns current signal health. Wire `_check_staleness` to call `bot.send()` on first stale detection of each source (one alert per source per hour max).
- [ ] 🟢 Every auto-halt emitted by `RiskGuard` should carry a `recovery` field in its `detail`: `"auto"` (will clear itself) vs `"manual"` (operator must act). Wire into cockpit banner text.
- ✅ **Exit:** cockpit shows amber/red dot when forecast or sentiment is stale; operator receives one Telegram alert per stale source; health command returns live status.

### 8.13 Tier-1 Self-Eval Rubrics (AGENT_TEAM_PLAN §9.5 — pre-live)
> The plan says Tier-1 agents must flag failure with a reason rather than silently
> delivering garbage. Currently none of the three LLM agents check their own output
> quality. This is a 2–3 hour wiring job with high demo value: "the agent knows when
> it doesn't know."

- [ ] 🟡 **Researcher self-check** (`agent/secondbrain/research.py::ResearchAgent.synthesise`): after producing a digest, call LLM (Haiku T0, cheap) with a one-sentence rubric prompt: *"Is this digest specific, actionable, and grounded in the data above? Reply YES or NO + one sentence."* If NO → retry once with the same context. If still NO → tag `digest.low_confidence = True` and emit a `KIND_OBSERVATION` AgentEvent `"Researcher: low-confidence digest flagged"`. Offline → skip check (parity).
- [ ] 🟡 **Co-pilot self-check** (`agent/secondbrain/copilot.py::CoPilot.ask`): after building the answer, scan whether every key claim has a `[source: …]` cite in the retrieved docs. If any claim is uncited → prepend `"⚠️ Some claims could not be grounded in retrieved memory. "` to the answer. No LLM call needed — pure text scan. Never blocks the answer.
- [ ] 🟡 **Reflector self-check** (`agent/secondbrain/reflection.py::ReflectionWriter.write`): after the LLM produces a lesson string, verify it starts with a concrete regime/signal qualifier (e.g. "In CHOP with S1 negative…"). If it looks like a generic platitude (< 8 words, no numbers, no regime mention) → regenerate once with an explicit rubric injection. If still fails → store as-is with `quality="low"` tag in the Convex `reflections` row.
- [ ] 🟢 Surface `low_confidence` / `quality="low"` tags in the cockpit agent channel badge (amber instead of green) so the operator can see when the advisory layer is uncertain.
- ✅ **Exit:** a researcher digest that fails the rubric is tagged and visible in the channel; co-pilot answer with uncited claims carries a visible warning; reflector stores a `quality` field on every lesson.

### 8.14 Tier-1 Failure Visibility (AGENT_TEAM_PLAN §9.3 — pre-live, wiring only) ✅
> The failure matrix says "every failure is a visible agent_events row, never a silent
> swallow." Currently every supervisor node wraps its body in `except Exception: pass`
> (correct — advisory must never break trading) but emits nothing to the channel. During
> the live window a silently failing Researcher looks identical to a working one.

- [ ] 🟡 In `agent/graph/supervisor.py`, replace bare `except Exception: pass` in each node with a helper `_emit_failure(state, agent_name, error)` that emits a `KIND_CONTROL` AgentEvent (`agent=agent_name`, `headline=f"{agent_name} failed: {type(error).__name__}"`, `detail={"error": str(error)[:200]}`). Trading is still unaffected; the operator sees the failure in the cockpit and Telegram.
- [ ] 🟡 Same pattern for `agent/server.py` supervisor endpoint exception handler and `agent/convex_bridge.py` `emit_event` failures — any swallowed exception that a user would want to know about during the live window should reach the channel.
- [ ] 🟢 Add `failure_count` counter per agent to `agentControl` (incremented on each failure event); surface in the Signal Health cockpit row (8.11) as a badge count.
- ✅ **Exit:** failing a supervisor node mid-run writes a visible red event to the agent channel; operator does not need to grep logs to know an advisory agent crashed.

### 8.15 Researcher Fan-out Across Symbols (AGENT_TEAM_PLAN §9.1 — pre-live)
> The plan says parallelize the Researcher across symbols/anomalies. Currently
> `ResearchSupervisor.run_cycle` is single-symbol sequential. Fan-out is
> straightforward since each `ResearchAgent` is stateless per symbol.

- [ ] 🟢 `agent/secondbrain/research.py::ResearchSupervisor.run_cycle`: if `symbols` list has > 1 entry, run `ResearchAgent` per symbol concurrently via `concurrent.futures.ThreadPoolExecutor(max_workers=3)`. Collect all digests. Each symbol's digest is independently stored; the nightly Dreamer consolidates across symbols.
- [ ] 🟢 `agent/graph/supervisor.py::_researcher_node`: pass `symbols = bridge.get_token_allowlist()` (the eligible-token list `{ETH,CAKE,UNI,LINK,AAVE}`) into `run_cycle`. Research now covers all eligible tokens, not just the loop's active symbol.
- [ ] 🟢 Research-tick dedupe (8.10) applies per-symbol: `last_research_ts[symbol]` checked for each before spawning.
- ✅ **Exit:** one research tick produces digests for all 5 eligible tokens concurrently; each has its own `forecast_state` row; co-pilot can answer questions about any eligible token, not just the active one.

### 8.16 Glass Cockpit Full Build-out (FRONTEND_PLAN.md — pre-live, post-funding)
> The mission-control UI. Source of truth: `FRONTEND_PLAN.md` (rendering) +
> `AGENT_TEAM_PLAN.md` §7 (data shapes). 8.5 shipped the **functional** cockpit
> (agent channel render, 3 stop controls, equity-floor settings + banners). 8.16 is
> the **premium** build-out: animated agent roster, co-pilot chat, polish system.
> Locked: browser never talks to the agent port — all live data flows through Convex
> cloud (decision #5); the prompt is ask/explain/trigger only, **never** the trade path
> (decision #1). Build is local-only (no public deploy); not funding-gated for the UI
> itself, sequenced after the funding/compliance work. Stack: shadcn/ui + Tailwind +
> Framer Motion + recharts + vite-plugin-pwa (current `web/` is plain-CSS → upgrade).

**Backend glue (small Convex additions — do first; verified against `convex/`):**
- [ ] 🔴 `convex/copilot.ts` — `ask` **action** (proxies `POST /copilot` on the agent or Anthropic → `{answer, sources}`) + `copilot_messages` table (persist the thread, syncs across devices). *(gap — `POST /copilot` exists on the agent; no Convex action/table yet.)*
- [ ] 🟡 `convex/agentEvents.ts` — add a **latest-per-agent** roster query (derived "latest row per agent" over the append-only stream) for §3. *(gap — only `append`/`recent` exist; roster must derive, not double-write.)*
- [ ] 🟡 `reflections` — add a `mode` field + a **wins query** (`outcome_label == "win"`, filter testnet) for the wins feed. *(gap — `byOutcome` exists; no `mode` field.)*
- [ ] 🟢 `config.setCaps` — verify `config.updateLimits` covers all 5 slider caps (max position / daily-loss / slippage / max-exposure / consecutive-losses); extend if any are missing. *(partial — `updateLimits` exists.)*
- [x] 🟢 `ledger.history` (equity/drawdown chart) — **built** (`convex/ledger.ts`). `agent_control` (kill/pause/stop) — **built** (8.1). `agent_events` append/recent — **built** (8.3). Co-pilot, reflections, research digests, telemetry — **built** (Step 6); UI just surfaces them.

**Frontend build sequence (FRONTEND_PLAN §12):**
- [ ] 🟡 **1. Shell** — Tailwind/shadcn install + mission-control dark theme (`#0b0f17`, glass cards, faint grid, accent glows green on a win) + layout. Replace the plain-CSS component.
- [ ] 🔴 **2. Co-pilot + animated agent roster (centerpiece)** — chat box → `copilot.ask` → render `{answer, sources}`, streamed token-by-token. **Animated roster/selector**: agent glyphs orbit the supervisor node; active one docks into the prompt as a pill; motion = state (idle breathe / running ring / done pop+check); `@`-mention routing; per-agent color+sigil (Core = different shape, it's the deterministic engine). Framer Motion; respect `prefers-reduced-motion`. **GUARDRAIL: prompt is ask/explain/trigger only — never routes into the signal/trade path.**
- [ ] 🟡 **3. Testnet-wins feed + equity/drawdown chart** — wins feed from reflections (`win`, testnet) showing setup + realized PnL + Hermes lesson; equity/drawdown chart off `ledger.history` (recharts). Drawdown as the hero line (flat while PnL climbs = the risk-adjusted story).
- [ ] 🟡 **4. Risk-cap sliders + mode toggle + live log console** — caps as live sliders → `config.setCaps`/`updateLimits` (show "applies next cycle"); paper/testnet/mainnet toggle (mainnet double-confirm); read-only **live log console** streaming `jlog` JSON (`agent/observability.py`) — the "watch the terminal from the UI" pane. Trigger buttons: Run research now / Run one cycle / Reconcile / Explain last decision. *(Kill switch + pause + stop already in 8.5.)*
- [ ] 🟢 **5. Polish pass** — PnL count-up, sparklines that draw in, spring physics, skeleton shimmers, persistent heartbeat tick each cycle, win animation (restrained confetti + green glow), optional ambient sound (off by default), PWA push on events that matter (kill / drawdown breach / big win), reduced-motion paths. Self-custody badge + audit-stream + "blocked N risky trades" counters (TWAK/BNB prize hooks).
- ✅ **Exit (8.16):** demo moments live — kill switch from phone halts within one cycle; co-pilot answers "why did you skip that pump?" citing the exact past loss; drawdown flat while PnL climbs; "$X saved vs naive Opus" telemetry on screen; self-custody + audit trail visible. (FRONTEND_PLAN §10.)

> **Out of scope (FRONTEND_PLAN §11, decisions):** no browser extension (now/future), no multitenant SaaS / per-user agents, no desktop app (web + PWA only), Option-B offline-local backend deferred (Convex cloud stays the bus).

### 8.12 Advisory Evaluation Harness ✅ Done (Jun 10)
- [x] 🟢 `agent/tests/test_advisory_impact.py` — 15 tests: replay harness (AllowAll baseline vs RegimeBlocker SB), drawdown non-worsening on trend + mixed windows, false-block-rate formula (<30%), useful-shrink-rate formula (>50%), mock blocker/shrinker unit tests.
- [x] 🟢 `core/risk/forecast.py`: `brier_score(buckets)` — MSE between confidence and win-rate; 0.0=perfect, 0.25=uninformed baseline. 4 tests.
- [x] 🟢 Memory lineage: `source_cycle_id: Optional[str]` added to `Reflection` + `ResearchDigest` dataclasses; threaded through `ReflectionWriter.reflect()`; stored in Convex `reflections.ts` (`source_cycle_id: v.optional(v.string())`). 5 tests. ⚠️ Run `bunx convex dev` to deploy schema change.
- ✅ **Exit:** advisory layer provably doesn't worsen drawdown; Brier score queryable; each reflection traces back to its originating trade. 479 passed, 1 skipped.

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

## STEP 9 — Packaging + Distribution ✅ Done (Jun 10)

> Build after the live window closes. Nothing here affects Track 1 scoring — it exists so judges can reproduce the demo and future operators can onboard in 30 seconds.

### 9.1 Onboarding wizard ✅ Done (Jun 10)
- [x] 🔴 `install.sh` — bash wizard with full dep checks (Python≥3.11/uv/bun/twak), interactive prompts with defaults from existing .env.local, `.env.local` write, Convex health probe, launch instructions, ASCII QR print. `--non-interactive` flag reads from env.

### 9.2 Deploy PWA ✅ Done (Jun 10)
- [x] 🟡 `web/vercel.json` — zero-config Vite build, SPA rewrites, SW cache headers.
- [x] 🟡 `agent/qr.py` — `resolve_url()` cascade: arg → `PWA_URL` env → localhost fallback.

### 9.3 Deploy agent ✅ Done (Jun 10)
- [x] 🟢 `Dockerfile` — multi-stage Python 3.11-slim + uv, `EXECUTION_BACKEND=paper`, health check.
- [x] 🟢 `fly.toml` — Fly.io config (512mb shared, iad region, auto-stop).

### 9.4 Demo video
- [ ] 🔴 Record demo video (~3 min). *(Still needed — screen recording is operator task.)*

### 9.5 curl-bootstrap install flow
- [ ] 🟡 Add bootstrap preamble to `install.sh`: detect `curl | bash` mode (empty `BASH_SOURCE[0]`), auto `git clone github.com/the-niresh/alien-trade ~/alien-trade`, then re-exec the real `install.sh` from the cloned copy.
- [ ] 🟡 Serve `install.sh` as a static file at `alientrade.niresh.tech/install.sh` (Vercel static asset or nginx alias on VPS).
- [ ] 🟡 One-liner for users: `curl -fsSL https://alientrade.niresh.tech/install.sh | bash`
- [ ] 🟢 After install: agent boots in paper mode, cockpit opens at `localhost:4173`, ASCII QR printed in terminal — cockpit is local-only (Hermes/OpenClaw pattern, keys never leave user's machine).

### 9.6 Public landing page — alientrade.niresh.tech
- [ ] 🟡 Build `web-landing/` — separate Vite/React static site (alien terminal aesthetic, matches cockpit identity).
- [ ] 🟡 Sections: Hero (product + one-liner install command), How it works (3 steps: Install → Configure TWAK → Run), Architecture diagram (Your Machine ↔ Convex ↔ BSC), Signal stack (S1/S2/S3/S4), Live stats panel (Convex public read-only: regime + last trade + cumulative PnL), GitHub CTA.
- [ ] 🟡 Deploy to Vercel, point `alientrade.niresh.tech` CNAME → `cname.vercel-dns.com` (Hostinger DNS panel).
- [ ] 🟢 Serve `install.sh` as `/install.sh` static file from the same Vercel deployment.
- [ ] 🟢 The VPS cockpit (`:4173`) remains the operator's private instance — not linked from the public page.

- ✅ **Exit (9.1–9.3):** judge can `bash install.sh` for one-command setup; `docker build .` for containerised demo; `vercel deploy web/` for hosted PWA.
- ⬜ **Exit (9.5–9.6):** any user can `curl -fsSL https://alientrade.niresh.tech/install.sh | bash` and be trading in paper mode within 5 minutes.

---

## Daily Discipline

1. **Out-of-sample only.** In-sample numbers are lies you tell yourself.
2. **Sim and live run the same `/core` code.** If they diverge, the sim is worthless.
3. **Costs in every backtest.** Gas, slippage, fees, funding, latency.
4. **Fewer knobs.** Every parameter you add is overfit you'll pay for live.
5. **Drawdown is the score.** Tune risk to protect it, not just to be safe.
6. **Testnet → paper → mainnet. Simulate before send. Always.**
7. **Every decision auditable.** If it's not in Convex, it didn't happen.
