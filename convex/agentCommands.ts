import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { assertControlToken } from "./control";

export const enqueue = mutation({
  args: {
    control_token: v.string(),
    command_type:  v.string(),
    params:        v.string(),   // JSON
    queued_by:     v.optional(v.string()),
  },
  returns: v.id("agent_commands"),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    const now = Date.now();
    return await ctx.db.insert("agent_commands", {
      command_type:  args.command_type,
      params:        args.params,
      status:        "queued",
      queued_by:     args.queued_by ?? "user",
      queued_at_ms:  now,
      updated_at_ms: now,
    });
  },
});

export const list = query({
  args: { limit: v.optional(v.number()) },
  returns: v.array(v.any()),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("agent_commands")
      .withIndex("by_queued_at")
      .order("desc")
      .take(args.limit ?? 20);
  },
});

export const updateStatus = mutation({
  args: {
    id:            v.id("agent_commands"),
    status:        v.union(v.literal("running"), v.literal("done"), v.literal("failed")),
    result:        v.optional(v.string()),
    error:         v.optional(v.string()),
    audit_id:      v.optional(v.id("audit")),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, {
      status:        args.status,
      result:        args.result,
      error:         args.error,
      audit_id:      args.audit_id,
      updated_at_ms: Date.now(),
    });
    return null;
  },
});
