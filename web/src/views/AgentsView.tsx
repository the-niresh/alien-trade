import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { AgentCard, AGENT_DEFS } from "../components/AgentCard";

type Props = { onAgentClick: (name: string) => void };

export function AgentsView({ onAgentClick }: Props) {
  const roster = useQuery(api.agentEvents.latestPerAgent);
  const rosterMap = new Map(
    (roster ?? []).map((e: { agent: string; ts_ms: number; kind: string; headline: string }) =>
      [e.agent, { ts_ms: e.ts_ms, kind: e.kind, headline: e.headline }]
    )
  );

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 20, fontWeight: 700, marginBottom: 6 }}>
          Agent Team
        </div>
        <div style={{ fontSize: 13, color: "var(--muted)" }}>
          Click any agent to ask the co-pilot about them.
        </div>
      </div>
      <div className="agents-grid">
        {AGENT_DEFS.map((def) => (
          <AgentCard key={def.name} def={def}
            lastEvent={rosterMap.get(def.name)}
            onClick={() => onAgentClick(def.name)} />
        ))}
      </div>
    </div>
  );
}
