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
    <div className="agent-ticker">
      <div className="ticker-track">
        {doubled.map((item, i) => (
          <span key={`${item.id}-${i}`} className="ticker-item">
            <span className="ticker-item__agent" style={{ color: item.color }}>{item.agent}</span>
            {item.headline}
          </span>
        ))}
      </div>
    </div>
  );
}
