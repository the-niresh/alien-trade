import { action, internalAction, mutation, internalMutation, internalQuery, query } from "./_generated/server";
import { internal } from "./_generated/api";
import { v } from "convex/values";
import { assertControlToken } from "./control";

/**
 * Persist one message (user or assistant) to the co-pilot thread.
 * Called by the client when a question is sent and when the action returns.
 */
export const addMessage = mutation({
  args: {
    control_token: v.optional(v.string()),
    role: v.union(v.literal("user"), v.literal("assistant")),
    content: v.string(),
    sources_json: v.optional(v.string()),
    thread_id: v.optional(v.id("copilot_threads")),
  },
  returns: v.id("copilot_messages"),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
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
  args: { control_token: v.optional(v.string()), title: v.string() },
  returns: v.id("copilot_threads"),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    const now = Date.now();
    return await ctx.db.insert("copilot_threads", {
      title: args.title,
      created_ms: now,
      last_active_ms: now,
    });
  },
});

/** Rename a thread. */
export const renameThread = mutation({
  args: {
    control_token: v.optional(v.string()),
    id: v.id("copilot_threads"),
    title: v.string(),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    await ctx.db.patch(args.id, { title: args.title, last_active_ms: Date.now() });
    return null;
  },
});

/** Delete a thread and all its messages. */
export const deleteThread = mutation({
  args: {
    control_token: v.optional(v.string()),
    id: v.id("copilot_threads"),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    // Delete all messages belonging to this thread first
    const msgs = await ctx.db
      .query("copilot_messages")
      .withIndex("by_thread", (q) => q.eq("thread_id", args.id))
      .collect();
    for (const msg of msgs) {
      await ctx.db.delete(msg._id);
    }
    await ctx.db.delete(args.id);
    return null;
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
  args: { control_token: v.optional(v.string()), thread_id: v.optional(v.id("copilot_threads")) },
  returns: v.id("copilot_messages"),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
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
  args: { control_token: v.optional(v.string()), id: v.id("copilot_messages"), chunk: v.string() },
  returns: v.null(),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
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
    control_token: v.optional(v.string()),
    id:           v.id("copilot_messages"),
    content:      v.string(),
    sources_json: v.optional(v.string()),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
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
  args: { question: v.string(), control_token: v.optional(v.string()) },
  returns: v.object({
    answer: v.string(),
    grounded: v.boolean(),
    sources: v.array(v.any()),
    action: v.optional(v.any()),
  }),
  handler: async (_ctx, args) => {
    assertControlToken(args.control_token);
    const { question } = args;
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
          action: null,
        };
      }
      const data = (await res.json()) as {
        answer?: string;
        grounded?: boolean;
        sources?: unknown[];
        action?: Record<string, unknown> | null;
      };
      return {
        answer: data.answer ?? "",
        grounded: Boolean(data.grounded),
        sources: Array.isArray(data.sources) ? data.sources : [],
        action: data.action ?? null,
      };
    } catch (e) {
      return {
        answer: `Co-pilot offline — start the agent server to enable live Q&A. (${e})`,
        grounded: false,
        sources: [],
        action: null,
      };
    }
  },
});

/** Fix messages stuck as is_streaming=true with no content (action timed out). */
export const cleanupStuck = mutation({
  args: { control_token: v.optional(v.string()) },
  returns: v.number(),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    const stuck = await ctx.db
      .query("copilot_messages")
      .withIndex("by_ts")
      .filter((q) => q.eq(q.field("is_streaming"), true))
      .collect();
    let count = 0;
    for (const m of stuck) {
      if (!m.content && !m.partial_content) {
        await ctx.db.patch(m._id, { content: "_[response lost — co-pilot timed out]_", is_streaming: false, partial_content: undefined });
        count++;
      }
    }
    return count;
  },
});

// ── Internal helpers (called only from askStreaming action) ──────────────────

export const renameThreadInternal = internalMutation({
  args: { id: v.id("copilot_threads"), title: v.string() },
  returns: v.null(),
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, { title: args.title, last_active_ms: Date.now() });
    return null;
  },
});

export const updatePartialInternal = internalMutation({
  args: { id: v.id("copilot_messages"), chunk: v.string() },
  returns: v.null(),
  handler: async (ctx, args) => {
    const msg = await ctx.db.get(args.id);
    if (!msg) return null;
    await ctx.db.patch(args.id, { partial_content: (msg.partial_content ?? "") + args.chunk });
    return null;
  },
});

export const finaliseStreamInternal = internalMutation({
  args: { id: v.id("copilot_messages"), content: v.string() },
  returns: v.null(),
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, { content: args.content, partial_content: undefined, is_streaming: false, sources_json: "[]" });
    return null;
  },
});

export const getLiveState = internalQuery({
  args: {},
  returns: v.any(),
  handler: async (ctx) => {
    const cfg = await ctx.db.query("config").withIndex("by_key", (q) => q.eq("key", "global")).unique();
    const rs  = await ctx.db.query("risk_state").withIndex("by_key", (q) => q.eq("key", "global")).unique();
    const led = await ctx.db.query("ledger").withIndex("by_timestamp").order("desc").first();
    const pos = await ctx.db.query("positions").collect();
    const wal = await ctx.db.query("wallet_state").order("desc").first();
    return { cfg, rs, led, pos, wal };
  },
});

// askStreaming lives in convex/copilotNode.ts ("use node" — needed for HTTPS to api.anthropic.com)
