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
});
