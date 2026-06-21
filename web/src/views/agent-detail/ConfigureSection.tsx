import type { DetailAgent } from "./types";

export function ConfigureSection({ agent }: { agent: DetailAgent }) {
  return <div className="panel p-6 font-mono text-[12px] text-muted-fg">Configure — {agent.name}</div>;
}
