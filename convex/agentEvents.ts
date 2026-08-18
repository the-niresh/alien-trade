import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { assertControlToken } from "./control";

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
    control_token: v.optional(v.string()),
  },
  returns: v.id("agent_events"),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    const { control_token: _ct, ...fields } = args;
    void _ct;
    return await ctx.db.insert("agent_events", fields);
  },
});

/**
 * Latest event per agent - drives the animated agent roster in the glass cockpit.
 * Scans the last 200 events and returns one row per unique agent name.
 */
export const latestPerAgent = query({
  args: {},
  returns: v.array(v.any()),
  handler: async (ctx) => {
    const events = await ctx.db
      .query("agent_events")
      .withIndex("by_ts")
      .order("desc")
      .take(200);
    const seen = new Set<string>();
    const result: (typeof events)[number][] = [];
    for (const e of events) {
      if (!seen.has(e.agent)) {
        seen.add(e.agent);
        result.push(e);
      }
    }
    return result;
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
