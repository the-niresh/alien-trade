import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const label = v.union(v.literal("good"), v.literal("bad"));

/**
 * Operator marks a setup good/bad from the cockpit (human-in-the-loop). The agent
 * consults these per setup_key before the next trade on the same setup
 * (core/risk/feedback.py). Append-only — every mark is kept for the audit trail.
 */
export const record = mutation({
  args: {
    cycle_id: v.string(),
    setup_key: v.string(),
    symbol: v.string(),
    label,
    note: v.optional(v.string()),
  },
  returns: v.id("trade_feedback"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("trade_feedback", { ...args, ts_ms: Date.now() });
  },
});

/** All labels for one setup_key (the agent reads this before trading the setup). */
export const bySetup = query({
  args: { setup_key: v.string() },
  returns: v.array(
    v.object({
      _id: v.id("trade_feedback"),
      _creationTime: v.number(),
      cycle_id: v.string(),
      setup_key: v.string(),
      symbol: v.string(),
      label,
      note: v.optional(v.string()),
      ts_ms: v.number(),
    }),
  ),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("trade_feedback")
      .withIndex("by_setup", (q) => q.eq("setup_key", args.setup_key))
      .collect();
  },
});

/** Recent feedback (cockpit history + the win/loss annotation feed). */
export const recent = query({
  args: { limit: v.optional(v.number()) },
  returns: v.array(
    v.object({
      _id: v.id("trade_feedback"),
      _creationTime: v.number(),
      cycle_id: v.string(),
      setup_key: v.string(),
      symbol: v.string(),
      label,
      note: v.optional(v.string()),
      ts_ms: v.number(),
    }),
  ),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("trade_feedback")
      .withIndex("by_ts")
      .order("desc")
      .take(args.limit ?? 30);
  },
});
