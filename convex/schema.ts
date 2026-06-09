import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  // Every executed or simulated trade
  trades: defineTable({
    symbol: v.string(),
    side: v.union(v.literal("buy"), v.literal("sell")),
    size_usd: v.number(),
    fill_price: v.number(),
    fee_usd: v.number(),
    gas_usd: v.number(),
    slippage_usd: v.number(),
    tx_hash: v.optional(v.string()),
    mode: v.union(v.literal("testnet"), v.literal("paper"), v.literal("mainnet")),
    timestamp_ms: v.number(),
  })
    .index("by_symbol", ["symbol"])
    .index("by_timestamp", ["timestamp_ms"]),

  // Every decision cycle: what the agent saw, computed, and decided
  decisions: defineTable({
    cycle_id: v.string(),            // idempotency key
    symbol: v.string(),
    timestamp_ms: v.number(),
    regime: v.string(),              // "trend" | "chop" | "high_vol" | "crash"
    signals: v.object({
      s1_momentum: v.optional(v.number()),
      s2_funding: v.optional(v.number()),
      s2_oi: v.optional(v.number()),
      s3_sentiment: v.optional(v.number()),
      s4_flow: v.optional(v.number()),
    }),
    target_position_usd: v.number(),
    risk_verdict: v.union(v.literal("allow"), v.literal("reduce"), v.literal("block")),
    risk_reason: v.optional(v.string()),
    final_size_usd: v.number(),
    trade_id: v.optional(v.id("trades")),
  })
    .index("by_cycle", ["cycle_id"])
    .index("by_timestamp", ["timestamp_ms"]),

  // Hermes self-learning: post-trade reflections stored for mistake-avoidance
  reflections: defineTable({
    trade_id: v.id("trades"),
    cycle_id: v.string(),
    timestamp_ms: v.number(),
    signals_snapshot: v.string(),    // JSON-serialised signal state
    regime: v.string(),
    outcome_pnl_usd: v.number(),
    outcome_label: v.union(v.literal("win"), v.literal("loss"), v.literal("scratch")),
    lesson: v.string(),              // compressed lesson for Vector store
    vector_id: v.optional(v.string()), // Upstash Vector doc ID after upsert
  })
    .index("by_trade", ["trade_id"])
    .index("by_outcome", ["outcome_label"]),

  // Running PnL + cost ledger (one row per trade, cumulative)
  ledger: defineTable({
    trade_id: v.id("trades"),
    timestamp_ms: v.number(),
    realized_pnl_usd: v.number(),
    cumulative_pnl_usd: v.number(),
    cumulative_fees_usd: v.number(),
    cumulative_gas_usd: v.number(),
    peak_equity_usd: v.number(),
    current_drawdown_pct: v.number(),
  })
    .index("by_timestamp", ["timestamp_ms"]),

  // Full audit log — every agent action, immutable append-only
  audit: defineTable({
    timestamp_ms: v.number(),
    event_type: v.string(),          // "decision" | "trade" | "reflection" | "risk_veto" | "kill_switch" | "error"
    cycle_id: v.optional(v.string()),
    payload: v.string(),             // JSON blob
    severity: v.union(v.literal("info"), v.literal("warn"), v.literal("error")),
  })
    .index("by_event_type", ["event_type"])
    .index("by_timestamp", ["timestamp_ms"]),

  // Live agent config + kill switch — UI writes here, agent reads each cycle
  config: defineTable({
    key: v.string(),                 // singleton key e.g. "global"
    halted: v.boolean(),             // kill switch
    trading_mode: v.union(v.literal("testnet"), v.literal("paper"), v.literal("mainnet")),
    max_position_usd: v.number(),
    daily_loss_limit_usd: v.number(),
    max_drawdown_pct: v.number(),
    token_allowlist: v.array(v.string()),
    updated_at_ms: v.number(),
  })
    .index("by_key", ["key"]),

  // Live risk state — agent updates each cycle; UI reads for dashboard
  risk_state: defineTable({
    key: v.string(),                 // singleton key e.g. "global"
    daily_loss_usd: v.number(),
    open_exposure_usd: v.number(),
    current_drawdown_pct: v.number(),
    peak_equity_usd: v.number(),
    circuit_breaker_active: v.boolean(),
    last_updated_ms: v.number(),
  })
    .index("by_key", ["key"]),

  // Signal snapshots per cycle — for debugging + regime analysis
  signals: defineTable({
    cycle_id: v.string(),
    symbol: v.string(),
    timestamp_ms: v.number(),
    s1_ema_fast: v.optional(v.number()),
    s1_ema_slow: v.optional(v.number()),
    s1_roc: v.optional(v.number()),
    s1_atr: v.optional(v.number()),
    s2_funding_rate: v.optional(v.number()),
    s2_open_interest: v.optional(v.number()),
    s3_social_score: v.optional(v.number()),
    s3_social_roc: v.optional(v.number()),
    s4_net_flow_usd: v.optional(v.number()),
    composite_score: v.optional(v.number()),
  })
    .index("by_cycle", ["cycle_id"])
    .index("by_symbol_time", ["symbol", "timestamp_ms"]),

  // Social layer — the user's curated watchlist of traders/channels to watch.
  // USER-writable (the "add your list" surface); the agent only reads it.
  social_sources: defineTable({
    platform: v.union(
      v.literal("rss"), v.literal("farcaster"),
      v.literal("telegram"), v.literal("twitter"),
    ),
    handle: v.string(),              // feed URL | username | channel
    label: v.string(),               // display name
    weight: v.number(),              // user trust weight
    enabled: v.boolean(),
    added_ms: v.number(),
  })
    .index("by_platform", ["platform"]),

  // Normalised posts ingested from the watchlist (agent-written, UI feed).
  social_posts: defineTable({
    post_id: v.string(),             // "<platform>:<native_id>" (dedupe key)
    platform: v.string(),
    author: v.string(),
    text: v.string(),
    url: v.string(),
    ts_ms: v.number(),
    symbols: v.array(v.string()),    // detected tickers
  })
    .index("by_post_id", ["post_id"])
    .index("by_ts", ["ts_ms"]),

  // Off-hot-path deterministic sentiment feature per symbol (feeds signal S3,
  // same bridge shape as forecast_state: a bounded number crosses into the core).
  sentiment_state: defineTable({
    symbol: v.string(),
    score: v.number(),               // [-1, 1]
    confidence: v.number(),          // [0, 1]
    n_posts: v.number(),
    ts_ms: v.number(),
    top_post_ids: v.array(v.string()),
  })
    .index("by_symbol", ["symbol"]),

  // ── Agent team layer (STEP 8) — contracts mirrored in agent/graph/contracts.py ──

  // Agent Activity Channel: append-only trace stream — the "glass cockpit" the
  // PWA subscribes to (read-only). The marketing surface AND the human-readable
  // audit log, same data. Headline is template-rendered from structured fields
  // (cheap, deterministic, zero hot-path latency). `detail` is a JSON blob like
  // `audit.payload` so each agent's structured payload stays flexible.
  agent_events: defineTable({
    cycle_id: v.optional(v.string()), // ties one team's actions to one decision
    ts_ms: v.number(),
    agent: v.string(),                // "Strategist" | "Risk Officer" | "Historian" | ...
    kind: v.union(
      v.literal("observation"), v.literal("analysis"), v.literal("verdict"),
      v.literal("action"), v.literal("handoff"), v.literal("control"),
    ),
    headline: v.string(),             // one-line, the agent's own voice
    detail: v.string(),               // JSON structured payload
    refs: v.array(v.string()),        // reflection/digest ids, tx hash
  })
    .index("by_cycle", ["cycle_id"])
    .index("by_ts", ["ts_ms"])
    .index("by_agent", ["agent"]),

  // Option-B forecast bridge (per symbol): the ONE deterministic number the
  // Researcher's forecast may push into the decision. Read by the Risk Officer
  // as a size multiplier that can ONLY shrink (clamp + decay-to-neutral math
  // lives in core/risk, STEP 8.4). A stale or failed forecast decays to 1.0
  // (neutral) so it can never silently throttle trading.
  forecast_state: defineTable({
    symbol: v.string(),
    confidence: v.number(),          // [0, 1]; 1.0 = neutral / no shrink
    reason: v.string(),              // one-line why (e.g. "OI/price divergence")
    ttl_ms: v.number(),              // age past which it decays to neutral
    ts_ms: v.number(),
  })
    .index("by_symbol", ["symbol"]),

  // Live scorecard singleton — the agent's GOAL made measurable (docs/GOAL.md).
  // Computed in core/scorecard.py (sim AND live share it, locked decision #2) and
  // upserted each cycle / at window close. The glass cockpit reads this for the
  // headline "how are we doing against the objective" panel. Nullable lines are
  // genuinely absent in sim (no timestamps/exposure) — never faked. `operational`
  // and `rule_adherence` are JSON blobs (like `audit.payload`) carrying the
  // autonomy + constraint-compliance facts the runtime knows.
  scorecard: defineTable({
    key: v.string(),                          // singleton, e.g. "global"
    // objective (the one number we optimise: sortino - 2*|maxDD|)
    objective: v.number(),
    // returns
    total_return: v.number(),
    net_pnl_usd: v.number(),
    // drawdown (depth + duration)
    max_drawdown: v.number(),
    max_drawdown_duration_days: v.union(v.number(), v.null()),
    // risk-adjusted
    sortino: v.number(),
    sharpe: v.number(),
    calmar: v.number(),
    // consistency
    pct_positive_days: v.union(v.number(), v.null()),
    daily_pnl_vol: v.union(v.number(), v.null()),
    // trade quality
    n_trades: v.number(),
    win_rate: v.number(),
    profit_factor: v.number(),
    expectancy_usd: v.number(),
    worst_trade_usd: v.number(),
    // cost efficiency
    total_cost_usd: v.number(),
    cost_ratio: v.number(),
    // exposure efficiency
    turnover: v.number(),
    avg_exposure_pct: v.union(v.number(), v.null()),
    peak_exposure_pct: v.union(v.number(), v.null()),
    // rule adherence (denormalised flags for cheap UI badges + JSON detail)
    rule_adherence_clean: v.boolean(),
    rule_violations: v.number(),
    operational: v.string(),                  // JSON: uptime, unattended cycles, recoveries
    rule_adherence: v.string(),               // JSON: violations, blocks, halts, peak exposure
    updated_at_ms: v.number(),
  })
    .index("by_key", ["key"]),

  // The single user-writable control doc — three graduated stops (§7). The PWA
  // is the ONLY writer; the supervisor + DecisionLoop are reactive readers.
  // `trading_halted` mirrors `config.halted` (the Tier-0 kill switch); the other
  // flags only quiet the Tier-1 advisory team and never touch trading.
  agent_control: defineTable({
    key: v.string(),                 // singleton, e.g. "global"
    agents_paused: v.boolean(),      // quiet the whole Tier-1 team
    paused_agents: v.array(v.string()), // finer-grained per-agent pause
    trading_halted: v.boolean(),     // mirrors config.halted
    stop_response_id: v.optional(v.string()), // cancel one in-flight action
    updated_by: v.string(),
    ts_ms: v.number(),
  })
    .index("by_key", ["key"]),
});
