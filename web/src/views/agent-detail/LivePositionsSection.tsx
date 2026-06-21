import type { DetailAgent } from "./types";

export function LivePositionsSection({ agent }: { agent: DetailAgent }) {
  return <div className="panel p-6 font-mono text-[12px] text-muted-fg">Live Positions — {agent.name}</div>;
}
