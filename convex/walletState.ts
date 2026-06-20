import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { assertControlToken } from "./control";

export const upsert = mutation({
  args: {
    address:   v.optional(v.string()),
    usdt:      v.number(),
    eth:       v.number(),
    bnb:       v.number(),
    bnb_usd:   v.number(),
    total_usd: v.number(),
    updated_ms: v.number(),
    control_token: v.optional(v.string()),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    const { control_token: _ct, ...fields } = args;
    void _ct;
    const existing = await ctx.db.query("wallet_state").first();
    if (existing) {
      await ctx.db.patch(existing._id, fields);
    } else {
      await ctx.db.insert("wallet_state", fields);
    }
    return null;
  },
});

export const get = query({
  args: {},
  returns: v.union(v.null(), v.object({
    _id: v.id("wallet_state"),
    _creationTime: v.number(),
    address:   v.optional(v.string()),
    usdt:      v.number(),
    eth:       v.number(),
    bnb:       v.number(),
    bnb_usd:   v.number(),
    total_usd: v.number(),
    updated_ms: v.number(),
  })),
  handler: async (ctx) => {
    return await ctx.db.query("wallet_state").first();
  },
});

/**
 * Returns the self-custody wallet address directly from the server env var.
 * Used by DepositView so it works immediately without waiting for an agent cycle.
 */
export const getAddress = query({
  args: {},
  returns: v.string(),
  handler: async (ctx) => {
    // First try the Convex row (populated by agent each cycle)
    const row = await ctx.db.query("wallet_state").first();
    if (row?.address) return row.address;
    // Fall back to env var set in Convex dashboard / deployment
    return process.env.WALLET_ADDRESS ?? "";
  },
});
