import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// Per-symbol singleton: the Researcher writes confidence; the Risk Officer reads.
// Upsert (patch-or-insert) keeps exactly one row per symbol.

export const get = query({
  args: { symbol: v.string() },
  returns: v.union(
    v.null(),
    v.object({
      _id: v.id("forecast_state"),
      _creationTime: v.number(),
      symbol: v.string(),
      confidence: v.number(),
      reason: v.string(),
      ttl_ms: v.number(),
      ts_ms: v.number(),
    }),
  ),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("forecast_state")
      .withIndex("by_symbol", (q) => q.eq("symbol", args.symbol))
      .unique();
  },
});

export const set = mutation({
  args: {
    symbol: v.string(),
    confidence: v.number(),
    reason: v.string(),
    ttl_ms: v.number(),
    ts_ms: v.number(),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    const row = await ctx.db
      .query("forecast_state")
      .withIndex("by_symbol", (q) => q.eq("symbol", args.symbol))
      .unique();
    if (row) {
      await ctx.db.patch(row._id, {
        confidence: args.confidence,
        reason: args.reason,
        ttl_ms: args.ttl_ms,
        ts_ms: args.ts_ms,
      });
    } else {
      await ctx.db.insert("forecast_state", args);
    }
    return null;
  },
});
