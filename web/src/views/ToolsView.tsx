import { useQuery, useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { AgentCard, AgentCardSkeleton, AGENT_DEFS } from "../components/AgentCard";

type Props = {
  controlToken?: string;
};

export function ToolsView({ controlToken }: Props) {
  const roster = useQuery(api.agentEvents.latestPerAgent);
  const pending = useQuery(api.approvals.listPending) ?? [];
  const resolveApproval = useMutation(api.approvals.resolve);

  const rosterMap = new Map(
    (roster ?? []).map((e: { agent: string; ts_ms: number; kind: string; headline: string }) =>
      [e.agent, { ts_ms: e.ts_ms, kind: e.kind, headline: e.headline }]
    )
  );

  return (
    <div className="max-w-[1180px] mx-auto">
      <div className="mb-6">
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Tools</h1>
        <p className="font-mono text-[11px] text-muted-fg/50 mt-1">tap a card to see what it uses</p>
      </div>

      <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        {roster === undefined
          ? AGENT_DEFS.map((d) => <AgentCardSkeleton key={d.name} />)
          : AGENT_DEFS.map((def) => (
              <AgentCard
                key={def.name}
                def={def}
                lastEvent={rosterMap.get(def.name)}
              />
            ))}
      </div>

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
    </div>
  );
}
