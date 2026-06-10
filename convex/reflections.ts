import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const outcome = v.union(
  v.literal("win"),
  v.literal("loss"),
  v.literal("scratch"),
);

/**
 * Hermes self-learning: record one post-trade reflection. Idempotent on
 * (trade_id, cycle_id) — a retry of the same reflection patches the lesson/vector
 * id rather than writing a duplicate, so the audit trail stays one-per-trade.
 */
export const record = mutation({
  args: {
    trade_id: v.id("trades"),
    cycle_id: v.string(),
    timestamp_ms: v.number(),
    signals_snapshot: v.string(),
    regime: v.string(),
    outcome_pnl_usd: v.number(),
    outcome_label: outcome,
    lesson: v.string(),
    vector_id: v.optional(v.string()),
    quality: v.optional(v.string()),
    source_cycle_id: v.optional(v.string()),
  },
  returns: v.id("reflections"),
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("reflections")
      .withIndex("by_trade", (q) => q.eq("trade_id", args.trade_id))
      .collect();
    const dup = existing.find((r) => r.cycle_id === args.cycle_id);
    if (dup) {
      await ctx.db.patch(dup._id, {
        lesson: args.lesson,
        vector_id: args.vector_id,
        quality: args.quality,
      });
      return dup._id;
    }
    return await ctx.db.insert("reflections", args);
  },
});

export const recent = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const rows = await ctx.db.query("reflections").order("desc").take(args.limit ?? 50);
    return rows;
  },
});

/** Dreamer calls this to mark a duplicate reflection as stale (soft-delete). */
export const softDelete = mutation({
  args: { id: v.id("reflections") },
  returns: v.null(),
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, { stale: true });
    return null;
  },
});

export const byOutcome = query({
  args: { outcome_label: outcome, limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("reflections")
      .withIndex("by_outcome", (q) => q.eq("outcome_label", args.outcome_label))
      .order("desc")
      .take(args.limit ?? 50);
  },
});

/** Winning trades for the Wins Feed panel. Optionally filter by mode. */
export const wins = query({
  args: {
    limit: v.optional(v.number()),
    mode: v.optional(v.string()),
  },
  returns: v.array(v.any()),
  handler: async (ctx, args) => {
    const rows = await ctx.db
      .query("reflections")
      .withIndex("by_outcome", (q) => q.eq("outcome_label", "win"))
      .order("desc")
      .take(args.limit ?? 20);
    return args.mode ? rows.filter((r) => r.mode === args.mode) : rows;
  },
});
