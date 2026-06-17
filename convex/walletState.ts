import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const upsert = mutation({
  args: {
    usdt: v.number(),
    eth: v.number(),
    bnb: v.number(),
    bnb_usd: v.number(),
    total_usd: v.number(),
    updated_ms: v.number(),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    const existing = await ctx.db.query("wallet_state").first();
    if (existing) {
      await ctx.db.patch(existing._id, args);
    } else {
      await ctx.db.insert("wallet_state", args);
    }
    return null;
  },
});

export const get = query({
  args: {},
  returns: v.union(v.null(), v.object({
    _id: v.id("wallet_state"),
    _creationTime: v.number(),
    usdt: v.number(),
    eth: v.number(),
    bnb: v.number(),
    bnb_usd: v.number(),
    total_usd: v.number(),
    updated_ms: v.number(),
  })),
  handler: async (ctx) => {
    return await ctx.db.query("wallet_state").first();
  },
});
