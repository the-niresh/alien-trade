import type { DetailAgent } from "./types";

export function DashboardSection({ agent }: { agent: DetailAgent }) {
  return <div className="panel p-6 font-mono text-[12px] text-muted-fg">Dashboard — {agent.name}</div>;
}
