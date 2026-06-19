import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { AgentCard, AgentCardSkeleton, AGENT_DEFS } from "../components/AgentCard";
import { cn } from "@/lib/utils";

type Props = {
  onAgentClick: (name: string) => void;
  onAgentOpen?: (threadId: string) => void;
};

export function AgentsView({ onAgentClick, onAgentOpen }: Props) {
  const roster = useQuery(api.agentEvents.latestPerAgent);
  const spawnedAgents = useQuery(api.spawnedAgents.list) ?? [];
  const rosterMap = new Map(
    (roster ?? []).map((e: { agent: string; ts_ms: number; kind: string; headline: string }) =>
      [e.agent, { ts_ms: e.ts_ms, kind: e.kind, headline: e.headline }]
    )
  );

  return (
    <div className="max-w-[1180px] mx-auto">
      <div className="mb-6 flex items-end gap-4 justify-between">
        <div>
          <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
            <span className="h-[2px] w-4 bg-purple rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--purple)" }} />
            Neural Mesh
          </div>
          <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Agent Team</h1>
        </div>
        <p className="font-mono text-[11px] text-muted-fg/60 hidden sm:block pb-0.5">
          tap to interrogate via co-pilot
        </p>
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

      {/* Your Agents — user-spawned fleet */}
      <div className="mt-8">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-3 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
          Your Agents
        </div>

        {spawnedAgents.length === 0 ? (
          <div className="panel p-6 text-center">
            <p className="font-mono text-[13px] text-muted-fg mb-1">No agents yet.</p>
            <p className="font-mono text-[11px] text-muted-fg/60">
              Open the Co-Pilot and say what job you need done.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
            {spawnedAgents.map((agent) => {
              const timeAgo = agent.last_activity_ms
                ? Math.round((Date.now() - agent.last_activity_ms) / 60000)
                : null;
              return (
                <div
                  key={agent._id}
                  className="panel p-4 flex flex-col gap-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "w-2.5 h-2.5 rounded-full flex-shrink-0 mt-0.5",
                          agent.status === "active" ? "bg-green" : "bg-muted-fg/30"
                        )}
                        style={agent.status === "active" ? { boxShadow: "0 0 6px var(--green)" } : {}}
                      />
                      <span className="font-display text-[14px] font-bold text-text">{agent.name}</span>
                    </div>
                    <span className={cn(
                      "font-mono text-[10px] border rounded px-2 py-0.5 uppercase tracking-widest flex-shrink-0",
                      agent.status === "active"
                        ? "bg-green/12 text-green border-green/25"
                        : "bg-muted-fg/8 text-muted-fg border-muted-fg/20"
                    )}>
                      {agent.status}
                    </span>
                  </div>

                  <p className="font-mono text-[11px] text-muted-fg/80 leading-relaxed line-clamp-2">
                    {agent.task_summary}
                  </p>

                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] text-muted-fg/50">
                      {timeAgo != null ? `${timeAgo}m ago` : "just now"}
                    </span>
                    <button
                      onClick={() => onAgentOpen?.(agent.thread_id ?? "")}
                      className="font-mono text-[11px] text-purple hover:text-purple/80 transition-colors cursor-pointer flex items-center gap-1"
                    >
                      Open Chat →
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
