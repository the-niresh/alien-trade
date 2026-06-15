import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { AgentCard, AgentCardSkeleton, AGENT_DEFS } from "../components/AgentCard";

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
      <div className="mb-5">
        <h1 className="font-grotesk text-xl font-bold mb-1.5">Agent Team</h1>
        <p className="text-[13px] text-muted-fg">Click any agent to ask the co-pilot about them.</p>
      </div>
      <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        {roster === undefined
          ? AGENT_DEFS.map((d) => <AgentCardSkeleton key={d.name} />)
          : AGENT_DEFS.map((def) => (
              <AgentCard key={def.name} def={def}
                lastEvent={rosterMap.get(def.name)}
                onClick={() => onAgentClick(def.name)} />
            ))
        }
      </div>
    </div>
  );
}
