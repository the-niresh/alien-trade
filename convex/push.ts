import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

export const subscribe = mutation({
  args: { endpoint: v.string(), p256dh: v.string(), auth: v.string() },
  handler: async (ctx, a) => {
    const existing = await ctx.db.query("push_subscriptions")
      .withIndex("by_endpoint", q => q.eq("endpoint", a.endpoint)).unique();
    if (existing) return existing._id;
    return await ctx.db.insert("push_subscriptions", { ...a, created_ms: Date.now() });
  },
});

export const list = query({
  args: {},
  handler: async (ctx) => await ctx.db.query("push_subscriptions").collect(),
});

export const remove = mutation({
  args: { id: v.id("push_subscriptions") },
  handler: async (ctx, a) => { await ctx.db.delete(a.id); },
});
