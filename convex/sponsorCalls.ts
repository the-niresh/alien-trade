import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { assertControlToken } from "./control";

const SPONSOR = v.union(v.literal("CMC"), v.literal("TWAK"), v.literal("BNB_SDK"));

export const append = mutation({
  args: {
    sponsor:    SPONSOR,
    kind:       v.string(),
    endpoint:   v.string(),
    status:     v.union(v.literal("ok"), v.literal("error")),
    latency_ms: v.number(),
    cost_usd:   v.optional(v.number()),
    tx_hash:    v.optional(v.string()),
    cycle_id:   v.optional(v.string()),
    detail:     v.string(),
    ts_ms:      v.number(),
    control_token: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    const { control_token: _ct, ...fields } = args;
    void _ct;
    const id = await ctx.db.insert("sponsor_calls", fields);

    // Fan-out notable events (swaps, payments, errors) to agent_events feed
    const notable =
      fields.kind === "swap" ||
      fields.kind === "payment" ||
      (fields.cost_usd != null && fields.cost_usd > 0) ||
      fields.status === "error";
    if (notable) {
      let headline = "";
      if (fields.status === "error") {
        headline = `${fields.sponsor} call failed — ${fields.endpoint}`;
      } else if (fields.kind === "swap") {
        headline = `TWAK swap executed — ${fields.endpoint}`;
      } else if (fields.kind === "payment") {
        headline = `CMC x402 payment $${(fields.cost_usd ?? 0).toFixed(4)} — ${fields.endpoint}`;
      } else {
        headline = `${fields.sponsor} x402 $${(fields.cost_usd ?? 0).toFixed(4)} — ${fields.endpoint}`;
      }
      await ctx.db.insert("agent_events", {
        ts_ms:   fields.ts_ms,
        agent:   fields.sponsor,
        kind:    "action",
        headline,
        detail:  fields.detail,
        refs:    fields.tx_hash ? [fields.tx_hash] : [],
      });
    }

    // Retention: prune rows beyond 500
    const rows = await ctx.db.query("sponsor_calls").withIndex("by_ts").order("asc").take(501);
    if (rows.length === 501) {
      await ctx.db.delete(rows[0]._id);
    }

    return id;
  },
});

export const recent = query({
  args: { limit: v.optional(v.number()) },
  returns: v.array(v.any()),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("sponsor_calls")
      .withIndex("by_ts")
      .order("desc")
      .take(args.limit ?? 50);
  },
});

export const summary = query({
  args: {},
  returns: v.array(v.any()),
  handler: async (ctx) => {
    const rows = await ctx.db
      .query("sponsor_calls")
      .withIndex("by_ts")
      .order("desc")
      .take(500);
    const sponsors = ["CMC", "TWAK", "BNB_SDK"] as const;
    return sponsors.map((s) => {
      const mine = rows.filter((r) => r.sponsor === s);
      return {
        sponsor:        s,
        calls:          mine.length,
        errors:         mine.filter((r) => r.status === "error").length,
        cost_usd_total: mine.reduce((acc, r) => acc + (r.cost_usd ?? 0), 0),
        last_ts:        mine[0]?.ts_ms ?? null,
      };
    });
  },
});
