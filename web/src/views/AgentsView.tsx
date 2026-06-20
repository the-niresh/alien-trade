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

const AVAILABLE_TOOLS = [
  { id: "get_price",         label: "Price Feed",    desc: "Live token price via CMC" },
  { id: "cmc_market_skill",  label: "Market Intel",  desc: "Regime + funding/OI + social" },
  { id: "get_agent_state",   label: "Agent State",   desc: "Portfolio + equity snapshot" },
  { id: "get_trending",      label: "Trending",      desc: "CMC trending tokens" },
  { id: "check_token_risk",  label: "Risk Check",    desc: "Token risk score via CMC" },
];

const TRIGGER_OPTIONS = [
  { value: "1h",  label: "Every hour" },
  { value: "4h",  label: "Every 4 hours" },
  { value: "24h", label: "Daily" },
];

type BuilderState = {
  name: string;
  goal: string;
  allowed_tools: string[];
  trigger_spec: string;
  mode: "paper" | "live";
};

const DEFAULT_BUILDER: BuilderState = {
  name: "",
  goal: "",
  allowed_tools: ["get_price", "cmc_market_skill"],
  trigger_spec: "4h",
  mode: "paper",
};

function AgentBuilderPanel({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (state: BuilderState) => Promise<void>;
}) {
  const [form, setForm] = useState<BuilderState>(DEFAULT_BUILDER);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function toggleTool(id: string) {
    setForm((f) => ({
      ...f,
      allowed_tools: f.allowed_tools.includes(id)
        ? f.allowed_tools.filter((t) => t !== id)
        : [...f.allowed_tools, id],
    }));
  }

  async function handleSubmit() {
    if (!form.name.trim()) { setError("Name is required"); return; }
    if (!form.goal.trim()) { setError("Goal is required"); return; }
    if (form.allowed_tools.length === 0) { setError("Pick at least one tool"); return; }
    setSaving(true);
    setError("");
    try {
      await onCreate(form);
      onClose();
    } catch (e) {
      setError(String(e));
      setSaving(false);
    }
  }

  return (
    <div className="panel p-5 flex flex-col gap-4 border border-purple/30" style={{ boxShadow: "0 0 20px rgba(var(--purple-rgb,168,85,247),0.08)" }}>
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase">New Agent</span>
        <button onClick={onClose} className="font-mono text-[11px] text-muted-fg/50 hover:text-muted-fg transition-colors">✕</button>
      </div>

      {/* Name */}
      <div className="flex flex-col gap-1.5">
        <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Name</label>
        <input
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          placeholder="CAKE-Watcher"
          className="font-mono text-[12px] bg-surface border border-border/40 rounded px-3 py-2 text-text placeholder:text-muted-fg/30 focus:outline-none focus:border-purple/50"
        />
      </div>

      {/* Goal */}
      <div className="flex flex-col gap-1.5">
        <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Goal</label>
        <textarea
          value={form.goal}
          onChange={(e) => setForm((f) => ({ ...f, goal: e.target.value }))}
          placeholder="Monitor CAKE. Notify me when funding rate flips negative."
          rows={2}
          className="font-mono text-[12px] bg-surface border border-border/40 rounded px-3 py-2 text-text placeholder:text-muted-fg/30 focus:outline-none focus:border-purple/50 resize-none"
        />
      </div>

      {/* Tools picker */}
      <div className="flex flex-col gap-2">
        <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Allowed Tools</label>
        <div className="grid grid-cols-1 gap-1.5">
          {AVAILABLE_TOOLS.map((t) => {
            const checked = form.allowed_tools.includes(t.id);
            return (
              <button
                key={t.id}
                onClick={() => toggleTool(t.id)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded border text-left transition-colors",
                  checked
                    ? "bg-purple/10 border-purple/30 text-purple"
                    : "bg-surface border-border/30 text-muted-fg hover:border-border/60"
                )}
              >
                <span className={cn(
                  "w-4 h-4 rounded flex-shrink-0 border flex items-center justify-center text-[10px] font-bold",
                  checked ? "bg-purple border-purple text-white" : "border-border/40"
                )}>
                  {checked ? "✓" : ""}
                </span>
                <div className="flex flex-col min-w-0">
                  <span className="font-mono text-[11px] font-semibold">{t.label}</span>
                  <span className="font-mono text-[10px] text-muted-fg/60">{t.desc}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Trigger */}
      <div className="flex gap-4">
        <div className="flex flex-col gap-1.5 flex-1">
          <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Run cadence</label>
          <select
            value={form.trigger_spec}
            onChange={(e) => setForm((f) => ({ ...f, trigger_spec: e.target.value }))}
            className="font-mono text-[12px] bg-surface border border-border/40 rounded px-3 py-2 text-text focus:outline-none focus:border-purple/50"
          >
            {TRIGGER_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Mode</label>
          <div className="flex gap-1 pt-0.5">
            {(["paper", "live"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setForm((f) => ({ ...f, mode: m }))}
                className={cn(
                  "font-mono text-[11px] border rounded px-3 py-2 uppercase tracking-widest transition-colors",
                  form.mode === m
                    ? m === "live"
                      ? "bg-green/15 text-green border-green/30"
                      : "bg-purple/15 text-purple border-purple/30"
                    : "text-muted-fg border-border/30 hover:border-border/60"
                )}
              >{m}</button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <p className="font-mono text-[11px] text-red">{error}</p>
      )}

      <button
        onClick={handleSubmit}
        disabled={saving}
        className="font-mono text-[12px] bg-purple/20 text-purple border border-purple/30 rounded px-4 py-2.5 hover:bg-purple/30 transition-colors disabled:opacity-50 uppercase tracking-widest"
      >
        {saving ? "Spawning…" : "Spawn Agent"}
      </button>
    </div>
  );
}

export function AgentsView({ onAgentClick, onAgentOpen, controlToken }: Props) {
  const roster = useQuery(api.agentEvents.latestPerAgent);
  const spawnedAgents = useQuery(api.spawnedAgents.list) ?? [];
  const pending = useQuery(api.approvals.listPending) ?? [];
  const latestRuns = useQuery(api.agentRuns.latestAllAgents) ?? [];
  const resolveApproval = useMutation(api.approvals.resolve);
  const createAgent = useMutation(api.spawnedAgents.create);
  const convex = useConvex();
  const [alertsEnabled, setAlertsEnabled] = useState(false);
  const [expandedTrace, setExpandedTrace] = useState<string | null>(null);
  const [showBuilder, setShowBuilder] = useState(false);

  async function handleCreateAgent(form: BuilderState) {
    await createAgent({
      name: form.name.trim(),
      goal: form.goal.trim(),
      allowed_tools: form.allowed_tools,
      trigger: { kind: "schedule", spec: form.trigger_spec },
      mode: form.mode,
    });
  }
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
          <div className="flex items-center gap-2">
            <button
              onClick={async () => { const ok = await enableAlerts(convex); if (ok) setAlertsEnabled(true); }}
              className={cn("font-mono text-[10px] border rounded px-2 py-0.5 uppercase tracking-widest transition-colors",
                alertsEnabled ? "bg-green/12 text-green border-green/25" : "text-muted-fg border-muted-fg/20 hover:border-muted-fg/40")}
            >{alertsEnabled ? "Alerts on" : "Enable alerts"}</button>
            <button
              onClick={() => setShowBuilder((v) => !v)}
              className={cn(
                "font-mono text-[10px] border rounded px-2 py-0.5 uppercase tracking-widest transition-colors",
                showBuilder
                  ? "bg-purple/15 text-purple border-purple/30"
                  : "text-muted-fg border-muted-fg/20 hover:border-muted-fg/40"
              )}
            >+ New</button>
          </div>
        </div>

        {showBuilder && (
          <div className="mb-4">
            <AgentBuilderPanel
              onClose={() => setShowBuilder(false)}
              onCreate={handleCreateAgent}
            />
          </div>
        )}

        {spawnedAgents.length === 0 && !showBuilder ? (
          <div className="panel p-6 text-center">
            <p className="font-mono text-[13px] text-muted-fg mb-1">No agents yet.</p>
            <p className="font-mono text-[11px] text-muted-fg/60">
              Tap <span className="text-purple">+ New</span> to build one, or open the Co-Pilot and describe the job.
            </p>
          </div>
        ) : spawnedAgents.length > 0 ? (
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
        ) : null}
      </div>
    </div>
  );
}
