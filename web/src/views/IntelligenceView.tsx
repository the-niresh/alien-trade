import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { SponsorCard } from "../components/SponsorCard";
import { cn } from "@/lib/utils";
import { Brain, Cpu, BookOpen, FlaskConical, MessageSquare, ChevronRight } from "lucide-react";

// ── helpers ───────────────────────────────────────────────────────────────────

function StatusPill({ status }: { status: "ON" | "OFF" | "ARMED" }) {
  const styles: Record<typeof status, string> = {
    ON:    "bg-green/10 text-green border-green/25",
    OFF:   "bg-muted-fg/10 text-muted-fg border-muted-fg/20",
    ARMED: "bg-yellow/10 text-yellow border-yellow/25",
  };
  return (
    <span
      className={cn(
        "font-mono text-[9px] font-bold tracking-[0.18em] uppercase px-1.5 py-0.5 rounded border",
        styles[status],
      )}
    >
      {status}
    </span>
  );
}

function FlowArrow() {
  return (
    <ChevronRight className="w-4 h-4 text-muted-fg/50 flex-shrink-0 max-sm:hidden" />
  );
}

// ── intelligence flow node ─────────────────────────────────────────────────────

interface FlowNodeProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  sub: string;
  status: "ON" | "OFF" | "ARMED";
  detail?: string;
  iconColor?: string;
}

function FlowNode({ icon: Icon, title, sub, status, detail, iconColor = "text-green" }: FlowNodeProps) {
  return (
    <div className="panel flex-1 min-w-0 px-3 py-2.5 flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <Icon className={cn("w-4 h-4 flex-shrink-0", iconColor)} />
        <StatusPill status={status} />
      </div>
      <div>
        <p className="font-display font-bold text-[13px] text-text leading-tight">{title}</p>
        <p className="font-mono text-[10px] text-muted-fg mt-0.5">{sub}</p>
      </div>
      {detail && (
        <p className="font-mono text-[10px] text-muted-fg/70 truncate">{detail}</p>
      )}
    </div>
  );
}

// ── main view ─────────────────────────────────────────────────────────────────

