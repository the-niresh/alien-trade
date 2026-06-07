import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const KEY = "global";

/**
 * Upsert the live risk-state singleton each cycle. The dashboard reads this for
 * the real-time drawdown / exposure / circuit-breaker view.
 */
export const update = mutation({
  args: {
    daily_loss_usd: v.number(),
    open_exposure_usd: v.number(),
    current_drawdown_pct: v.number(),
    peak_equity_usd: v.number(),
    circuit_breaker_active: v.boolean(),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    const row = await ctx.db
      .query("risk_state")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
    const doc = { key: KEY, ...args, last_updated_ms: Date.now() };
    if (row) {
      await ctx.db.patch(row._id, doc);
    } else {
      await ctx.db.insert("risk_state", doc);
    }
    return null;
  },
});

export const get = query({
  args: {},
  returns: v.union(
    v.null(),
    v.object({
      _id: v.id("risk_state"),
      _creationTime: v.number(),
      key: v.string(),
      daily_loss_usd: v.number(),
      open_exposure_usd: v.number(),
      current_drawdown_pct: v.number(),
      peak_equity_usd: v.number(),
      circuit_breaker_active: v.boolean(),
      last_updated_ms: v.number(),
    }),
  ),
  handler: async (ctx) => {
    return await ctx.db
      .query("risk_state")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
  },
});
