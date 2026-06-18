import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { RegimeBadge } from "../components/RegimeBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { usd, ts } from "../lib/formatters";
import { Activity, Clock, CheckCircle2, XCircle, Loader2 } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  queued:  "text-yellow border-yellow/30 bg-yellow/8",
  running: "text-cyan border-cyan/30 bg-cyan/8",
  done:    "text-green border-green/30 bg-green/8",
  failed:  "text-red border-red/30 bg-red/8",
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  queued:  <Clock className="w-3 h-3" />,
  running: <Loader2 className="w-3 h-3 animate-spin" />,
  done:    <CheckCircle2 className="w-3 h-3" />,
  failed:  <XCircle className="w-3 h-3" />,
};

type Position = {
  _id: string;
  symbol: string;
  quantity: number;
  avg_entry_price: number;
  current_price?: number;
  current_value_usd?: number;
  unrealized_pnl_usd: number;
  mode?: string;
  updated_ms?: number;
};

type AgentCommand = {
  _id: string;
  command_type: string;
  params?: string;
  status: string;
  queued_by?: string;
  queued_at_ms: number;
  updated_at_ms?: number;
  error?: string;
};

type Decision = {
  _id: string;
  symbol: string;
  regime: string;
  risk_verdict: string;
  timestamp_ms: number;
};

export function TrackersView() {
  const positions = useQuery(api.positions.open) ?? [];
  const commands  = useQuery(api.agentCommands.list, { limit: 20 }) ?? [];
  const decisions = useQuery(api.decisions.recent, { limit: 1 }) ?? [];

  const typedPositions = positions as Position[];
  const typedCommands  = commands as AgentCommand[];
  const typedDecisions = decisions as Decision[];

  const ongoing = typedCommands.filter((c) => c.status === "running");
  const pending = typedCommands.filter((c) => c.status === "queued");
  const recent  = typedCommands.filter((c) => c.status === "done" || c.status === "failed").slice(0, 5);
  const nextDecision = typedDecisions[0];

  const positionsLoading  = positions === undefined;
  const commandsLoading   = commands === undefined;

  return (
    <div className="max-w-[900px] mx-auto space-y-4">
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span
            className="h-[2px] w-4 bg-cyan rounded-full inline-block"
            style={{ boxShadow: "0 0 6px var(--cyan)" }}
          />
          Live Agent Activity
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Trackers</h1>
      </div>

      {/* Ongoing — open positions */}
      <Panel
        label="Ongoing Trades"
        tick="green"
        action={
          <span className="font-mono text-[10px] text-muted-fg">
            {positionsLoading ? "…" : `${typedPositions.length} open`}
          </span>
        }
      >
        {positionsLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full rounded-lg" />
            <Skeleton className="h-10 w-full rounded-lg" />
          </div>
        ) : typedPositions.length === 0 ? (
          <div className="flex items-center gap-3 py-3">
            <Activity className="w-4 h-4 text-muted-fg" />
            <p className="font-mono text-[12px] text-muted-fg">
              No active trades — agent is watching the market.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {typedPositions.map((p) => {
              const pnlPos = p.unrealized_pnl_usd >= 0;
              return (
                <div
                  key={p._id}
                  className="flex items-center gap-3 rounded-lg bg-bg/50 border border-border px-3 py-2.5"
                >
                  <span className="font-mono font-bold text-cyan text-[13px] w-14">{p.symbol}</span>
                  <span className="font-mono text-[11px] text-muted-fg">
                    {p.quantity.toFixed(6)}
                  </span>
                  <span className="font-mono text-[11px] text-muted-fg ml-1">
                    @ {usd(p.avg_entry_price)}
                  </span>
                  <span
                    className={cn(
                      "ml-auto font-mono text-[12px] font-bold",
                      pnlPos ? "text-green" : "text-red",
                    )}
                  >
                    {pnlPos ? "+" : ""}{usd(p.unrealized_pnl_usd)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </Panel>

      {/* Next planned action */}
      {nextDecision && (
        <Panel label="Next Decision" tick="cyan">
          <div className="flex items-center gap-3 rounded-lg bg-bg/50 border border-border px-3 py-2.5">
            <span className="font-mono font-bold text-cyan text-[13px] w-14">
              {nextDecision.symbol}
            </span>
            <RegimeBadge regime={nextDecision.regime} />
            <span
              className={cn(
                "ml-auto font-mono text-[10px] font-bold tracking-[0.16em] uppercase px-2 py-1 rounded border",
                nextDecision.risk_verdict === "allow"
                  ? "text-green border-green/30 bg-green/10"
                  : "text-red border-red/30 bg-red/10",
              )}
            >
              {nextDecision.risk_verdict}
            </span>
          </div>
        </Panel>
      )}

      {/* Pending / running commands */}
      {(ongoing.length > 0 || pending.length > 0) && (
        <Panel
          label="Pending Commands"
          tick="yellow"
          action={
            <span className="font-mono text-[10px] text-muted-fg">
              {ongoing.length + pending.length} queued
            </span>
          }
        >
          <div className="space-y-2">
            {[...ongoing, ...pending].map((c) => (
              <div
                key={c._id}
                className="flex items-center gap-3 rounded-lg bg-bg/50 border border-border px-3 py-2.5"
              >
                <span
                  className={cn(
                    "flex items-center gap-1 font-mono text-[10px] font-bold px-2 py-0.5 rounded border",
                    STATUS_STYLE[c.status] ?? STATUS_STYLE["queued"],
                  )}
                >
                  {STATUS_ICON[c.status]}
                  {c.status}
                </span>
                <span className="font-mono text-[12px] text-text">{c.command_type}</span>
                <span className="font-mono text-[10px] text-muted-fg ml-auto">
                  {ts(c.queued_at_ms)}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {/* Recent command history */}
      {recent.length > 0 && (
        <Panel label="Command History" tick="cyan">
          <div className="space-y-2">
            {recent.map((c) => (
              <div
                key={c._id}
                className="flex items-center gap-3 rounded-lg bg-bg/50 border border-border px-3 py-2.5"
              >
                <span
                  className={cn(
                    "flex items-center gap-1 font-mono text-[10px] font-bold px-2 py-0.5 rounded border",
                    STATUS_STYLE[c.status] ?? STATUS_STYLE["done"],
                  )}
                >
                  {STATUS_ICON[c.status]}
                  {c.status}
                </span>
                <span className="font-mono text-[12px] text-text">{c.command_type}</span>
                {c.error && (
                  <span className="font-mono text-[10px] text-red truncate max-w-[200px]">
                    {c.error}
                  </span>
                )}
                <span className="font-mono text-[10px] text-muted-fg ml-auto">
                  {ts(c.queued_at_ms)}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {/* Empty state when no commands at all */}
      {!commandsLoading && ongoing.length === 0 && pending.length === 0 && recent.length === 0 && (
        <Panel label="Command History" tick="cyan">
          <div className="flex items-center gap-3 py-3">
            <Activity className="w-4 h-4 text-muted-fg" />
            <p className="font-mono text-[12px] text-muted-fg">
              No commands dispatched yet.
            </p>
          </div>
        </Panel>
      )}
    </div>
  );
}
