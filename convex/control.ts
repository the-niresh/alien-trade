// Shared-secret gate for all state-changing control mutations.
// The secret lives in the Convex deployment env (CONTROL_TOKEN) AND in the operator's
// ~/.alien-trade/credentials.json. The agent and the paired cockpit send it; nobody else has it.
// Read-only queries are intentionally NOT gated (the cockpit shows state to anyone paired).
export function assertControlToken(provided: string | undefined): void {
  const expected = process.env.CONTROL_TOKEN;
  if (!expected) {
    // Fail-OPEN only when no token is configured yet (pre-onboarding dev), so we never
    // brick the agent's own control path. Onboarding sets CONTROL_TOKEN -> fail-closed.
    return;
  }
  if (!provided || provided !== expected) {
    throw new Error("unauthorized: invalid or missing control token");
  }
}
