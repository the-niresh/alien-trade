import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

export const record = mutation({
  args: {
    agent_id:   v.id("spawned_agents"),
    started_ms: v.number(),
    ended_ms:   v.number(),
    ok:         v.boolean(),
    summary:    v.string(),
    tool_calls: v.array(v.object({ tool: v.string(), args: v.string() })),
  },
  handler: async (ctx, a) => {
    await ctx.db.patch(a.agent_id, { last_activity_ms: Date.now() });
    return await ctx.db.insert("agent_runs", a);
  },
});

export const recent = query({
  args: { agent_id: v.id("spawned_agents") },
  handler: async (ctx, a) =>
    await ctx.db.query("agent_runs").withIndex("by_agent", q => q.eq("agent_id", a.agent_id))
      .order("desc").take(20),
});

export const latestAllAgents = query({
  args: {},
  handler: async (ctx) => {
    // Scan the most recent runs and return one (the latest) per agent_id.
    const runs = await ctx.db.query("agent_runs").order("desc").take(200);
    const seen = new Set<string>();
    const result: typeof runs = [];
    for (const r of runs) {
      const key = r.agent_id as string;
      if (!seen.has(key)) { seen.add(key); result.push(r); }
    }
    return result;
  },
});
