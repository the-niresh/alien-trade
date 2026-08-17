import { useQuery } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { cn } from "@/lib/utils";
import { RealizedPnlChart } from "@/components/RealizedPnlChart";
import type { DetailAgent } from "./types";

function Stat({ label, value, tone }: { label: string; value: string; tone?: "green" | "red" | "muted" }) {
  return (
    <div className="panel p-3 flex flex-col gap-1">
      <span className="font-mono text-[9px] text-muted-fg/60 uppercase tracking-widest">{label}</span>
      <span className={cn("font-mono text-[16px] font-bold",
        tone === "green" ? "text-green" : tone === "red" ? "text-red" : "text-text")}>{value}</span>
    </div>
  );
}

function timeAgo(ms?: number): string {
  if (!ms) return "—";
  const s = Math.floor((Date.now() - ms) / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function DashboardSection({ agent }: { agent: DetailAgent }) {
  if (agent.kind === "primary") return <PrimaryDashboard />;
  return <SpawnedDashboard agent={agent} />;
}

/**
 * Trade lifecycle — the missing middle of the cycle: entry → live unrealized PnL +
 * the agent's *intended* exit → (realized lands on the chart below). When flat it
 * states the capital-preservation thesis explicitly: HOLD is a decision, not idle
 * time. Numbers are read straight from live state — nothing inflated.
 */
function TradeLifecycle() {
  const positions = useQuery(api.positions.open) ?? [];
  const config = useQuery(api.config.get);
  const falsified = useQuery(api.thesisLedger.byStatus, { status: "FALSIFIED" }) ?? [];
  const validated = useQuery(api.thesisLedger.byStatus, { status: "VALIDATED" }) ?? [];
  const ap = config?.autopilot;
  const tested = falsified.length + validated.length;

  const scienceStrip = tested > 0 ? (
    <div className="flex items-center gap-2 flex-wrap font-mono text-[10px] text-muted-fg/70">
      <span className="uppercase tracking-widest text-muted-fg/50">Science log</span>
      <span>{tested} tested</span><span className="text-muted-fg/30">·</span>
      <span className="text-red">{falsified.length} falsified</span><span className="text-muted-fg/30">·</span>
      <span className={validated.length > 0 ? "text-green" : ""}>{validated.length} validated</span>
    </div>
  ) : (
    <div className="font-mono text-[10px] text-muted-fg/60">
      Capital-preserving until an edge validates net-of-costs.
    </div>
  );

  if (positions.length === 0) {
    return (
      <div className="panel p-4 flex flex-col gap-2.5">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-yellow-400/70 flex-shrink-0" />
          <span className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Trade lifecycle — flat, capital preserved</span>
        </div>
        <p className="font-mono text-[12px] text-text leading-relaxed">
          Holding USDT. <span className="text-yellow-400">HOLD is a decision</span>, not idle time —
          trading without a validated, cost-net edge bleeds to fees and slippage. The agent waits for a
          setup that beats sitting in cash.
        </p>
        {scienceStrip}
      </div>
    );
  }

  return (
    <div className="panel p-4 flex flex-col gap-3">
      <span className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Trade lifecycle — open</span>
      <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
        {positions.map((p) => {
          const target = ap?.enabled ? (ap.profit_target_pct ?? 0) : 0;
          const trailing = ap?.enabled ? (ap.trailing_giveback_pct ?? 0) : 0;
          const lockPrice = target > 0 ? p.avg_entry_price * (1 + target) : null;
          const intent = lockPrice
            ? `holding · locks at +${(target * 100).toFixed(0)}% ($${lockPrice.toFixed(4)}) · trails ${(trailing * 100).toFixed(0)}% from peak`
            : "holding · deterministic risk-engine exit (no autopilot profit-lock set)";
          return (
            <div key={p._id} className="flex flex-col gap-1.5 border border-border/30 rounded p-3">
              <div className="flex items-center justify-between">
                <span className="font-display text-[14px] font-bold text-text">{p.symbol}</span>
                <span className={cn("font-mono text-[12px] font-bold", p.unrealized_pnl_usd >= 0 ? "text-green" : "text-red")}>
                  {p.unrealized_pnl_usd >= 0 ? "+" : ""}${p.unrealized_pnl_usd.toFixed(2)} <span className="text-muted-fg/50 font-normal">unrl.</span>
                </span>
              </div>
              <div className="font-mono text-[10px] text-muted-fg/70 flex justify-between">
                <span>entry ${p.avg_entry_price.toFixed(4)}</span>
                <span>now ${p.current_price.toFixed(4)}</span>
              </div>
              <div className="font-mono text-[10px] text-purple/80 leading-relaxed">→ {intent}</div>
            </div>
          );
        })}
      </div>
      <p className="font-mono text-[10px] text-muted-fg/50 leading-relaxed">
        Exits run automatically on the rules above. Manual realize / hold override plugs in here when the
        engine is live.
      </p>
      {scienceStrip}
    </div>
  );
}

function PrimaryDashboard() {
  const sc = useQuery(api.scorecard.get);
  const decision = useQuery(api.decisions.latest);
  const pnl = sc?.net_pnl_usd ?? null;
  const dd = sc?.max_drawdown ?? null;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-3 max-sm:grid-cols-2">
        <Stat label="Realized PnL" value={pnl == null ? "—" : `${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}`} tone={pnl == null ? "muted" : pnl >= 0 ? "green" : "red"} />
        <Stat label="Win Rate" value={sc?.win_rate == null ? "—" : `${(sc.win_rate * 100).toFixed(0)}%`} />
        <Stat label="Trades" value={sc?.n_trades?.toString() ?? "—"} />
        <Stat label="Max Drawdown" value={dd == null ? "—" : `${(dd * 100).toFixed(1)}%`} tone={dd ? "red" : "muted"} />
        <Stat label="Sortino" value={sc?.sortino?.toFixed(2) ?? "—"} />
        <Stat label="Profit Factor" value={sc?.profit_factor?.toFixed(2) ?? "—"} />
      </div>

      <TradeLifecycle />

      <div className="panel p-4">
        <div className="font-mono text-[10px] text-muted-fg uppercase tracking-widest mb-2">Performance — realized PnL</div>
        <RealizedPnlChart period="max" />
      </div>

      <div className="panel p-4">
        <div className="font-mono text-[10px] text-muted-fg uppercase tracking-widest mb-2">AI Insights</div>
        {decision ? (
          <div className="flex flex-col gap-1.5">
            <p className="font-mono text-[12px] text-text leading-relaxed">
              Regime <span className="text-purple">{decision.regime}</span> on {decision.symbol} ·
              verdict <span className={cn(decision.risk_verdict === "block" ? "text-red" : decision.risk_verdict === "reduce" ? "text-yellow-400" : "text-green")}>{decision.risk_verdict}</span>
            </p>
            {decision.risk_reason && <p className="font-mono text-[11px] text-muted-fg/80 leading-relaxed">{decision.risk_reason}</p>}
            <p className="font-mono text-[10px] text-muted-fg/50">target ${decision.target_position_usd.toFixed(0)} → final ${decision.final_size_usd.toFixed(0)}</p>
          </div>
        ) : (
          <p className="font-mono text-[11px] text-muted-fg/60">No decisions recorded yet.</p>
        )}
      </div>
    </div>
  );
}

function SpawnedDashboard({ agent }: { agent: DetailAgent }) {
  const runs = useQuery(api.agentRuns.recent, agent.id ? { agent_id: agent.id } : "skip") ?? [];
  const lastRun = runs[0];
  const okCount = runs.filter((r) => r.ok).length;
  const avgTools = runs.length ? (runs.reduce((s, r) => s + r.tool_calls.length, 0) / runs.length) : 0;
  const cadence = agent.trigger?.spec ?? "—";
  const trace: string[] = lastRun?.tool_calls?.map((t: { tool: string }) => t.tool) ?? [];

  // oldest → newest left-to-right for the run-history strip
  const history = [...runs].reverse();
  const maxTools = Math.max(1, ...history.map((r) => r.tool_calls.length));

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-4 gap-3 max-sm:grid-cols-2">
        <Stat label="Runs" value={runs.length.toString()} />
        <Stat label="OK / Total" value={`${okCount}/${runs.length}`} tone={runs.length > 0 && okCount === runs.length ? "green" : runs.length === 0 ? "muted" : "red"} />
        <Stat label="Avg Tools/Run" value={avgTools.toFixed(1)} />
        <Stat label="Last Run" value={timeAgo(lastRun?.ended_ms ?? lastRun?.started_ms)} tone="muted" />
      </div>

      <div className="panel p-4 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Run history</span>
          <span className="font-mono text-[9px] text-muted-fg/50 uppercase tracking-widest">cadence {cadence} · {agent.mode ?? "paper"}</span>
        </div>
        {history.length === 0 ? (
          <p className="font-mono text-[11px] text-muted-fg/50">No runs yet — first run fires on the next {cadence} cycle.</p>
        ) : (
          <div className="flex items-end gap-1 h-12">
            {history.map((r, i) => (
              <div
                key={i}
                title={`${r.ok ? "ok" : "failed"} · ${r.tool_calls.length} tools · ${timeAgo(r.ended_ms ?? r.started_ms)}`}
                className={cn("flex-1 min-w-[3px] rounded-sm", r.ok ? "bg-green/60" : "bg-red/60")}
                style={{ height: `${20 + (r.tool_calls.length / maxTools) * 80}%` }}
              />
            ))}
          </div>
        )}
      </div>

      <div className="panel p-4 flex flex-col gap-1.5">
        <div className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Mandate</div>
        <p className="font-mono text-[12px] text-text leading-relaxed">{agent.goal ?? "—"}</p>
      </div>

      <div className="panel p-4 flex flex-col gap-2">
        <div className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Last run — AI insight</div>
        {lastRun ? (
          <>
            <p className="font-mono text-[12px] text-text leading-relaxed">
              <span className={lastRun.ok ? "text-green" : "text-red"}>{lastRun.ok ? "✓" : "⚠"}</span>{" "}
              {lastRun.summary || "(no summary)"}
            </p>
            {trace.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap pt-1">
                <span className="font-mono text-[9px] text-muted-fg/50 uppercase tracking-widest">trace</span>
                {trace.map((t, i) => (
                  <span key={i} className="flex items-center gap-1.5">
                    <span className="font-mono text-[10px] text-purple border border-purple/25 bg-purple/5 rounded px-1.5 py-0.5">{t}</span>
                    {i < trace.length - 1 && <span className="text-muted-fg/40 text-[10px]">→</span>}
                  </span>
                ))}
              </div>
            )}
          </>
        ) : (
          <p className="font-mono text-[11px] text-muted-fg/50">No insight yet — runs report here once the agent executes.</p>
        )}
      </div>
    </div>
  );
}
