import { AnimatePresence, motion } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { StatCard } from "../components/StatCard";
import { EquityChart } from "../components/EquityChart";
import { AgentCard, AgentCardSkeleton, AGENT_DEFS } from "../components/AgentCard";
import { PositionCard } from "../components/PositionCard";
import { Panel } from "../components/Panel";
import { RegimeBadge } from "../components/RegimeBadge";
import { Skeleton } from "@/components/ui/skeleton";
import ThesisLedger from "../components/ThesisLedger";
import { RecentTrades } from "../components/RecentTrades";
import { DailyStats } from "../components/DailyStats";
import { SignalScores } from "../components/SignalScores";
import { FearGreedGauge } from "../components/FearGreedGauge";
import { AgentHeartbeat } from "../components/AgentHeartbeat";
import { WalletBalance } from "../components/WalletBalance";
import { FeesGasSummary } from "../components/FeesGasSummary";
import { StartTradingCTA } from "../components/StartTradingCTA";
import { cn } from "@/lib/utils";
import { usd, pct, ts } from "../lib/formatters";

type Props = { onCopilot: () => void };

export function OverviewView({ onCopilot }: Props) {
  const ledger    = useQuery(api.ledger.latest);
  const risk      = useQuery(api.riskState.get);
  const scorecard = useQuery(api.scorecard.get);
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
    <div className="space-y-5 max-w-[1180px] mx-auto">
      {/* Alert banners */}
      <AnimatePresence>
        {floorHalt && (
          <motion.div
            className="panel rounded-xl px-4 py-3 font-mono text-[12px] font-semibold !bg-red/10 !border-red/30 text-red flex items-center gap-2"
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
          >
            <span className="h-2 w-2 rounded-full bg-red animate-pulse" />
            TRADING HALTED - equity floor hit. Fund wallet or raise floor, then Resume.
          </motion.div>
        )}
        {floorWarn && (
          <motion.div
            className="panel rounded-xl px-4 py-3 font-mono text-[12px] font-semibold !bg-yellow/10 !border-yellow/25 text-yellow flex items-center gap-2"
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
          >
            <span className="h-2 w-2 rounded-full bg-yellow animate-pulse" />
            Portfolio approaching equity floor. Consider adding capital.
          </motion.div>
        )}
      </AnimatePresence>

      {/* Lead with the live risk metrics - this is an operator console, not a
          landing page. PnL + Drawdown are the thesis-critical pair (featured). */}
      <div className="grid grid-cols-4 gap-3 items-stretch max-[900px]:grid-cols-2">
        {ledger === undefined
          ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[104px] w-full bg-surface border border-border rounded-xl" />)
          : <>
              <StatCard label="Cumulative PnL" value={usd(pnl)} unit="USD" featured
                tone={(pnl ?? 0) >= 0 ? "positive" : "negative"} animKey={pnl ?? 0}
                sub={(pnl ?? 0) >= 0 ? "in profit" : "drawdown"} />
              <StatCard label="Max Drawdown" value={pct(dd)} unit="peak" featured
                tone={(dd ?? 0) > 0.05 ? "negative" : (dd ?? 0) > 0 ? "warn" : "positive"}
                sub={(dd ?? 0) > 0.05 ? "breaching" : "within cap"} />
              <StatCard label="Open Exposure" value={usd(risk?.open_exposure_usd)} unit="USD" />
              <StatCard label="Win Rate" value={scorecard?.win_rate != null ? pct(scorecard.win_rate) : "-"} unit="hit" />
            </>
        }
      </div>

      {/* Co-Pilot entry - a slim strip below the metrics, not a hero block. */}
      <StartTradingCTA onStart={onCopilot} />

      {/* Daily stats */}
      <DailyStats />

      {/* Signal scores + Fear & Greed */}
      <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
        <SignalScores />
        <FearGreedGauge />
      </div>

      {/* Agent heartbeat + Wallet balance */}
      <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
        <AgentHeartbeat />
        <WalletBalance />
      </div>

      {/* Equity chart */}
      <Panel label="Equity Curve" action={
        <span className="font-mono text-[10px] text-muted-fg flex items-center gap-3">
          <span className="flex items-center gap-1.5"><span className="h-[2px] w-3 bg-green inline-block rounded" />equity</span>
          <span className="flex items-center gap-1.5"><span className="h-[2px] w-3 bg-red inline-block rounded" />drawdown</span>
        </span>
      }>
        <EquityChart />
      </Panel>

      {/* Open positions */}
      {positions.length > 0 && (
        <Panel label="Open Positions" tick="cyan" action={
          <span className="font-mono text-[10px] text-muted-fg">{positions.length} active</span>
        }>
          <div className="grid grid-cols-3 gap-3 max-[1200px]:grid-cols-2 max-sm:grid-cols-1">
            <AnimatePresence>
              {positions.map((p) => <PositionCard key={p._id} position={p} />)}
            </AnimatePresence>
          </div>
        </Panel>
      )}

      {/* Trade history - actual fills with size, price, TX hash */}
      <RecentTrades />

      {/* Fees & gas */}
      <FeesGasSummary />

      {/* Recent decisions */}
      <Panel label="Recent Decisions" tick="cyan">
        {decisions === undefined
          ? <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-11 w-full bg-elevated rounded-lg" />)}</div>
          : decisions.length === 0
            ? <p className="font-mono text-[12px] text-muted-fg py-2">// no decisions logged yet</p>
            : <div className="flex flex-col gap-1.5">
                {decisions.map((d) => {
                  const allow = d.risk_verdict === "allow";
                  return (
                    <div key={d._id} className="flex items-center gap-3 rounded-lg bg-bg/50 border border-border px-3 py-2.5 text-[13px]">
                      <span className="font-mono text-[11px] text-muted-fg w-16 flex-shrink-0">{ts(d.timestamp_ms)}</span>
                      <span className="font-display font-bold text-cyan w-14 flex-shrink-0">{d.symbol}</span>
                      <RegimeBadge regime={d.regime} />
                      <span className={cn(
                        "ml-auto font-mono text-[10px] font-bold tracking-[0.16em] uppercase px-2 py-1 rounded border",
                        allow ? "text-green border-green/30 bg-green/10" : "text-red border-red/30 bg-red/10",
                      )}>
                        {d.risk_verdict}
                      </span>
                    </div>
                  );
                })}
              </div>
        }
      </Panel>

      {/* Agent roster */}
      <Panel label="Agent Team" tick="purple">
        <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
          {roster === undefined
            ? AGENT_DEFS.map((d) => <AgentCardSkeleton key={d.name} />)
            : AGENT_DEFS.map((def) => (
                <AgentCard key={def.name} def={def}
                  lastEvent={rosterMap.get(def.name)} />
              ))
          }
        </div>
      </Panel>

      <ThesisLedger />
    </div>
  );
}
