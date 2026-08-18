export type Severity = "info" | "trade" | "risk" | "critical";

const RISK_AGENTS = new Set(["RiskGuard", "Risk Officer", "Autopilot"]);

/** Single source of truth for how an agent_events row maps to a UI severity tier. */
export function eventSeverity(e: {
  agent: string;
  kind: string;
  headline: string;
}): Severity {
  const h = e.headline.toLowerCase();
  if (h.includes("floor hit") || h.includes("kill switch") || h.includes("halt")) {
    return "critical";
  }
  // Failures must never fall through to the green "trade" tier below - an
  // errored action (e.g. "TWAK call failed") is a warning, not a success.
  if (
    h.includes("fail") || h.includes("error") ||
    h.includes("reverted") || h.includes("rejected")
  ) {
    return "risk";
  }
  if (h.includes("stop") || h.includes("circuit") || RISK_AGENTS.has(e.agent)) {
    return "risk";
  }
  if (e.kind === "action" || h.includes("filled") || h.includes("trade")) {
    return "trade";
  }
  return "info";
}

export const SEVERITY_LABEL: Record<Severity, string> = {
  info: "Info",
  trade: "Trade",
  risk: "Risk",
  critical: "Critical",
};
