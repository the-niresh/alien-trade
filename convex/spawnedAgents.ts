import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

export const list = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db
      .query("spawned_agents")
      .withIndex("by_created")
      .order("desc")
      .filter((q) => q.neq(q.field("status"), "archived"))
      .collect();
  },
});

export const create = mutation({
  args: {
    name:         v.string(),
    task_summary: v.string(),
    thread_id:    v.optional(v.id("copilot_threads")),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("spawned_agents", {
      name:             args.name,
      task_summary:     args.task_summary,
      thread_id:        args.thread_id,
      status:           "active",
      created_at:       Date.now(),
      last_activity_ms: Date.now(),
    });
  },
});

export const setStatus = mutation({
  args: {
    id:     v.id("spawned_agents"),
    status: v.union(v.literal("active"), v.literal("idle"), v.literal("archived")),
  },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, { status: args.status });
  },
});

export const updateActivity = mutation({
  args: { id: v.id("spawned_agents") },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, { last_activity_ms: Date.now() });
  },
});
