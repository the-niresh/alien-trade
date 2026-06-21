import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { assertControlToken } from "./control";

/**
 * Record one signal snapshot per cycle. cycle_id is the idempotency key.
 */
export const record = mutation({
  args: {
    cycle_id: v.string(),
    symbol: v.string(),
    timestamp_ms: v.number(),
    momentum_ema_fast: v.optional(v.number()),
    momentum_ema_slow: v.optional(v.number()),
    momentum_roc:      v.optional(v.number()),
    momentum_atr:      v.optional(v.number()),
    funding_rate:      v.optional(v.number()),
    open_interest:     v.optional(v.number()),
    social_score:      v.optional(v.number()),
    social_roc:        v.optional(v.number()),
    net_flow_usd:      v.optional(v.number()),
    composite_score:   v.optional(v.number()),
    control_token:     v.optional(v.string()),
  },
  returns: v.id("signals"),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    const { control_token: _ct, ...fields } = args;
    void _ct;
    const existing = await ctx.db
      .query("signals")
      .withIndex("by_cycle", (q) => q.eq("cycle_id", fields.cycle_id))
      .unique();
    if (existing) return existing._id;
    return await ctx.db.insert("signals", fields);
  },
});

/**
 * Latest signal snapshot, optionally filtered by symbol.
 */
export const latest = query({
  args: { symbol: v.optional(v.string()) },
  returns: v.union(v.any(), v.null()),
  handler: async (ctx, args) => {
    if (args.symbol) {
      return await ctx.db
        .query("signals")
        .withIndex("by_symbol_time", (q) => q.eq("symbol", args.symbol!))
        .order("desc")
        .first();
    }
    return await ctx.db
      .query("signals")
      .withIndex("by_symbol_time")
      .order("desc")
      .first();
  },
});

/**
 * Recent signal snapshots — newest first.
 */
export const recent = query({
  args: { limit: v.optional(v.number()) },
  returns: v.array(v.any()),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("signals")
      .withIndex("by_symbol_time")
      .order("desc")
      .take(args.limit ?? 50);
  },
});
