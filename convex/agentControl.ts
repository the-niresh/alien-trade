import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { assertControlToken } from "./control";

const KEY = "global";

// The single user-writable control doc (§7). The PWA is the only writer; the
// supervisor + DecisionLoop are reactive readers. `trading_halted` mirrors
// config.halted (the Tier-0 kill); the other flags only quiet the Tier-1 team.
export const get = query({
  args: {},
  returns: v.union(
    v.null(),
    v.object({
      _id: v.id("agent_control"),
      _creationTime: v.number(),
      key: v.string(),
      agents_paused: v.boolean(),
      paused_agents: v.array(v.string()),
      trading_halted: v.boolean(),
      stop_response_id: v.optional(v.string()),
      updated_by: v.string(),
      ts_ms: v.number(),
    }),
  ),
  handler: async (ctx) => {
    return await ctx.db
      .query("agent_control")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
  },
});

export const set = mutation({
  args: {
    agents_paused: v.optional(v.boolean()),
    paused_agents: v.optional(v.array(v.string())),
    trading_halted: v.optional(v.boolean()),
    stop_response_id: v.optional(v.string()),
    updated_by: v.optional(v.string()),
    control_token: v.optional(v.string()),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    const row = await ctx.db
      .query("agent_control")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
    const doc = {
      key: KEY,
      agents_paused: args.agents_paused ?? row?.agents_paused ?? false,
      paused_agents: args.paused_agents ?? row?.paused_agents ?? [],
      trading_halted: args.trading_halted ?? row?.trading_halted ?? false,
      stop_response_id: args.stop_response_id ?? row?.stop_response_id,
      updated_by: args.updated_by ?? "user",
      ts_ms: Date.now(),
    };
    if (row) {
      await ctx.db.patch(row._id, doc);
    } else {
      await ctx.db.insert("agent_control", doc);
    }
    return null;
  },
});
