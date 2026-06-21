import type { DetailAgent } from "./types";

export function TradesSection({ agent }: { agent: DetailAgent }) {
  return <div className="panel p-6 font-mono text-[12px] text-muted-fg">Trades — {agent.name}</div>;
}
