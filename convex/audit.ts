import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const severity = v.union(v.literal("info"), v.literal("warn"), v.literal("error"));

/**
 * Append-only audit log. Every agent action lands here so "if it's not in
 * Convex, it didn't happen" holds. payload is a JSON string blob.
 */
export const log = mutation({
  args: {
    event_type: v.string(),
    cycle_id: v.optional(v.string()),
    payload: v.string(),
    severity,
    timestamp_ms: v.optional(v.number()),
  },
  returns: v.id("audit"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("audit", {
      timestamp_ms: args.timestamp_ms ?? Date.now(),
      event_type: args.event_type,
      cycle_id: args.cycle_id,
      payload: args.payload,
      severity: args.severity,
    });
  },
});

/** Most recent audit rows for the dashboard / debugging. */
export const recent = query({
  args: { limit: v.optional(v.number()) },
  returns: v.array(
    v.object({
      _id: v.id("audit"),
      _creationTime: v.number(),
      timestamp_ms: v.number(),
      event_type: v.string(),
      cycle_id: v.optional(v.string()),
      payload: v.string(),
      severity,
    }),
  ),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("audit")
      .withIndex("by_timestamp")
      .order("desc")
      .take(args.limit ?? 50);
  },
});
