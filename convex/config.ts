import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// Singleton key for the global live-agent config row.
const KEY = "global";

const tradingMode = v.union(
  v.literal("testnet"),
  v.literal("paper"),
  v.literal("mainnet"),
);

// Autopilot config (user-set targets) + persisted ratchet state.
const autopilotConfig = v.object({
  enabled: v.boolean(),
  profit_target_pct: v.optional(v.number()),
  profit_target_abs: v.optional(v.number()),
  protect_principal: v.optional(v.boolean()),
  min_recycle_confidence: v.optional(v.number()),
  recycle_blocked_regimes: v.optional(v.array(v.string())),
  trailing_giveback_pct: v.optional(v.number()),
  daily_profit_target_pct: v.optional(v.number()),
  loss_cooldown_hours: v.optional(v.number()),
});

const autopilotState = v.object({
  protected_floor: v.number(),
  cycle_start_equity: v.number(),
  peak_equity: v.number(),
  day_start_equity: v.number(),
  day_key: v.string(),
  halted_for_day: v.boolean(),
  cooldown_until_ms: v.number(),
});

/**
 * Read the live config (kill switch + caps). The agent calls this every cycle.
 * Returns null when not yet seeded — the agent treats that as "not halted".
 */
export const get = query({
  args: {},
  returns: v.union(
    v.null(),
    v.object({
      _id: v.id("config"),
      _creationTime: v.number(),
      key: v.string(),
      halted: v.boolean(),
      trading_mode: tradingMode,
      max_position_usd: v.number(),
      daily_loss_limit_usd: v.number(),
      max_drawdown_pct: v.number(),
      token_allowlist: v.array(v.string()),
      equity_floor: v.optional(v.number()),
      strategy_name: v.optional(v.string()),
      autopilot: v.optional(autopilotConfig),
      autopilot_state: v.optional(autopilotState),
      updated_at_ms: v.number(),
    }),
  ),
  handler: async (ctx) => {
    return await ctx.db
      .query("config")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
  },
});

/**
 * Cheap kill-switch check — the hot-path read every decision cycle uses.
 * Defaults to false (not halted) when unseeded so a missing config never
 * accidentally freezes the agent. Use `ensure` to seed before going live.
 */
export const isHalted = query({
  args: {},
  returns: v.boolean(),
  handler: async (ctx) => {
    const row = await ctx.db
      .query("config")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
    return row?.halted ?? false;
  },
});

/** Seed the singleton config row if it doesn't exist yet (idempotent). */
export const ensure = mutation({
  args: {
    trading_mode: v.optional(tradingMode),
    max_position_usd: v.optional(v.number()),
    daily_loss_limit_usd: v.optional(v.number()),
    max_drawdown_pct: v.optional(v.number()),
    token_allowlist: v.optional(v.array(v.string())),
  },
  returns: v.id("config"),
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("config")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
    if (existing) return existing._id;

    return await ctx.db.insert("config", {
      key: KEY,
      halted: false,
      trading_mode: args.trading_mode ?? "paper",
      max_position_usd: args.max_position_usd ?? 2000,
      daily_loss_limit_usd: args.daily_loss_limit_usd ?? 500,
      max_drawdown_pct: args.max_drawdown_pct ?? 0.15,
      token_allowlist: args.token_allowlist ?? ["ETH", "CAKE", "UNI", "LINK", "AAVE"],
      updated_at_ms: Date.now(),
    });
  },
});

/** Kill switch. UI (or co-pilot) flips this; the agent halts within one cycle. */
export const setHalted = mutation({
  args: { halted: v.boolean() },
  returns: v.null(),
  handler: async (ctx, args) => {
    const row = await ctx.db
      .query("config")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
    if (!row) {
      await ctx.db.insert("config", {
        key: KEY,
        halted: args.halted,
        trading_mode: "paper",
        max_position_usd: 2000,
        daily_loss_limit_usd: 500,
        max_drawdown_pct: 0.15,
        token_allowlist: ["ETH", "CAKE", "UNI", "LINK", "AAVE"],
        updated_at_ms: Date.now(),
      });
      return null;
    }
    await ctx.db.patch(row._id, { halted: args.halted, updated_at_ms: Date.now() });
    return null;
  },
});

