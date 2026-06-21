import type { DetailAgent } from "./types";

export function ScanningSection({ agent }: { agent: DetailAgent }) {
  return <div className="panel p-6 font-mono text-[12px] text-muted-fg">Scanning — {agent.name}</div>;
}
