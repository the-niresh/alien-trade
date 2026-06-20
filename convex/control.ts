// Shared-secret gate for all state-changing control mutations.
// The secret lives in the Convex deployment env (CONTROL_TOKEN) AND in the operator's
// ~/.alien-trade/credentials.json. The agent and the paired cockpit send it; nobody else has it.
// Read-only queries are intentionally NOT gated (the cockpit shows state to anyone paired).
export function assertControlToken(provided: string | undefined): void {
  const expected = process.env.CONTROL_TOKEN;
  // Fail CLOSED: if the deployment has no CONTROL_TOKEN configured, reject every
  // state-changing call rather than waving them through. A missing secret (rotation,
  // fresh redeploy, accidental dashboard deletion) must never silently disable the gate,
  // since Convex deployment URLs are publicly addressable. Onboarding sets CONTROL_TOKEN.
  if (!expected) {
    throw new Error("unauthorized: CONTROL_TOKEN not configured in deployment");
  }
  if (!provided || provided !== expected) {
    throw new Error("unauthorized: invalid or missing control token");
  }
}
