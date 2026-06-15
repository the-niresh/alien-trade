import { AnimatePresence, motion } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { StatCard } from "../components/StatCard";
import { EquityChart } from "../components/EquityChart";
import { AgentCard, AgentCardSkeleton, AGENT_DEFS } from "../components/AgentCard";
import { PositionCard } from "../components/PositionCard";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import ThesisLedger from "../components/ThesisLedger";
import { usd, pct, ts } from "../lib/formatters";

type Props = { onAgentClick: (name: string) => void };

export function OverviewView({ onAgentClick }: Props) {
  const ledger    = useQuery(api.ledger.latest);
  const risk      = useQuery(api.riskState.get);
  const decisions = useQuery(api.decisions.recent, { limit: 3 });
  const roster    = useQuery(api.agentEvents.latestPerAgent);
  const positions = useQuery(api.positions.open) ?? [];
  const events    = useQuery(api.agentEvents.recent, { limit: 30 });

  const pnl = ledger?.cumulative_pnl_usd;
  const dd  = risk?.current_drawdown_pct;

  const floorHalt = (events ?? []).find(
    (e) => e.agent === "RiskGuard" && e.kind === "control" &&
      typeof e.headline === "string" && e.headline.includes("floor hit"),
  );
  const floorWarn = !floorHalt && (events ?? []).find(
    (e) => e.agent === "RiskGuard" && e.kind === "control" &&
      typeof e.headline === "string" && e.headline.includes("approaching floor"),
  );

  const rosterMap = new Map(
    (roster ?? []).map((e: { agent: string; ts_ms: number; kind: string; headline: string }) =>
      [e.agent, { ts_ms: e.ts_ms, kind: e.kind, headline: e.headline }]
    )
  );

  return (
    <div className="space-y-5">
      {/* Alert banners */}
      <AnimatePresence>
        {floorHalt && (
          <motion.div
            className="rounded-xl px-4 py-3 font-semibold text-[13px] bg-red/10 text-red border border-red/25"
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
          >
            Trading HALTED — equity floor hit. Fund wallet or raise floor, then Resume.
          </motion.div>
        )}
        {floorWarn && (
          <motion.div
            className="rounded-xl px-4 py-3 font-semibold text-[13px] bg-yellow/10 text-yellow border border-yellow/20"
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
          >
            Portfolio approaching equity floor. Consider adding capital.
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-3 max-[900px]:grid-cols-2">
        {ledger === undefined
          ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full bg-surface border border-border rounded-[14px]" />)
          : <>
              <StatCard label="Cumulative PnL" value={usd(pnl)}
                tone={(pnl ?? 0) >= 0 ? "positive" : "negative"} animKey={pnl ?? 0} />
              <StatCard label="Max Drawdown" value={pct(dd)}
                tone={(dd ?? 0) > 0.05 ? "negative" : (dd ?? 0) > 0 ? "warn" : "positive"} />
              <StatCard label="Open Exposure" value={usd(risk?.open_exposure_usd)} />
              <StatCard label="Win Rate" value={risk?.win_rate != null ? pct(risk.win_rate) : "—"} />
            </>
        }
      </div>

      {/* Equity chart */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-2">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Equity Curve</p>
        </CardHeader>
        <CardContent>
          <EquityChart />
        </CardContent>
      </Card>

      {/* Open positions */}
      {positions.length > 0 && (
        <Card className="bg-surface border-border">
          <CardHeader className="pb-2">
            <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Open Positions</p>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3 max-[1200px]:grid-cols-2 max-sm:grid-cols-1">
              <AnimatePresence>
                {positions.map((p) => <PositionCard key={p._id} position={p} />)}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent decisions */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-2">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Recent Decisions</p>
        </CardHeader>
        <CardContent>
          {decisions === undefined
            ? <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12 w-full bg-elevated" />)}</div>
            : decisions.length === 0
              ? <p className="text-[13px] text-muted-fg">No decisions yet.</p>
              : <div className="divide-y divide-border">
                  {decisions.map((d) => (
                    <div key={d._id} className="flex items-center justify-between text-[13px] py-2">
                      <span className="text-muted-fg text-[11px]">{ts(d.timestamp_ms)}</span>
                      <span className="text-cyan font-bold">{d.symbol}</span>
                      <span className="text-muted-fg">{d.regime}</span>
                      <span className={d.risk_verdict === "allow" ? "text-green font-bold" : "text-red font-bold"}>{d.risk_verdict}</span>
                    </div>
                  ))}
                </div>
          }
        </CardContent>
      </Card>

      {/* Agent roster */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-2">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Agent Team</p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
            {roster === undefined
              ? AGENT_DEFS.map((d) => <AgentCardSkeleton key={d.name} />)
              : AGENT_DEFS.map((def) => (
                  <AgentCard key={def.name} def={def}
                    lastEvent={rosterMap.get(def.name)}
                    onClick={() => onAgentClick(def.name)} />
                ))
            }
          </div>
        </CardContent>
      </Card>

      <ThesisLedger />
    </div>
  );
}
