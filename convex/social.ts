import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// ── sentiment_state: per-symbol singleton written by the ingest agent ─────────

export const getSentiment = query({
  args: { symbol: v.string() },
  returns: v.union(
    v.null(),
    v.object({
      _id: v.id("sentiment_state"),
      _creationTime: v.number(),
      symbol: v.string(),
      score: v.number(),
      confidence: v.number(),
      n_posts: v.number(),
      ts_ms: v.number(),
      top_post_ids: v.array(v.string()),
    }),
  ),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("sentiment_state")
      .withIndex("by_symbol", (q) => q.eq("symbol", args.symbol))
      .unique();
  },
});

export const setSentiment = mutation({
  args: {
    symbol: v.string(),
    score: v.number(),
    confidence: v.number(),
    n_posts: v.number(),
    ts_ms: v.number(),
    top_post_ids: v.array(v.string()),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    const row = await ctx.db
      .query("sentiment_state")
      .withIndex("by_symbol", (q) => q.eq("symbol", args.symbol))
      .unique();
    if (row) {
      await ctx.db.patch(row._id, {
        score: args.score,
        confidence: args.confidence,
        n_posts: args.n_posts,
        ts_ms: args.ts_ms,
        top_post_ids: args.top_post_ids,
      });
    } else {
      await ctx.db.insert("sentiment_state", args);
    }
    return null;
  },
});

// ── social_posts: batch-write normalised posts (dedupe by post_id) ────────────

export const writePosts = mutation({
  args: {
    posts: v.array(v.object({
      post_id: v.string(),
      platform: v.string(),
      author: v.string(),
      text: v.string(),
      url: v.string(),
      ts_ms: v.number(),
      symbols: v.array(v.string()),
    })),
  },
  returns: v.number(),   // count inserted (skips dupes)
  handler: async (ctx, args) => {
    let inserted = 0;
    for (const p of args.posts) {
      const existing = await ctx.db
        .query("social_posts")
        .withIndex("by_post_id", (q) => q.eq("post_id", p.post_id))
        .unique();
      if (!existing) {
        await ctx.db.insert("social_posts", p);
        inserted++;
      }
    }
    return inserted;
  },
});

// ── social_sources: watchlist CRUD (user-writable) ────────────────────────────

export const getSources = query({
  args: {},
  returns: v.array(v.object({
    _id: v.id("social_sources"),
    _creationTime: v.number(),
    platform: v.union(
      v.literal("rss"), v.literal("farcaster"),
      v.literal("telegram"), v.literal("twitter"),
    ),
    handle: v.string(),
    label: v.string(),
    weight: v.number(),
    enabled: v.boolean(),
    added_ms: v.number(),
  })),
  handler: async (ctx) => {
    return await ctx.db.query("social_sources").collect();
  },
});

export const addSource = mutation({
  args: {
    platform: v.union(
      v.literal("rss"), v.literal("farcaster"),
      v.literal("telegram"), v.literal("twitter"),
    ),
    handle: v.string(),
    label: v.string(),
    weight: v.optional(v.number()),
    enabled: v.optional(v.boolean()),
  },
  returns: v.id("social_sources"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("social_sources", {
      platform: args.platform,
      handle: args.handle,
      label: args.label,
      weight: args.weight ?? 1.0,
      enabled: args.enabled ?? true,
      added_ms: Date.now(),
    });
  },
});

export const toggleSource = mutation({
  args: { id: v.id("social_sources"), enabled: v.boolean() },
  returns: v.null(),
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, { enabled: args.enabled });
    return null;
  },
});

export const removeSource = mutation({
  args: { id: v.id("social_sources") },
  returns: v.null(),
  handler: async (ctx, args) => {
    await ctx.db.delete(args.id);
    return null;
  },
});
