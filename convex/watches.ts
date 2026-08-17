// Market/trade watches — CRUD + the agent's edge-trigger state write.
// create/cancel are operator actions (token-gated); active/list are read-only;
// setState is the agent loop persisting the armed/clear flag (ungated agent write,
// same as agentEvents:append). The deterministic predicate lives in agent/watches.py.
import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { assertControlToken } from "./control";

const KINDS = ["price", "regime", "drawdown", "equity"];
const NUMERIC_OPS = ["lt", "gt"];

export const active = query({
  args: {},
  handler: async (ctx) =>
    await ctx.db.query("watches").withIndex("by_status", (q) => q.eq("status", "active")).collect(),
});

export const list = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, a) =>
    await ctx.db.query("watches").order("desc").take(a.limit ?? 50),
});

export const create = mutation({
  args: {
    kind:          v.string(),
    target:        v.optional(v.string()),
    op:            v.optional(v.string()),
    threshold:     v.optional(v.number()),
    label:         v.optional(v.string()),
    control_token: v.optional(v.string()),
  },
  returns: v.id("watches"),
  handler: async (ctx, a) => {
    assertControlToken(a.control_token);
    const kind = a.kind.trim().toLowerCase();
    if (!KINDS.includes(kind)) throw new Error(`unknown watch kind: ${kind}`);

    let target = (a.target ?? "").trim();
    let op = (a.op ?? "").trim().toLowerCase();
    let threshold = a.threshold ?? 0;

    if (kind === "regime") {
      if (!target) throw new Error("regime watch needs a target regime");
      target = target.toUpperCase();
      op = "eq";
      threshold = 0;
    } else {
      if (!NUMERIC_OPS.includes(op)) throw new Error(`${kind} watch needs op lt|gt`);
      if (kind === "price") {
        if (!target) throw new Error("price watch needs a target symbol");
        target = target.toUpperCase();
      } else {
        target = "";
      }
      if (typeof threshold !== "number" || Number.isNaN(threshold)) {
        throw new Error("threshold must be a number");
      }
    }

    return await ctx.db.insert("watches", {
      kind, target, op, threshold,
      label: (a.label ?? "").trim() || undefined,
      status: "active",
      last_state: "clear",
      created_at_ms: Date.now(),
    });
  },
});

export const cancel = mutation({
  args: { id: v.id("watches"), control_token: v.optional(v.string()) },
  returns: v.null(),
  handler: async (ctx, a) => {
    assertControlToken(a.control_token);
    await ctx.db.patch(a.id, { status: "cancelled" });
    return null;
  },
});

// Agent loop: persist the edge-trigger arming flag after each evaluation.
export const setState = mutation({
  args: {
    id:            v.id("watches"),
    last_state:    v.string(),
    last_fired_ms: v.optional(v.number()),
  },
  returns: v.null(),
  handler: async (ctx, a) => {
    const patch: Record<string, unknown> = { last_state: a.last_state };
    if (a.last_fired_ms !== undefined) patch.last_fired_ms = a.last_fired_ms;
    await ctx.db.patch(a.id, patch);
    return null;
  },
});
