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
    thread_id: v.optional(v.id("copilot_threads")),
  },
  returns: v.id("copilot_messages"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("copilot_messages", {
      role: args.role,
      content: args.content,
      sources_json: args.sources_json ?? "[]",
      ts_ms: Date.now(),
      thread_id: args.thread_id,
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

/** Create a new co-pilot thread. */
export const createThread = mutation({
  args: { title: v.string() },
  returns: v.id("copilot_threads"),
  handler: async (ctx, args) => {
    const now = Date.now();
    return await ctx.db.insert("copilot_threads", {
      title: args.title,
      created_ms: now,
      last_active_ms: now,
    });
  },
});

/** List all threads, most-recently-active first. */
export const threads = query({
  args: {},
  returns: v.array(v.any()),
  handler: async (ctx) => {
    return await ctx.db
      .query("copilot_threads")
      .withIndex("by_last_active")
      .order("desc")
      .take(20);
  },
});

/** Read messages for a specific thread. */
export const threadMessages = query({
  args: { thread_id: v.id("copilot_threads"), limit: v.optional(v.number()) },
  returns: v.array(v.any()),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("copilot_messages")
      .withIndex("by_thread", (q) => q.eq("thread_id", args.thread_id))
      .order("asc")
      .take(args.limit ?? 60);
  },
});

/** Write an assistant message row to start streaming. Returns the message id. */
export const startStreamingMessage = mutation({
  args: { thread_id: v.optional(v.id("copilot_threads")) },
  returns: v.id("copilot_messages"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("copilot_messages", {
      role: "assistant",
      content: "",
      sources_json: "[]",
      ts_ms: Date.now(),
      thread_id: args.thread_id,
      partial_content: "",
      is_streaming: true,
    });
  },
});

/** Append a token chunk to a streaming assistant message. */
export const updatePartial = mutation({
  args: { id: v.id("copilot_messages"), chunk: v.string() },
  returns: v.null(),
  handler: async (ctx, args) => {
    const msg = await ctx.db.get(args.id);
    if (!msg) return null;
    await ctx.db.patch(args.id, {
      partial_content: (msg.partial_content ?? "") + args.chunk,
    });
    return null;
  },
});

/** Finalise a streaming message — set full content and clear streaming flag. */
export const finaliseStream = mutation({
  args: {
    id:           v.id("copilot_messages"),
    content:      v.string(),
    sources_json: v.optional(v.string()),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, {
      content:         args.content,
      partial_content: undefined,
      is_streaming:    false,
      sources_json:    args.sources_json ?? "[]",
    });
    return null;
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