export function IntelligenceView() {
  const agentEvents  = useQuery(api.agentEvents.recent, { limit: 100 }) ?? [];
  const auditRows    = useQuery(api.audit.recent,        { limit: 200 }) ?? [];
  const tradeRows    = useQuery(api.trades.recent,       { limit: 200 }) ?? [];
  const reflections  = useQuery(api.reflections.recent,  { limit: 1  }) ?? [];

  // CMC call count — filter by agent/headline containing CMC or price signal
  const cmcCallCount = agentEvents.filter(
    (e) =>
      e.agent?.toLowerCase().includes("cmc") ||
      e.agent?.toLowerCase().includes("price") ||
      (typeof e.headline === "string" && e.headline.toLowerCase().includes("cmc")) ||
      (typeof e.headline === "string" && e.headline.toLowerCase().includes("price feed")),
  ).length;

  // TWAK swap count — audit rows with event_type containing "swap"
  const swapCount = auditRows.filter((r) =>
    r.event_type?.toLowerCase().includes("swap"),
  ).length;

  // Trades on-chain count
  const tradesCount = tradeRows.length;

  // Reflection / Hermes
  const lastReflection = reflections[0];
  const hermesOn = reflections.length > 0;

  // AutoResearch — agentEvents from a research agent
  const researchEvents = agentEvents.filter(
    (e) =>
      e.agent?.toLowerCase().includes("research") ||
      (typeof e.headline === "string" && e.headline.toLowerCase().includes("research digest")),
  );
  const autoResearchOn = researchEvents.length > 0;
  const lastResearch   = researchEvents[0];

  return (
    <div className="max-w-[960px] mx-auto space-y-5">
      {/* ── Page header ───────────────────────────────────────────────────── */}
      <div className="mb-1">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span
            className="h-[2px] w-4 bg-green rounded-full inline-block"
            style={{ boxShadow: "0 0 6px var(--green)" }}
          />
          The thinking layer
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">
          Intelligence
        </h1>
      </div>

      {/* ── Architecture banner ───────────────────────────────────────────── */}
      <div
        className="panel rounded-xl px-4 py-3.5 flex items-start gap-3 !border-green/25 !bg-green/5"
        style={{ boxShadow: "0 0 32px color-mix(in oklab, var(--green) 8%, transparent)" }}
      >
        <div
          className="mt-0.5 p-2 rounded-lg bg-green/10 border border-green/20 flex-shrink-0"
          style={{ boxShadow: "0 0 12px color-mix(in oklab, var(--green) 22%, transparent)" }}
        >
          <Cpu className="w-4 h-4 text-green" />
        </div>
        <div>
          <p className="font-display font-bold text-[14px] text-green tracking-wide">
            LLM is OFF the trade hot path
          </p>
          <p className="font-mono text-[12px] text-muted-fg mt-0.5 leading-relaxed">
            Decisions are deterministic Python in{" "}
            <span className="text-text font-bold">/core</span>. The LLM learns{" "}
            <em>around</em> the trade — regime narrative, post-trade reflection, market
            research — all async, zero latency impact.
          </p>
        </div>
      </div>

      {/* ── External services this agent depends on ──────────────────────── */}
      <div>
        <div className="panel-label mb-3" style={{ "--tick": "var(--green)" } as React.CSSProperties}>
          Services it depends on
        </div>
        <div className="grid grid-cols-3 gap-3 max-[780px]:grid-cols-1 max-[1100px]:grid-cols-2">
          {/* CMC */}
          <SponsorCard
            sponsor="CMC"
            name="CoinMarketCap Agent Hub"
            tagline="Live market data for every decision"
            integrations={[
              "OHLCV price feed → momentum + trend signals",
              "Funding rate + Open Interest → contrarian entries",
              "Social sentiment → rate-of-change attention signal",
              "On-chain exchange flow → accumulation detection",
              "x402 micropayments on every data call (EIP-3009)",
            ]}
            stat={{ label: "CMC calls (recent)", value: cmcCallCount }}
          />

          {/* TWAK */}
          <SponsorCard
            sponsor="TWAK"
            name="Trust Wallet Agent Kit"
            tagline="Self-custody signing — keys never in code"
            integrations={[
              "ALL swap signing via `twak swap` (zero raw keys)",
              "Rug-check gate before every swap",
              "Portfolio refresh from on-chain wallet",
              "Real-time price feed for mark-to-market",
              "ERC-20 approve/revoke for safe DeFi interactions",
              "x402 EIP-3009 gasless payment signing",
            ]}
            stat={{ label: "Swaps executed", value: swapCount }}
          />

          {/* BNB SDK */}
          <SponsorCard
            sponsor="BNB_SDK"
            name="BNB AI Agent SDK"
            tagline="On-chain execution on BNB Smart Chain"
            integrations={[
              "PancakeSwap spot swaps via `twak swap`",
              "Slippage simulation before every send",
              "Gas estimation → real cost model in backtest",
              "On-chain receipt as ledger source of truth",
              "BSC token registry: ETH/CAKE/UNI/LINK/AAVE",
            ]}
            stat={{ label: "Trades on-chain", value: tradesCount }}
          />
        </div>
      </div>

      {/* ── Intelligence layer flow ───────────────────────────────────────── */}
      <div>
        <div className="panel-label mb-3" style={{ "--tick": "var(--purple)" } as React.CSSProperties}>
          Intelligence Layer
        </div>

        <div className="flex items-stretch gap-2 max-sm:flex-col">
          <FlowNode
            icon={Cpu}
            title="Deterministic Core"
            sub="Signal engine (Python/core)"
            status="ON"
            iconColor="text-green"
            detail="Always on — every buy/sell decision"
          />
          <FlowArrow />

          <FlowNode
            icon={Brain}
            title="Hermes Reflection"
            sub="Post-trade self-learning"
            status={hermesOn ? "ON" : "OFF"}
            iconColor={hermesOn ? "text-cyan" : "text-muted-fg"}
            detail={
              lastReflection
                ? `Last: ${lastReflection.lesson?.slice(0, 48) ?? "—"}…`
                : "No reflections yet"
            }
          />
          <FlowArrow />

          <FlowNode
            icon={FlaskConical}
            title="AutoResearch"
            sub="Karpathy-style market digest"
            status={autoResearchOn ? "ON" : "OFF"}
            iconColor={autoResearchOn ? "text-cyan" : "text-muted-fg"}
            detail={
              lastResearch
                ? (typeof lastResearch.headline === "string"
                    ? lastResearch.headline.slice(0, 48)
                    : "Research event logged")
                : "No research events yet"
            }
          />
          <FlowArrow />

          <FlowNode
            icon={BookOpen}
            title="Second Brain"
            sub="Upstash Vector memory"
            status="ARMED"
            iconColor="text-yellow"
            detail="Armed — activates post-trade"
          />
          <FlowArrow />

          <FlowNode
            icon={MessageSquare}
            title="Co-Pilot"
            sub="LLM narrative layer"
            status="ON"
            iconColor="text-green"
            detail="Regime reports + user chat"
          />
        </div>

        <p className="font-mono text-[10px] text-muted-fg/60 mt-3 text-center leading-relaxed">
          Intelligence layer runs async, off the trade hot path.
          The deterministic core makes every buy/sell decision.
        </p>
      </div>
    </div>
  );
}
