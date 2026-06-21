import type { Id } from "../../../../convex/_generated/dataModel";

export type AgentKind = "primary" | "spawned";

export type DetailAgent = {
  kind: AgentKind;
  id?: Id<"spawned_agents">;        // undefined for the primary trader
  name: string;
  status: string;
  mode?: string;
  goal?: string;
  thread_id?: string;
  allowed_tools?: string[];
  trigger?: { kind: string; spec: string };
};

export type DetailSection = "dashboard" | "trades" | "scanning" | "positions" | "configure";

export const SECTION_ORDER: DetailSection[] = [
  "dashboard", "trades", "scanning", "positions", "configure",
];

export function sectionLabel(s: DetailSection): string {
  switch (s) {
    case "dashboard": return "Dashboard";
    case "trades":    return "Trades";
    case "scanning":  return "Scanning";
    case "positions": return "Live Positions";
    case "configure": return "Configure";
  }
}
