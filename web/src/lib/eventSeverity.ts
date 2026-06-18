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
