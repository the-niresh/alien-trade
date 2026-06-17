import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { AGENT_DEFS } from "./AgentCard";

export function AgentTicker() {
  const events = useQuery(api.agentEvents.recent, { limit: 20 }) ?? [];
  if (events.length === 0) return null;

  const items = events.map((e) => {
    const def = AGENT_DEFS.find((a) => a.name === e.agent);
    return { id: e._id, agent: e.agent, color: def?.color ?? "var(--muted)", headline: String(e.headline) };
  });
  const doubled = [...items, ...items];

  return (
    <div className="chrome h-[30px] border-t border-border flex items-center flex-shrink-0 z-10">
      {/* live tag */}
      <div className="flex items-center gap-1.5 px-3 h-full border-r border-border flex-shrink-0 bg-green/[0.04]">
        <span className="h-1.5 w-1.5 rounded-full bg-green animate-pulse" style={{ boxShadow: "0 0 8px var(--green)" }} />
        <span className="font-mono text-[9px] font-bold tracking-[0.18em] text-green uppercase">Feed</span>
      </div>
      <div className="flex-1 overflow-hidden">
      <div className="ticker-track px-4">
        {doubled.map((item, i) => (
          <span key={`${item.id}-${i}`} className="font-mono text-[11px] text-muted-fg flex items-center gap-2">
            <span className="font-bold tracking-wide" style={{ color: item.color }}>{item.agent}</span>
            <span className="text-border-hi">›</span>
            <span className="text-text/70">{item.headline}</span>
          </span>
        ))}
      </div>
      </div>
    </div>
  );
}
