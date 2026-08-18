import { mutation } from "./_generated/server";
import { v } from "convex/values";
import { assertControlToken } from "./control";

/** Token validation probe - throws if the token is wrong, returns true if correct. */
export const ping = mutation({
  args: { control_token: v.string() },
  handler: async (_ctx, args) => {
    assertControlToken(args.control_token);
    return true;
  },
});
