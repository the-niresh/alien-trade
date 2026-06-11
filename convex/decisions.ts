import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const signals = v.object({
  momentum:    v.optional(v.number()),
  derivatives: v.optional(v.number()),
  sentiment:   v.optional(v.number()),
  flow:        v.optional(v.number()),
});

const verdict = v.union(
  v.literal("allow"),
  v.literal("reduce"),
  v.literal("block"),
);

/**
 * Record one decision cycle. cycle_id is the idempotency key: if a decision
 * with the same cycle_id already exists we return it untouched instead of
 * writing a duplicate. This is the audit anchor — one row per cycle, always.
 */
export const record = mutation({
  args: {
    cycle_id: v.string(),
    symbol: v.string(),
    timestamp_ms: v.number(),
    regime: v.string(),
    signals,
    target_position_usd: v.number(),
    risk_verdict: verdict,
    risk_reason: v.optional(v.string()),
    final_size_usd: v.number(),
    trade_id: v.optional(v.id("trades")),
    setup_key: v.optional(v.string()),
  },
  returns: v.id("decisions"),
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("decisions")
      .withIndex("by_cycle", (q) => q.eq("cycle_id", args.cycle_id))
      .unique();
    if (existing) {
      // Idempotent: a re-run of the same cycle links the trade if newly known.
      if (args.trade_id && !existing.trade_id) {
        await ctx.db.patch(existing._id, { trade_id: args.trade_id });
      }
      return existing._id;
    }
    return await ctx.db.insert("decisions", args);
  },
});

export const recent = query({
  args: { limit: v.optional(v.number()) },
  returns: v.array(
    v.object({
      _id: v.id("decisions"),
      _creationTime: v.number(),
      cycle_id: v.string(),
      symbol: v.string(),
      timestamp_ms: v.number(),
      regime: v.string(),
      signals,
      target_position_usd: v.number(),
      risk_verdict: verdict,
      risk_reason: v.optional(v.string()),
      final_size_usd: v.number(),
      trade_id: v.optional(v.id("trades")),
      setup_key: v.optional(v.string()),
    }),
  ),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("decisions")
      .withIndex("by_timestamp")
      .order("desc")
      .take(args.limit ?? 50);
  },
});
