import { action, mutation, query } from "./_generated/server";
import { v } from "convex/values";

/**
 * Persist one message (user or assistant) to the co-pilot thread.
 * Called by the client when a question is sent and when the action returns.
 */
export const addMessage = mutation({
  args: {
    role: v.union(v.literal("user"), v.literal("assistant")),
    content: v.string(),
    sources_json: v.optional(v.string()),
  },
  returns: v.id("copilot_messages"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("copilot_messages", {
      role: args.role,
      content: args.content,
      sources_json: args.sources_json ?? "[]",
      ts_ms: Date.now(),
    });
  },
});

/** Read the full conversation thread, oldest first. */
export const messages = query({
  args: { limit: v.optional(v.number()) },
  returns: v.array(v.any()),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("copilot_messages")
      .withIndex("by_ts")
      .order("asc")
      .take(args.limit ?? 50);
  },
});

/**
 * Ask the co-pilot a question. Proxies to POST /copilot on the agent server.
 * Returns gracefully when the agent is offline (judges running paper-only).
 */
export const ask = action({
  args: { question: v.string() },
  returns: v.object({
    answer: v.string(),
    grounded: v.boolean(),
    sources: v.array(v.any()),
  }),
  handler: async (_ctx, { question }) => {
    const agentUrl = process.env.AGENT_URL ?? "http://localhost:8000";
    try {
      const res = await fetch(`${agentUrl}/copilot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
        signal: AbortSignal.timeout(20_000),
      });
      if (!res.ok) {
        return {
          answer: `Agent returned HTTP ${res.status}. Is the server running?`,
          grounded: false,
          sources: [],
        };
      }
      const data = (await res.json()) as {
        answer?: string;
        grounded?: boolean;
        sources?: unknown[];
      };
      return {
        answer: data.answer ?? "",
        grounded: Boolean(data.grounded),
        sources: Array.isArray(data.sources) ? data.sources : [],
      };
    } catch (e) {
      return {
        answer: `Co-pilot offline — start the agent server to enable live Q&A. (${e})`,
        grounded: false,
        sources: [],
      };
    }
  },
});
