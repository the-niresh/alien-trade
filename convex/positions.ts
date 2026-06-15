import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

/** Upsert the position for one symbol. Called by the agent each cycle. */
export const upsert = mutation({
  args: {
    symbol: v.string(),
    quantity: v.number(),
    avg_entry_price: v.number(),
    current_price: v.number(),
    current_value_usd: v.number(),
    unrealized_pnl_usd: v.number(),
    mode: v.string(),
    updated_ms: v.optional(v.number()),
  },
  returns: v.id("positions"),
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("positions")
      .withIndex("by_symbol", (q) => q.eq("symbol", args.symbol))
      .first();

    const row = {
      symbol: args.symbol,
      quantity: args.quantity,
      avg_entry_price: args.avg_entry_price,
      current_price: args.current_price,
      current_value_usd: args.current_value_usd,
      unrealized_pnl_usd: args.unrealized_pnl_usd,
      mode: args.mode,
      updated_ms: args.updated_ms ?? Date.now(),
    };

    if (existing) {
      await ctx.db.patch(existing._id, row);
      return existing._id;
    }
    return await ctx.db.insert("positions", row);
  },
});

/** Return all current positions (excludes flat ones with quantity == 0). */
export const open = query({
  args: {},
  returns: v.array(
    v.object({
      _id: v.id("positions"),
      _creationTime: v.number(),
      symbol: v.string(),
      quantity: v.number(),
      avg_entry_price: v.number(),
      current_price: v.number(),
      current_value_usd: v.number(),
      unrealized_pnl_usd: v.number(),
      mode: v.string(),
      updated_ms: v.number(),
    }),
  ),
  handler: async (ctx) => {
    const all = await ctx.db.query("positions").collect();
    return all.filter((p) => p.quantity > 0);
  },
});

/** All positions including flat (for debugging). */
export const all = query({
  args: {},
  returns: v.array(v.any()),
  handler: async (ctx) => {
    return await ctx.db.query("positions").collect();
  },
});
