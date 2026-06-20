import { useQuery, useMutation, useConvex } from "convex/react";
import { useState } from "react";
import { api } from "../../../convex/_generated/api";
import { AgentCard, AgentCardSkeleton, AGENT_DEFS } from "../components/AgentCard";
import { cn } from "@/lib/utils";
import { enableAlerts } from "@/lib/push";

type ToolCall = { tool: string; args?: string; summary?: string; error?: string };

type Props = {
  onAgentClick: (name: string) => void;
  onAgentOpen?: (threadId: string) => void;
  controlToken?: string;
};

export function AgentsView({ onAgentClick, onAgentOpen, controlToken }: Props) {
  const roster = useQuery(api.agentEvents.latestPerAgent);
  const spawnedAgents = useQuery(api.spawnedAgents.list) ?? [];
  const pending = useQuery(api.approvals.listPending) ?? [];
  const latestRuns = useQuery(api.agentRuns.latestAllAgents) ?? [];
  const resolveApproval = useMutation(api.approvals.resolve);
  const convex = useConvex();
  const [alertsEnabled, setAlertsEnabled] = useState(false);
  const [expandedTrace, setExpandedTrace] = useState<string | null>(null);
  const rosterMap = new Map(
    (roster ?? []).map((e: { agent: string; ts_ms: number; kind: string; headline: string }) =>
      [e.agent, { ts_ms: e.ts_ms, kind: e.kind, headline: e.headline }]
    )
  );
  const latestRunMap = new Map(
    latestRuns.map((r: { agent_id: string; ok: boolean; summary: string; tool_calls: ToolCall[] }) =>
      [r.agent_id, r]
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

      {/* Pending Approvals */}
      {pending.length > 0 && (
        <div className="mt-6">
          <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-3 flex items-center gap-2">
            <span className="h-[2px] w-4 bg-yellow rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--yellow)" }} />
            Pending Approvals
          </div>
          <div className="flex flex-col gap-2">
            {pending.map((p) => {
              const cmd = (() => { try { return JSON.parse(p.payload); } catch { return {}; } })();
              return (
                <div key={p._id} className="panel p-3 flex items-center justify-between gap-3">
                  <span className="font-mono text-[11px] text-text truncate">
                    {cmd.command_type ?? "trade"} — {cmd.params?.to ?? ""}
                  </span>
                  <div className="flex gap-2 flex-shrink-0">
                    <button
                      onClick={() => controlToken && resolveApproval({ id: p._id, status: "approved", control_token: controlToken })}
                      className="font-mono text-[11px] bg-green/15 text-green border border-green/30 rounded px-3 py-1 hover:bg-green/25 transition-colors"
                    >Approve</button>
                    <button
                      onClick={() => controlToken && resolveApproval({ id: p._id, status: "rejected", control_token: controlToken })}
                      className="font-mono text-[11px] bg-red/15 text-red border border-red/30 rounded px-3 py-1 hover:bg-red/25 transition-colors"
                    >Reject</button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Your Agents — user-spawned fleet */}
      <div className="mt-8">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-3 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
            Your Agents
          </div>
          <button
            onClick={async () => { const ok = await enableAlerts(convex); if (ok) setAlertsEnabled(true); }}
            className={cn("font-mono text-[10px] border rounded px-2 py-0.5 uppercase tracking-widest transition-colors",
              alertsEnabled ? "bg-green/12 text-green border-green/25" : "text-muted-fg border-muted-fg/20 hover:border-muted-fg/40")}
          >{alertsEnabled ? "Alerts on" : "Enable alerts"}</button>
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

                  {/* Neural Mesh chain trace */}
                  {(() => {
                    const run = latestRunMap.get(agent._id);
                    const calls: ToolCall[] = run?.tool_calls ?? [];
                    if (calls.length === 0) return null;
                    const isExpanded = expandedTrace === agent._id;
                    return (
                      <div className="border-t border-border/30 pt-2">
                        <button
                          onClick={() => setExpandedTrace(isExpanded ? null : agent._id)}
                          className="flex items-center gap-1.5 w-full group"
                        >
                          <span className="font-mono text-[9px] text-muted-fg/50 uppercase tracking-widest">
                            Chain
                          </span>
                          <div className="flex items-center gap-0.5 flex-1 overflow-hidden">
                            {calls.map((tc, i) => (
                              <span key={i} className="flex items-center gap-0.5">
                                {i > 0 && <span className="text-muted-fg/30 text-[9px]">→</span>}
                                <span className={cn(
                                  "font-mono text-[9px] rounded px-1.5 py-0.5 border",
                                  tc.error
                                    ? "bg-red/10 text-red border-red/20"
                                    : "bg-purple/10 text-purple border-purple/20"
                                )}>
                                  {tc.tool}
                                </span>
                              </span>
                            ))}
                          </div>
                          <span className="font-mono text-[9px] text-muted-fg/40 group-hover:text-muted-fg/70 transition-colors flex-shrink-0">
                            {isExpanded ? "▲" : "▼"}
                          </span>
                        </button>
                        {isExpanded && (
                          <div className="mt-2 flex flex-col gap-1">
                            {calls.map((tc, i) => (
                              <div key={i} className="flex items-start gap-2">
                                <span className={cn(
                                  "font-mono text-[9px] rounded px-1.5 py-0.5 border flex-shrink-0 mt-0.5",
                                  tc.error
                                    ? "bg-red/10 text-red border-red/20"
                                    : "bg-purple/10 text-purple border-purple/20"
                                )}>
                                  {tc.tool}
                                </span>
                                <span className="font-mono text-[10px] text-muted-fg/70 leading-relaxed line-clamp-2">
                                  {tc.error ?? tc.summary ?? tc.args ?? ""}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })()}

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
