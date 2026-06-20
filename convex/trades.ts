import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { assertControlToken } from "./control";

const mode = v.union(
  v.literal("testnet"),
  v.literal("paper"),
  v.literal("mainnet"),
);

/**
 * Record an executed (or paper-simulated) trade. Returns the trade id so the
 * caller can link a decision / ledger / reflection row to it.
 */
export const record = mutation({
  args: {
    symbol: v.string(),
    side: v.union(v.literal("buy"), v.literal("sell")),
    size_usd: v.number(),
    fill_price: v.number(),
    fee_usd: v.number(),
    gas_usd: v.number(),
    slippage_usd: v.number(),
    tx_hash: v.optional(v.string()),
    mode,
    timestamp_ms: v.optional(v.number()),
    control_token: v.optional(v.string()),
  },
  returns: v.id("trades"),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    return await ctx.db.insert("trades", {
      symbol: args.symbol,
      side: args.side,
      size_usd: args.size_usd,
      fill_price: args.fill_price,
      fee_usd: args.fee_usd,
      gas_usd: args.gas_usd,
      slippage_usd: args.slippage_usd,
      tx_hash: args.tx_hash,
      mode: args.mode,
      timestamp_ms: args.timestamp_ms ?? Date.now(),
    });
  },
});

export const recent = query({
  args: { limit: v.optional(v.number()) },
  returns: v.array(
    v.object({
      _id: v.id("trades"),
      _creationTime: v.number(),
      symbol: v.string(),
      side: v.union(v.literal("buy"), v.literal("sell")),
      size_usd: v.number(),
      fill_price: v.number(),
      fee_usd: v.number(),
      gas_usd: v.number(),
      slippage_usd: v.number(),
      tx_hash: v.optional(v.string()),
      mode,
      timestamp_ms: v.number(),
    }),
  ),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("trades")
      .withIndex("by_timestamp")
      .order("desc")
      .take(args.limit ?? 50);
  },
});
