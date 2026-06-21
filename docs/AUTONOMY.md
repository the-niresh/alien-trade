# Autonomous Strengthening Protocol

How to run Claude Code unattended on the VPS to keep strengthening alien-trade **safely** —
without overfitting the strategy or letting an LLM blind-deploy to a trading agent.

## Principle: autonomous research, gated deployment

- **Autonomous (safe, reversible, additive):** ingest data, run backtests / walk-forward,
  propose changes on a working branch, run tests, write validation reports + session logs,
  record *negative* results so dead ends aren't retried.
- **Human-gated (irreversible / outward):** `git commit`/push, deploy or restart the live
  agent, anything touching real money / mainnet / funding, changing a LOCKED decision.
  The loop STAGES these and notifies via Telegram; Nire approves.

## Per-iteration loop

1. Pick the top **unblocked** item from QUEUE.
2. Implement it (working tree / branch). **≤ 1 new knob per iteration; no free param sweeps.**
3. **Validate (walk-forward OOS only — never select on in-sample):** run
   `retune.py` across the eligible universe `{ETH,CAKE,UNI,LINK,AAVE}` at 1h. Keep the
   change ONLY if the objective (`Sortino − 2·|MaxDD|`) improves vs the current committed
   baseline on **≥ 4 of 5** assets. Run the full `core` test suite (must stay green).
4. **If pass:** append results to `docs/VALIDATION_1H.md`, add a line to `PENDING_APPROVAL`
   below, and Telegram-ping Nire. Do **not** auto-commit or auto-deploy.
5. **If fail:** revert the change, log the negative result in NEGATIVE RESULTS below
   (a negative result is a real result — it narrows the search).
6. Update QUEUE, write/append a vault session log. Self-pace to the next iteration.

## Hard guardrails (never violate)

- Walk-forward OOS only; in-sample numbers never justify a change (locked #7).
- Never auto-commit, auto-push, auto-deploy, restart the live unit, or fund/trade real money.
- Never edit a LOCKED decision (CLAUDE.md) without explicit Nire approval.
- Every kept change must carry its OOS evidence in `docs/VALIDATION_1H.md`.
- 2–3 signals max; minimal knobs; full cost model in every backtest.

## Human gates — require Nire's approval (staged, not executed)

- [ ] Deploy v1+v2 cash-default + rising-trend redesign to the paper agent (`systemctl restart`)
- [ ] Commit the redesign to git

---

## QUEUE — prioritized, dependency-ordered

> Ordering rule learned the hard way: **alpha is the gate.** Harness / agents / skills /
> token work is wasted effort while the deterministic core has no edge. Fix the core first.

### P1 — Alpha (the gating work)
- [x] ~~**Cross-sectional rotation**~~ — PARKED (negative result, see below). Portfolio
  backtester built (`core/backtest/portfolio.py`, reusable); rotation strategy itself
  loses badly in this regime. The cash-default single-asset v1+v2 remains the baseline.
- [ ] **Exit/risk lever (thesis-factory next direction)** — the first OOS thesis batch
  (T-001…T-006, all FALSIFIED — see `docs/THESIS_LEDGER.md`) proved **drawdown, not entry,
  is the binding constraint** (T-006 had positive Sortino on ETH/CAKE yet failed on a
  −14.7% open drawdown). Test hard/ATR stops, regime-conditional entry (long only in
  confirmed trend/recovery), and cash-default low-time-in-market rules. **← next up**
- [ ] **Vol-targeted position sizing** — scale size by inverse ATR to flatten drawdown
  further (incremental; the core posture is already capital-preservation).
- [ ] **Complete the signal data:** find an OI source reachable from the VPS (Binance
  `openInterestHist` is blocked here) to finish S2; wire S4 on-chain flow (currently 0).
  Then re-tune signal weights on the full S1–S4 stack.
- [ ] **Regime detector recalibration for 1h** — current thresholds are daily-calibrated
  (lookback=20, slope 0.3%/bar, crash −15%/20bars); recalibrate for hourly sizing/crash.

### P2 — Data & results integrity
- [ ] **CMC Agent Hub** historical + live feed (+ x402 micropayments) replacing the keyless
  Binance fallback — the competition-aligned source and a sponsor prize ($2k).
- [ ] Reset stale Convex ledger rows (equity ≈ $9,831) for a clean paper corpus.

### P3 — Agents / Second Brain (only once the core has edge)
- [ ] Turn `SECOND_BRAIN=1` (deps: langgraph, anthropic, upstash-redis, upstash-vector);
  verify the Hermes reflection loop (post-trade learning) and Karpathy AutoResearch loop.
- [ ] 2-year historical preload into Upstash Vector (institutional memory — locked #5).
- [ ] Verify the OpenAI fallback in prod once `OPENAI_API_KEY` is set (built 2026-06-12).

### P4 — Skills & skill-picking (Nire's interest)
- [ ] **Skill-router node** — a supervisor node that selects the right skill / sub-agent and
  injects it at the right point in the LangGraph (`agent/skills` + `agent/graph` are the
  seam). The "skill picking" capability.
- [ ] **Token reduction** — exploit tier-routing + the Upstash Redis semantic cache; route
  cheap/bulk LLM jobs to the smallest adequate tier; measure savings via `telemetry`.

### P5 — Live readiness & extensibility
- [ ] End-to-end `twak swap` on a funded wallet; enforce the ≥1 trade/day activity floor.
- [ ] Telegram token wiring (Nire pastes `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`).
- [ ] **Multi-wallet** support (Nire's stated want) — wallet-scoped ledger/equity.

---

## PENDING_APPROVAL (loop appends; Nire clears)
- (Deploy + commit of v1+v2 redesign — awaiting approval.)

## NEGATIVE RESULTS (don't retry these)
- Original trend/EMA-cross flipper: negative OOS on all 5 eligible assets at 1h, even with
  funding+sentiment live (2026-06-11). The "edge is in S2/S3/S4" hypothesis is falsified.
- Per-asset entry tuning (rising-trend filter, v2): only a marginal objective gain over v1;
  diminishing returns — pivot to cross-sectional rotation for the next real lever.
- Cross-sectional rotation (2026-06-12): tested 3 variants — naive (every-bar), daily
  cadence + switch band, and ride-winner/exit-only. ALL catastrophic (obj −2.2 to −2.6,
  ret −87% to −100%) vs cash 0.0 and single-asset CAKE −0.026. Accounting verified clean
  (enter-once-and-hold = flat). Root cause: the eligible universe fell ~57% *uniformly*
  (no dispersion), so "hold the strongest" = "hold the slowest faller"; rotation forces
  more market exposure than cash-default and eats churn on top. Rotation only helps with
  cross-sectional dispersion, which this data lacks. Don't tune it for a hoped-for bull
  regime (overfit). The cash-default v1+v2 (mostly-in-USDT) is the right posture here.
- Long-only trend/momentum thesis batch T-001…T-006 (2026-06-14, via the DSL + real-cost
  harness `research/evaluate.py`): ALL FALSIFIED, 0/5 assets beat cash — full numbers in
  `docs/THESIS_LEDGER.md`. Costs dominate naive single-line crossovers (700+ fills ≈ −60%
  from fees/slippage alone → hysteresis mandatory); no long-only edge exists in the eligible
  universe (it fell ~57% near-uniformly). Don't retry bare trend/momentum entries. The open
  lever is **exit/risk** (T-006 showed a faint positive entry edge swamped by a −14.7% DD).
