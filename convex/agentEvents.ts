import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const kind = v.union(
  v.literal("observation"), v.literal("analysis"), v.literal("verdict"),
  v.literal("action"), v.literal("handoff"), v.literal("control"),
);

// Append one trace row to the Agent Activity Channel (the "glass cockpit").
// Append-only; the supervisor + each agent write here, the PWA reads (read-only).
export const append = mutation({
  args: {
    cycle_id: v.optional(v.string()),
    ts_ms: v.number(),
    agent: v.string(),
    kind,
    headline: v.string(),
    detail: v.string(),               // JSON blob, like audit.payload
    refs: v.array(v.string()),
  },
  returns: v.id("agent_events"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("agent_events", args);
  },
});

// Newest-first slice for the channel view.
export const recent = query({
  args: { limit: v.optional(v.number()) },
  returns: v.array(v.any()),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("agent_events")
      .withIndex("by_ts")
      .order("desc")
      .take(args.limit ?? 50);
  },
});
