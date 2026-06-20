import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { assertControlToken } from "./control";

export const propose = mutation({
  args: { agent_id: v.id("spawned_agents"), payload: v.string() },
  handler: async (ctx, a) =>
    await ctx.db.insert("approval_requests", {
      agent_id: a.agent_id, kind: "trade", payload: a.payload,
      status: "pending", created_ms: Date.now(),
    }),
});

export const listPending = query({
  args: {},
  handler: async (ctx) =>
    await ctx.db.query("approval_requests").withIndex("by_status", q => q.eq("status", "pending"))
      .order("desc").collect(),
});

export const resolve = mutation({
  args: {
    id: v.id("approval_requests"),
    status: v.union(v.literal("approved"), v.literal("rejected")),
    control_token: v.string(),
  },
  handler: async (ctx, a) => {
    assertControlToken(a.control_token);
    const req = await ctx.db.get(a.id);
    if (!req || req.status !== "pending") throw new Error("approval not pending");
    await ctx.db.patch(a.id, { status: a.status, resolved_ms: Date.now() });
    if (a.status === "approved") {
      const { command_type, params } = JSON.parse(req.payload);
      await ctx.db.insert("agent_commands", {
        command_type, params: JSON.stringify(params), status: "queued",
        queued_by: `agent:${req.agent_id}`, queued_at_ms: Date.now(), updated_at_ms: Date.now(),
      });
    }
  },
});