/**
 * Trading-mode toggle — the user/judge picks testnet | paper | mainnet from the UI.
 * Dedicated (vs `updateLimits`) so the toggle is a single obvious call and seeds the
 * singleton if it's missing. The agent reads `config.trading_mode` each cycle and
 * routes execution accordingly (testnet vs paper vs self-custody mainnet).
 */
export const setTradingMode = mutation({
  args: { trading_mode: tradingMode },
  returns: v.null(),
  handler: async (ctx, args) => {
    const row = await ctx.db
      .query("config")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
    if (!row) {
      await ctx.db.insert("config", {
        key: KEY,
        halted: false,
        trading_mode: args.trading_mode,
        max_position_usd: 2000,
        daily_loss_limit_usd: 500,
        max_drawdown_pct: 0.15,
        token_allowlist: ["ETH", "CAKE", "UNI", "LINK", "AAVE"],
        updated_at_ms: Date.now(),
      });
      return null;
    }
    await ctx.db.patch(row._id, {
      trading_mode: args.trading_mode,
      updated_at_ms: Date.now(),
    });
    return null;
  },
});

/** Adjust risk caps live (allowed during the frozen window — caps only). */
export const updateLimits = mutation({
  args: {
    trading_mode: v.optional(tradingMode),
    max_position_usd: v.optional(v.number()),
    daily_loss_limit_usd: v.optional(v.number()),
    max_drawdown_pct: v.optional(v.number()),
    token_allowlist: v.optional(v.array(v.string())),
    equity_floor: v.optional(v.number()),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    const row = await ctx.db
      .query("config")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
    if (!row) throw new Error("config not seeded — call config:ensure first");
    const patch: Record<string, unknown> = { updated_at_ms: Date.now() };
    for (const k of [
      "trading_mode",
      "max_position_usd",
      "daily_loss_limit_usd",
      "max_drawdown_pct",
      "token_allowlist",
      "equity_floor",
    ] as const) {
      if (args[k] !== undefined) patch[k] = args[k];
    }
    await ctx.db.patch(row._id, patch);
    return null;
  },
});

/** Cockpit: pick the active strategy (momentum|contrarian|balanced|defensive).
 * The agent reads `config.strategy_name` and rebuilds its strategy while flat. */
export const setStrategy = mutation({
  args: { strategy_name: v.string() },
  returns: v.null(),
  handler: async (ctx, args) => {
    const row = await ctx.db
      .query("config")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
    if (!row) throw new Error("config not seeded — call config:ensure first");
    await ctx.db.patch(row._id, {
      strategy_name: args.strategy_name,
      updated_at_ms: Date.now(),
    });
    return null;
  },
});

/** Cockpit: set the Autopilot capital-manager targets (profit-lock, ratchet,
 * trailing, daily target, recycle gate). The agent reads these live. */
export const setAutopilot = mutation({
  args: { autopilot: autopilotConfig },
  returns: v.null(),
  handler: async (ctx, args) => {
    const row = await ctx.db
      .query("config")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
    if (!row) throw new Error("config not seeded — call config:ensure first");
    await ctx.db.patch(row._id, {
      autopilot: args.autopilot,
      updated_at_ms: Date.now(),
    });
    return null;
  },
});

/** Agent: persist the autopilot ratchet (protected floor etc.) each cycle so a
 * restart keeps the banked floor. Off the cockpit; written by the loop. */
export const setAutopilotState = mutation({
  args: { state: autopilotState },
  returns: v.null(),
  handler: async (ctx, args) => {
    const row = await ctx.db
      .query("config")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
    if (!row) return null;
    await ctx.db.patch(row._id, {
      autopilot_state: args.state,
      updated_at_ms: Date.now(),
    });
    return null;
  },
});
