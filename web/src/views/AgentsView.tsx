import { useQuery } from "convex/react";
import { useState } from "react";
import { api } from "../../../convex/_generated/api";
import { cn } from "@/lib/utils";
import { AgentDetailView } from "./agent-detail/AgentDetailView";
import type { DetailAgent } from "./agent-detail/types";
import type { Id } from "../../../convex/_generated/dataModel";

type ToolCall = { tool: string; args?: string };

type Props = {
  onAgentOpen?: (threadId: string) => void;   // opens co-pilot drawer on a thread
  onNewAgent?: () => void;                     // opens chat-first create
};

const PRIMARY: DetailAgent = {
  kind: "primary",
  name: "Alien-Trade",
  status: "active",
  goal: "Autonomous BSC spot trader — contrarian, drawdown-first.",
};

export function AgentsView({ onAgentOpen, onNewAgent }: Props) {
  const spawnedAgents = useQuery(api.spawnedAgents.list) ?? [];
  const latestRuns = useQuery(api.agentRuns.latestAllAgents) ?? [];
  const scorecard = useQuery(api.scorecard.get);
  const config = useQuery(api.config.get);
  const [selected, setSelected] = useState<DetailAgent | null>(null);

  const latestRunMap = new Map(
    latestRuns.map((r: { agent_id: string; tool_calls: ToolCall[] }) => [r.agent_id, r]),
  );

  if (selected) {
    return (
      <AgentDetailView
        agent={selected}
        onBack={() => setSelected(null)}
        onOpenChat={() => onAgentOpen?.(selected.thread_id ?? "")}
      />
    );
  }

  const primary: DetailAgent = {
    ...PRIMARY,
    status: config?.halted ? "idle" : "active",
    mode: config?.trading_mode,
  };
  const pnl = scorecard?.net_pnl_usd ?? null;

  return (
    <div className="max-w-[1180px] mx-auto">
      <div className="mb-6">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
          Agents
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Your Agents</h1>
      </div>

      <div className="flex items-center justify-end mb-3">
        <button
          onClick={() => onNewAgent?.()}
          className="font-mono text-[10px] border rounded px-2 py-0.5 uppercase tracking-widest transition-colors text-muted-fg border-muted-fg/20 hover:border-muted-fg/40"
        >+ New</button>
      </div>

      <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        {/* Pinned primary card */}
        <button
          onClick={() => setSelected(primary)}
          className="panel p-4 flex flex-col gap-3 text-left border border-green/25 hover:border-green/50 transition-colors"
          style={{ boxShadow: "0 0 20px rgba(var(--green-rgb,52,211,153),0.06)" }}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0 mt-0.5 bg-green" style={{ boxShadow: "0 0 6px var(--green)" }} />
              <span className="font-display text-[14px] font-bold text-text">Alien-Trade</span>
            </div>
            <span className="font-mono text-[9px] text-green border border-green/30 bg-green/10 rounded px-1.5 py-0.5 uppercase tracking-widest flex-shrink-0">Live trader</span>
          </div>
          <p className="font-mono text-[11px] text-muted-fg/80 leading-relaxed">{PRIMARY.goal}</p>
          <div className="flex items-center justify-between border-t border-border/30 pt-2">
            <span className="font-mono text-[10px] text-muted-fg/50 uppercase tracking-widest">Net PnL</span>
            <span className={cn("font-mono text-[13px] font-bold",
              pnl == null ? "text-muted-fg" : pnl >= 0 ? "text-green" : "text-red")}>
              {pnl == null ? "—" : `${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}`}
            </span>
          </div>
        </button>

        {/* Spawned agent cards */}
        {spawnedAgents.map((agent) => {
          const run = latestRunMap.get(agent._id);
          const calls: ToolCall[] = run?.tool_calls ?? [];
          const detail: DetailAgent = {
            kind: "spawned",
            id: agent._id as Id<"spawned_agents">,
            name: agent.name,
            status: agent.status,
            mode: agent.mode,
            goal: agent.goal ?? agent.task_summary,
            thread_id: agent.thread_id ?? undefined,
            allowed_tools: agent.allowed_tools ?? [],
            trigger: agent.trigger ?? undefined,
          };
          return (
            <button
              key={agent._id}
              onClick={() => setSelected(detail)}
              className="panel p-4 flex flex-col gap-3 text-left hover:border-border/60 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className={cn("w-2.5 h-2.5 rounded-full flex-shrink-0 mt-0.5",
                    agent.status === "active" ? "bg-green" : "bg-muted-fg/30")}
                    style={agent.status === "active" ? { boxShadow: "0 0 6px var(--green)" } : {}} />
                  <span className="font-display text-[14px] font-bold text-text">{agent.name}</span>
                </div>
                <span className={cn("font-mono text-[10px] border rounded px-2 py-0.5 uppercase tracking-widest flex-shrink-0",
                  agent.status === "active" ? "bg-green/12 text-green border-green/25" : "bg-muted-fg/8 text-muted-fg border-muted-fg/20")}>
                  {agent.status}
                </span>
              </div>
              <p className="font-mono text-[11px] text-muted-fg/80 leading-relaxed line-clamp-2">{agent.task_summary}</p>
              {calls.length > 0 && (
                <div className="flex items-center gap-0.5 flex-wrap border-t border-border/30 pt-2">
                  <span className="font-mono text-[9px] text-muted-fg/50 uppercase tracking-widest mr-1">Chain</span>
                  {calls.map((tc, i) => (
                    <span key={i} className="font-mono text-[9px] rounded px-1.5 py-0.5 border bg-purple/10 text-purple border-purple/20">{tc.tool}</span>
                  ))}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
