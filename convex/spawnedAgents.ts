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
    name:          v.string(),
    goal:          v.string(),
    allowed_tools: v.optional(v.array(v.string())),
    trigger:       v.optional(v.object({ kind: v.string(), spec: v.string() })),
    notify_policy: v.optional(v.object({ webpush: v.boolean(), severity_min: v.string() })),
    mode:          v.optional(v.union(v.literal("paper"), v.literal("live"))),
    thread_id:     v.optional(v.id("copilot_threads")),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("spawned_agents", {
      name:             args.name,
      task_summary:     args.goal,
      goal:             args.goal,
      allowed_tools:    args.allowed_tools ?? [],
      trigger:          args.trigger,
      notify_policy:    args.notify_policy ?? { webpush: true, severity_min: "info" },
      mode:             args.mode ?? "paper",
      thread_id:        args.thread_id,
      status:           "active",
      created_at:       Date.now(),
      last_activity_ms: Date.now(),
    });
  },
});

export const rename = mutation({
  args: { id: v.id("spawned_agents"), name: v.string() },
  handler: async (ctx, args) => { await ctx.db.patch(args.id, { name: args.name }); },
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

export const ensure = mutation({
  args: {
    name:          v.string(),
    goal:          v.string(),
    allowed_tools: v.optional(v.array(v.string())),
    trigger:       v.optional(v.object({ kind: v.string(), spec: v.string() })),
    mode:          v.optional(v.union(v.literal("paper"), v.literal("live"))),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db.query("spawned_agents")
      .filter((q) => q.eq(q.field("name"), args.name))
      .first();
    if (existing) return existing._id;
    return await ctx.db.insert("spawned_agents", {
      name:             args.name,
      task_summary:     args.goal,
      goal:             args.goal,
      allowed_tools:    args.allowed_tools ?? [],
      trigger:          args.trigger,
      notify_policy:    { webpush: true, severity_min: "info" },
      mode:             args.mode ?? "paper",
      status:           "active",
      created_at:       Date.now(),
      last_activity_ms: Date.now(),
    });
  },
});
