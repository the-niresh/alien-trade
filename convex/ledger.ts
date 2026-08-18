import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

/**
 * Append a ledger row after a trade closes. Cumulative figures are computed by
 * the agent from on-chain receipts (source of truth) and passed in here.
 */
export const append = mutation({
  args: {
    trade_id: v.id("trades"),
    realized_pnl_usd: v.number(),
    cumulative_pnl_usd: v.number(),
    cumulative_fees_usd: v.number(),
    cumulative_gas_usd: v.number(),
    peak_equity_usd: v.number(),
    current_drawdown_pct: v.number(),
    timestamp_ms: v.optional(v.number()),
  },
  returns: v.id("ledger"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("ledger", {
      trade_id: args.trade_id,
      timestamp_ms: args.timestamp_ms ?? Date.now(),
      realized_pnl_usd: args.realized_pnl_usd,
      cumulative_pnl_usd: args.cumulative_pnl_usd,
      cumulative_fees_usd: args.cumulative_fees_usd,
      cumulative_gas_usd: args.cumulative_gas_usd,
      peak_equity_usd: args.peak_equity_usd,
      current_drawdown_pct: args.current_drawdown_pct,
    });
  },
});

/** Latest ledger row - the dashboard's PnL + drawdown headline. */
export const latest = query({
  args: {},
  returns: v.union(
    v.null(),
    v.object({
      _id: v.id("ledger"),
      _creationTime: v.number(),
      trade_id: v.id("trades"),
      timestamp_ms: v.number(),
      realized_pnl_usd: v.number(),
      cumulative_pnl_usd: v.number(),
      cumulative_fees_usd: v.number(),
      cumulative_gas_usd: v.number(),
      peak_equity_usd: v.number(),
      current_drawdown_pct: v.number(),
    }),
  ),
  handler: async (ctx) => {
    const rows = await ctx.db
      .query("ledger")
      .withIndex("by_timestamp")
      .order("desc")
      .take(1);
    return rows[0] ?? null;
  },
});

export const history = query({
  args: { limit: v.optional(v.number()) },
  returns: v.array(
    v.object({
      _id: v.id("ledger"),
      _creationTime: v.number(),
      trade_id: v.id("trades"),
      timestamp_ms: v.number(),
      realized_pnl_usd: v.number(),
      cumulative_pnl_usd: v.number(),
      cumulative_fees_usd: v.number(),
      cumulative_gas_usd: v.number(),
      peak_equity_usd: v.number(),
      current_drawdown_pct: v.number(),
    }),
  ),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("ledger")
      .withIndex("by_timestamp")
      .order("desc")
      .take(args.limit ?? 200);
  },
});
