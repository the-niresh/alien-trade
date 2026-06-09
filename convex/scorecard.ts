import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const KEY = "global";

// The live scorecard singleton — the agent's GOAL made measurable. Written from
// core/scorecard.py `Scorecard.as_convex_row()` (sim and live share that module,
// locked decision #2), read by the glass cockpit's "objective" panel. Nullable
// lines are genuinely absent in sim — null is honest, never faked to 0.
const nullableNumber = v.union(v.number(), v.null());

const fields = {
  objective: v.number(),
  total_return: v.number(),
  net_pnl_usd: v.number(),
  max_drawdown: v.number(),
  max_drawdown_duration_days: nullableNumber,
  sortino: v.number(),
  sharpe: v.number(),
  calmar: v.number(),
  pct_positive_days: nullableNumber,
  daily_pnl_vol: nullableNumber,
  n_trades: v.number(),
  win_rate: v.number(),
  profit_factor: v.number(),
  expectancy_usd: v.number(),
  worst_trade_usd: v.number(),
  total_cost_usd: v.number(),
  cost_ratio: v.number(),
  turnover: v.number(),
  avg_exposure_pct: nullableNumber,
  peak_exposure_pct: nullableNumber,
  rule_adherence_clean: v.boolean(),
  rule_violations: v.number(),
  operational: v.string(),
  rule_adherence: v.string(),
};

/** Upsert the live scorecard each cycle / at window close. */
export const update = mutation({
  args: fields,
  returns: v.null(),
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("scorecard")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
    const doc = { key: KEY, ...args, updated_at_ms: Date.now() };
    if (existing) {
      await ctx.db.patch(existing._id, doc);
    } else {
      await ctx.db.insert("scorecard", doc);
    }
    return null;
  },
});

export const get = query({
  args: {},
  returns: v.union(
    v.null(),
    v.object({
      _id: v.id("scorecard"),
      _creationTime: v.number(),
      key: v.string(),
      ...fields,
      updated_at_ms: v.number(),
    }),
  ),
  handler: async (ctx) => {
    return await ctx.db
      .query("scorecard")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .unique();
  },
});
