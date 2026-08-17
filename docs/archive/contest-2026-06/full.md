What Is Alien-Trade?

  An autonomous BSC trading agent built for BNB Hack 2026 (DoraHacks). The mission is to win Track 1 — scored on risk-adjusted PnL
  and drawdown control over a 7-day live window (Jun 22–28). The entire architecture is engineered backward from one fact: judges
  score risk-adjusted performance, not raw return.

  The cockpit React PWA you see on screen is just the observable face of a much deeper system underneath.

  ---
  The Architecture: How This Agent Exists

  CMC Data (historical + live)
           ↓
     /core  ← THE CROWN JEWEL (pure Python)
     Signals → Regime → Strategy → Risk Engine
           ↓
     Live Runtime (FastAPI + LangGraph)
     Same /core code, live feed
           ↓
     Executor: simulate → TWAK sign → BNB send → confirm
           ↓
     Convex (real-time state bus)
           ↓
     PWA Dashboard (React + Vite)

  The key invariant: sim and live run identical code. /core is a pure Python library — no I/O, no API calls. The backtest imports it;
  the live agent imports it. If they ever diverge, the sim is lying.

  ---
  The Tools Stack

  ┌─────────────────┬──────────────────────────────────────┬────────────────────────────────────────────────────────────────────┐
  │      Layer      │                 Tool                 │                                Why                                 │
  ├─────────────────┼──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ Strategy + Sim  │ Python (numpy/pandas)                │ Deterministic, backtestable, optimizer-friendly                    │
  ├─────────────────┼──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ Live            │ FastAPI + LangGraph                  │ Supervisor pattern, multi-agent routing                            │
  │ orchestration   │                                      │                                                                    │
  ├─────────────────┼──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ Real-time state │ Convex                               │ Reactive queries — trades, decisions, ledger, risk state — UI      │
  │                 │                                      │ updates automatically                                              │
  ├─────────────────┼──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ Background jobs │ Trigger.dev                          │ Hourly decision loops, 30-min social ingestion, nightly Dreamer,   │
  │                 │                                      │ retries + dead-letter                                              │
  ├─────────────────┼──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ Cache + Memory  │ Upstash Redis + Upstash Vector       │ Redis for semantic cache; Vector for Second Brain (384-dim         │
  │                 │                                      │ embeddings, cosine)                                                │
  ├─────────────────┼──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ LLM             │ Claude (tier-routed)                 │ Haiku (T0) for routine reflection/cache checks; Sonnet (T1) for    │
  │                 │                                      │ research digests; off the trade hot path                           │
  ├─────────────────┼──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
  │ Frontend        │ React + Vite + shadcn/ui + Tailwind  │ PWA means no app store — accessible via QR code from any phone     │
  │                 │ + vite-plugin-pwa                    │                                                                    │
  └─────────────────┴──────────────────────────────────────┴────────────────────────────────────────────────────────────────────┘

  ---
  What Makes This Unique

  Three things no other team is doing together:

  1. CMC Data Others Ignore

  Most teams use price/TA only. We pull 4 orthogonal signal types from CMC:
  - S1 — Momentum/Trend (price, EMA, ATR-normalized)
  - S2 — Derivatives: funding rate + open interest (contrarian on extremes, OI confirms/denies trend)
  - S3 — Social/sentiment (rate-of-change of attention, not absolute — catches early trend formation)
  - S4 — On-chain flow (net exchange outflow = accumulation = bullish precursor)

  Each signal outputs a score in [-1, +1]. Combined: target = clip(w1*S1 + w2*S2 + w3*S3, -1, +1) × regime_gate

  2. Drawdown-First Optimization

  The objective function is:
  maximize  Sortino_oos  −  λ × max_drawdown_oos
  NOT raw return. This is the scoring rubric itself, baked into the optimizer. A flat equity curve with tight drawdown beats a
  volatile high-return bot on the 7-day judge window.

  3. Self-Improving via Second Brain (Hermes Loop)

  After every trade, the agent writes a structured reflection: {signals, regime, outcome, lesson} → compressed by Haiku → embedded
  into Upstash Vector. Before every trade, it queries: "Have we lost on this exact setup before?" — if yes, it blocks or halves the
  size. The agent improves during the live window without changing any /core code.

  ---
  How We Make Agents Specialized + Expert

  LangGraph Supervisor pattern with 4 advisory nodes, each specialized:

  ┌──────────────────┬──────────────────────────────────────────────────────────────────────────┬───────────────┬────────────────┐
  │      Agent       │                                   Role                                   │     Tier      │  On Hot Path?  │
  ├──────────────────┼──────────────────────────────────────────────────────────────────────────┼───────────────┼────────────────┤
  │ ResearchAgent    │ AutoResearch loop — fans out across all 5 eligible tokens every 2h,      │ T1 (Sonnet)   │ ❌ async       │
  │                  │ synthesizes market digest, stores in Second Brain                        │               │                │
  ├──────────────────┼──────────────────────────────────────────────────────────────────────────┼───────────────┼────────────────┤
  │ ReflectionWriter │ Post-trade — generates structured lesson from signals/regime/outcome     │ T0 (Haiku)    │ ❌ async after │
  │                  │                                                                          │               │  close         │
  ├──────────────────┼──────────────────────────────────────────────────────────────────────────┼───────────────┼────────────────┤
  │ Historian        │ Writes confirmed lessons to Vector; maintains institutional memory       │ T0 (Haiku)    │ ❌             │
  ├──────────────────┼──────────────────────────────────────────────────────────────────────────┼───────────────┼────────────────┤
  │ CoPilot          │ User-facing Q&A — grounds answers in Second Brain + live Convex state    │ T1 (Sonnet)   │ ❌ on-demand   │
  ├──────────────────┼──────────────────────────────────────────────────────────────────────────┼───────────────┼────────────────┤
  │ RiskGuard        │ Monitors for equity floor breach, signal staleness, circuit-break        │ Deterministic │ ✅ every cycle │
  │                  │ conditions                                                               │               │                │
  └──────────────────┴──────────────────────────────────────────────────────────────────────────┴───────────────┴────────────────┘

  None of these agents make the buy/sell decision. That's purely deterministic /core code.

  Each agent has self-eval rubrics (Step 8.13): the Researcher checks if its own digest is specific + actionable; the CoPilot warns
  when claims are uncited; the Reflector checks if lessons are concrete (not generic platitudes). Failed quality gates → tagged as
  low_confidence and visible in the cockpit.

  ---
  The Complete Decision Flow (Every Cycle)

  1. Fetch live bars (Binance OHLCV) + CMC live quote
  2. Inject S3 sentiment from social layer (30-min cron stamps sentiment_state)
  3. Enrich S2 from Binance Futures funding rate + OI
  4. compute signals → S1 score, S2 score, S3 score, S4 score
  5. Regime detector → trend / chop / high_vol / crash
  6. Strategy: raw = w1*S1 + w2*S2 + w3*S3 → apply regime_gate
  7. Risk engine: volatility-targeted sizing, Kelly-capped, hard guardrails
  8. BEFORE TRADE: VectorMistakeAvoidance.query("lost on this setup?")
     → block (≥75% loss rate) or halve size (≥50% loss rate)
  9. simulate-before-send (slippage check, quote check)
  10. Sign via TWAK (self-custody, zero raw keys)
  11. Send via BNB SDK → PancakeSwap
  12. On-chain confirm → ledger reconcile
  13. Write decision row to Convex (signals, regime, verdict, sizing, tx hash)
  14. AFTER TRADE (async): ReflectionWriter → lesson → Historian → Vector
  15. Equity floor check, signal staleness check, daily-loss kill check

  ---
  What's Already Built (Achievements)

  The build is essentially complete — 479+ tests passing across /core and /agent. Here's what's live:

  Core engine (the crown jewel):
  - Event-driven backtester with strict point-in-time access (zero look-ahead)
  - Full cost model: BSC gas, size-aware AMM slippage, swap fees, perp funding, fill latency
  - Walk-forward harness (optimize window N → validate on untouched N+1)
  - Metrics: Sharpe, Sortino, max drawdown, Calmar, win rate, rule-adherence score
  - S1+S2+S3+S4 signal library, each independently testable
  - Regime detector (deterministic)
  - Volatility-targeted + Kelly-capped risk engine
  - Daily-loss kill switch, circuit breaker, regime gating

  Live runtime:
  - Live decision loop importing identical /core strategy
  - Paper + OnchainExecutor with idempotency keys (no double-trades)
  - Kill switch: UI → Convex flag → agent halts within one cycle
  - Crash-state recovery (rebuilds ledger + risk state from Convex event log on restart)
  - 17/17 chaos tests green (mid-trade kill, failed tx, RPC timeout, slippage reject, replay)

  Second Brain (Hermes + Karpathy):
  - ReflectionWriter → Upstash Vector (embeddings live)
  - VectorMistakeAvoidance (deterministic, no LLM, fail-open)
  - ResearchSupervisor with fan-out across all 5 eligible tokens (concurrent)
  - 2-year historical pre-load script (walks full history, labels regimes, stores as institutional memory)
  - Dreamer (nightly curator: dedupe reflections cosine≥0.92, forecast calibration, age-out stale research)
  - Brier score for forecast calibration, memory lineage via source_cycle_id

  Agent Team (LangGraph):
  - Supervisor with all 4 advisory nodes
  - MAX_HOPS=4 budget per run (prevents runaway spend)
  - 90-min research-tick dedupe per symbol
  - Idempotent reflection (same cycle_id = one lesson, no duplicates)
  - Failure visibility: every node exception → KIND_CONTROL AgentEvent in cockpit

  Social Layer:
  - RSS + Farcaster ingestion live
  - Deterministic sentiment scorer (no LLM on this path)
  - 30-min Trigger.dev cron → stamps sentiment_state on Convex → DecisionLoop._inject_sentiment uses it

  Infra:
  - Trigger.dev jobs: hourly decision loop, 1-min trade watchdog, reflection job, social ingestion, nightly Dreamer
  - Telegram two-way bot: equity-floor alerts, kill-switch fires, daily summary, /status /halt /resume /pause, inline approve/reject
  buttons
  - install.sh onboarding wizard, Dockerfile, fly.toml, web/vercel.json
  - QR code in terminal (ASCII render of PWA URL on agent startup)

  Running on this VPS 24/7 — alien-trade.service (paper mode, autopilot on), alien-cockpit.service (PWA on :4173), alien-digest.timer
  (hourly Telegram summary).

  ---
  Pattern Recognition — How We Do It

  Three layers, all deterministic:

  1. Technical regime detection (deterministic TA):
  - ADX + EMA slope → trend vs chop
  - ATR/realized vol spike → high_vol regime
  - funding + flow capitulation → crash/risk-off
  - Each regime maps to a gate multiplier (0.0 to 1.0 on the strategy target)

  2. Walk-forward parameter stability (optimization-as-recognition):
  - Instead of a single backtest, we roll train→validate windows forward
  - We reject fragile peaks — pick the parameter neighborhood that works robustly across trend/chop/high-vol/crash slices
  - This is how we recognize which signal weights actually generalize

  3. Semantic memory recall (Upstash Vector, 384-dim embeddings):
  - Each trade reflection is embedded under its setup key (regime + signal combo)
  - Before every live trade, cosine similarity search: "have we seen this setup, and what happened?"
  - The pattern isn't hard-coded — it's learned from actual trade history and recalled via embedding distance

  ---
  The 3 Sponsor Layers — How We Use Each Wisely

  L1: CoinMarketCap (CMC) Agent Hub

  What it provides: Price/TA, derivatives (funding/OI), social/sentiment, on-chain flow — all in one place.

  How we use it:
  - Historical data → feeds the backtest engine (the competitive edge). Most teams get this from one source; we pull orthogonal data
  types (price + derivatives + social + flow) and combine them
  - Live feed → same fields the sim uses (sim/live parity enforced)
  - CMC Skill Hub → 8 curated skills loaded by the ResearchAgent and CoPilot for grounded, real-time market context (market_regime,
  funding_regime, kol_sentiment, etc.)
  - Track-2 Skill → our strategy is published as a CMC Skills Marketplace skill (alien_trade_multi_signal_score, unique_name), so
  judges can call it live
  - x402 micropayments → every CMC API call from the agent runtime pays per-call via the x402 protocol; infra ready, activation gated
  on X402_WALLET_ADDRESS

  L2: Trust Wallet Agent Kit (TWAK)

  What it provides: Self-custody signing — the private key never leaves the device.

  How we use it:
  - Every scored trade goes through twak swap — this is the organizer's ruling; only twak swap transactions count toward PnL in Track
  1
  - TwakSwapExecutor is the default execution backend (EXECUTION_BACKEND=twak) — zero raw keys in code or logs
  - Multi-step sequences (approve + swap) each signed on-device
  - twak compete register wrapper for on-chain competition registration before Jun 22
  - The "self-custody" story feeds the TWAK special-prize writeup

  L3: BNB AI Agent SDK

  What it provides: On-chain interaction with PancakeSwap on BSC.

  How we use it:
  - simulate-before-send: every order is simulated first (slippage check, quote check) — only sent if the simulation passes
  - PancakeSwap V3 calldata encoding for spot swaps on the eligible token list ({ETH,CAKE,UNI,LINK,AAVE})
  - Gas estimation from real fills → feeds back into the cost model in /core backtest (sim/live cost parity)
  - On-chain receipt as ledger source of truth — real fill price, real gas paid, not estimated values
  - Perps dropped from the scored path (not twak swap → don't count toward PnL)

  The wisdom in how they fit together: CMC is the data edge (orthogonal signals), TWAK is the safety layer (self-custody, zero key
  exposure), BNB SDK is the execution layer (actual trades). None of them make the trading decision — that lives in pure
  deterministic Python that can be backtested, validated, and optimized.


 S1 — Momentum / Trend
  Is the price going up or down consistently? Uses EMA (moving average) crossovers + rate of change. If ETH has been climbing for the
  last 8 hours faster than the last 21 hours → bullish signal. The backbone — tells you the direction.

  S2 — Derivatives (Funding Rate + Open Interest)
  What are futures traders betting on? Funding rate = when longs are paying shorts, everyone is over-leveraged long → contrarian
  signal to expect a dump. Open Interest = total money in futures positions — rising OI confirms a move, falling OI means the move is
  fake. Tells you if the trend has conviction or is about to reverse.

  S3 — Sentiment (Social + Fear & Greed)
  What is the crowd feeling? Rising social mentions of ETH + fear & greed index swinging from extreme fear to neutral = people
  starting to buy in. The trick is rate-of-change, not the absolute level — a sentiment spike is more useful than a high sentiment
  that's been flat for days.

  S4 — On-chain Flow (Exchange Flow + Whale Activity)
  Are big wallets moving coins onto exchanges (to sell) or off exchanges (to hold)? Net outflow from exchanges = whales accumulating
  = bullish precursor. This is the "smart money" signal.
