import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const record = mutation({
  args: {
    cycle_id: v.string(),
    symbol: v.string(),
    forecast_confidence: v.number(),
    regime: v.string(),
    realized_pnl: v.number(),
    ts_ms: v.number(),
  },
  returns: v.id("forecast_calibration"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("forecast_calibration", args);
  },
});

export const recent = query({
  args: { symbol: v.optional(v.string()), limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    let q = ctx.db.query("forecast_calibration");
    if (args.symbol) {
      return await q
        .withIndex("by_symbol", (i) => i.eq("symbol", args.symbol!))
        .order("desc")
        .take(args.limit ?? 200);
    }
    return await q.order("desc").take(args.limit ?? 200);
  },
});

/** Win-rate by confidence bucket: high (≥0.8), med (0.6–0.8), low (<0.6). */
export const getSummary = query({
  args: { symbol: v.optional(v.string()) },
  handler: async (ctx, args) => {
    const rows = await ctx.db
      .query("forecast_calibration")
      .order("desc")
      .take(500);
    const filtered = args.symbol ? rows.filter((r) => r.symbol === args.symbol) : rows;

    const buckets: Record<string, { wins: number; total: number }> = {
      high: { wins: 0, total: 0 },
      med: { wins: 0, total: 0 },
      low: { wins: 0, total: 0 },
    };
    for (const row of filtered) {
      const b = row.forecast_confidence >= 0.8 ? "high"
              : row.forecast_confidence >= 0.6 ? "med" : "low";
      buckets[b].total++;
      if (row.realized_pnl > 0) buckets[b].wins++;
    }
    return Object.fromEntries(
      Object.entries(buckets).map(([k, v]) => [
        k,
        { win_rate: v.total > 0 ? v.wins / v.total : null, n: v.total },
      ]),
    );
  },
});
