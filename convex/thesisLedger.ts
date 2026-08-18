import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { assertControlToken } from "./control";

const thesisFields = {
  thesis_id: v.string(),
  claim: v.string(),
  source: v.string(),
  regime: v.string(),
  status: v.string(),
  oos_objective: v.union(v.number(), v.null()),
  deflated_sharpe: v.union(v.number(), v.null()),
  asset_results: v.string(),
  trial_n: v.number(),
  ts_ms: v.number(),
};

/** Record (or update) a thesis card. Token-guarded - only the agent/loop writes. */
export const record = mutation({
  args: { ...thesisFields, control_token: v.optional(v.string()) },
  returns: v.null(),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    const { control_token: _ct, ...row } = args;
    const existing = await ctx.db
      .query("thesis_ledger")
      .withIndex("by_ts")
      .filter((q) => q.eq(q.field("thesis_id"), row.thesis_id))
      .first();
    if (existing) {
      await ctx.db.patch(existing._id, row);
    } else {
      await ctx.db.insert("thesis_ledger", row);
    }
    return null;
  },
});

/** Most-recent thesis cards for the cockpit feed. Ungated read. */
export const recent = query({
  args: { limit: v.optional(v.number()) },
  returns: v.array(v.any()),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("thesis_ledger")
      .withIndex("by_ts")
      .order("desc")
      .take(args.limit ?? 20);
  },
});

/** Cards filtered by status (untested | validated | FALSIFIED). Ungated read. */
export const byStatus = query({
  args: { status: v.string(), limit: v.optional(v.number()) },
  returns: v.array(v.any()),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("thesis_ledger")
      .withIndex("by_status", (q) => q.eq("status", args.status))
      .order("desc")
      .take(args.limit ?? 50);
  },
});
