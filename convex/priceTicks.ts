import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const append = mutation({
  args: {
    symbol: v.string(),
    price: v.float64(),
    timestamp_ms: v.optional(v.float64()),
  },
  returns: v.id("price_ticks"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("price_ticks", {
      symbol: args.symbol,
      price: args.price,
      timestamp_ms: args.timestamp_ms ?? Date.now(),
    });
  },
});

export const forSymbol = query({
  args: { symbol: v.string(), limit: v.optional(v.number()) },
  returns: v.array(v.object({
    _id: v.id("price_ticks"),
    _creationTime: v.number(),
    symbol: v.string(),
    price: v.float64(),
    timestamp_ms: v.float64(),
  })),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("price_ticks")
      .withIndex("by_symbol_ts", (q) => q.eq("symbol", args.symbol))
      .order("desc")
      .take(args.limit ?? 24);
  },
});
