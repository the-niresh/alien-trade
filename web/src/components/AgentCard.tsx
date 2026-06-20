import { motion } from "framer-motion";
import { Bot, BookOpen, FlaskConical, Sparkles, Wallet, type LucideIcon } from "lucide-react";
import { ts } from "../lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type AgentDef = {
  name: string;
  icon: LucideIcon;
  color: string;
  bg: string;
  role: string;
};

export const AGENT_DEFS: AgentDef[] = [
  { name: "CoPilot",       icon: Bot,           color: "var(--cyan)",   bg: "#00d4ff14", role: "Answers your questions about the market, regime and trades." },
  { name: "Historian",     icon: BookOpen,      color: "var(--yellow)", bg: "#ffd60a14", role: "Queries the Second Brain for institutional memory before each trade." },
  { name: "Researcher",    icon: FlaskConical,  color: "var(--purple)", bg: "#a855f714", role: "Auto-researches market anomalies and builds the research digest." },
  { name: "Reflector",     icon: Sparkles,      color: "var(--red)",    bg: "#ff306014", role: "Writes structured reflections after every trade for Hermes learning." },
  { name: "WalletManager", icon: Wallet,        color: "var(--green)",  bg: "#22c55e14", role: "Monitors real wallet vs ledger, detects swap failures, auto-realigns positions." },
];

const KIND_COLOR: Record<string, string> = {
  control:  "var(--red)",
  decision: "var(--green)",
  handoff:  "var(--yellow)",
  analysis: "var(--cyan)",
  observation: "var(--purple)",
};

type LastEvent = { ts_ms: number; kind: string; headline: string };
type Props = { def: AgentDef; lastEvent?: LastEvent; onClick: () => void };

export function AgentCard({ def, lastEvent, onClick }: Props) {
  const now = Date.now();
  const ageSec = lastEvent ? (now - lastEvent.ts_ms) / 1000 : Infinity;
  const isActive = ageSec < 60;
  const isRecent = ageSec < 300;
  const status   = isActive ? "ONLINE" : isRecent ? "ACTIVE" : "IDLE";
  const dotColor = isActive ? "var(--green)" : isRecent ? "var(--yellow)" : "var(--border-hi)";
  const kindColor = lastEvent ? (KIND_COLOR[lastEvent.kind] ?? "var(--border-hi)") : "var(--border-hi)";

  return (
    <button
      className="panel group relative w-full text-left p-5 cursor-pointer overflow-hidden panel-interactive"
      style={{ transition: "border-color 180ms ease, transform 180ms ease, box-shadow 180ms ease" }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = `color-mix(in oklab, ${def.color} 40%, var(--border))`;
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = "";
      }}
      onClick={onClick}
    >
      {/* Agent colour ambient wash — top right */}
      <span
        className="absolute -right-6 -top-6 h-28 w-28 rounded-full pointer-events-none transition-opacity duration-300 group-hover:opacity-20"
        style={{ background: def.color, filter: "blur(28px)", opacity: 0.07 }}
      />
      {/* Second glow — bottom left */}
      <span
        className="absolute -left-4 -bottom-4 h-16 w-16 rounded-full pointer-events-none opacity-0 group-hover:opacity-10 transition-opacity duration-300"
        style={{ background: def.color, filter: "blur(20px)" }}
      />

      {/* Header row */}
      <div className="flex items-center gap-3 mb-3.5 relative">
        {/* Avatar */}
        <motion.div
          className="w-[46px] h-[46px] rounded-xl flex items-center justify-center flex-shrink-0 relative"
          style={{ color: def.color, background: def.bg, border: `1px solid color-mix(in oklab, ${def.color} 30%, transparent)` }}
          animate={isActive
            ? { boxShadow: [`0 0 4px color-mix(in oklab, ${def.color} 25%, transparent)`, `0 0 20px color-mix(in oklab, ${def.color} 65%, transparent)`, `0 0 4px color-mix(in oklab, ${def.color} 25%, transparent)`] }
            : { boxShadow: "none" }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
        >
          <def.icon size={20} strokeWidth={1.75} />
        </motion.div>

        {/* Name + role */}
        <div className="flex-1 min-w-0">
          <div className="font-display text-[15px] font-bold tracking-wide" style={{ color: def.color }}>
            {def.name}
          </div>
          <div className="text-[11.5px] text-muted-fg leading-snug line-clamp-1 mt-0.5">{def.role}</div>
        </div>

        {/* Status badge */}
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          <motion.span
            className="w-2 h-2 rounded-full"
            style={{ background: dotColor, boxShadow: isActive ? `0 0 8px ${dotColor}` : "none" }}
            animate={isActive ? { opacity: [1, 0.3, 1] } : {}}
            transition={{ duration: 1.1, repeat: Infinity }}
          />
          <span
            className="font-mono text-[9px] font-bold tracking-[0.14em] uppercase px-1.5 py-0.5 rounded"
            style={{
              color: dotColor,
              background: `color-mix(in oklab, ${dotColor} 10%, transparent)`,
              border: `1px solid color-mix(in oklab, ${dotColor} 20%, transparent)`,
            }}
          >
            {status}
          </span>
        </div>
      </div>

      {/* Last event log */}
      <div
        className="rounded-lg bg-bg/60 px-3 py-2.5 relative overflow-hidden"
        style={{ border: `1px solid color-mix(in oklab, ${kindColor} 18%, var(--border))` }}
      >
        {/* kind accent — left edge */}
        <span
          className="absolute left-0 top-0 bottom-0 w-[2.5px] rounded-r-sm"
          style={{ background: kindColor, opacity: 0.7 }}
        />
        {lastEvent ? (
          <>
            <div className="text-[12.5px] text-text/85 leading-relaxed line-clamp-2 pl-1">{lastEvent.headline}</div>
            <div className="font-mono text-[10px] text-muted-fg mt-1.5 pl-1 flex items-center gap-1.5">
              <span>{ts(lastEvent.ts_ms)}</span>
              <span className="text-border-hi">·</span>
              <span
                className="uppercase tracking-[0.1em] font-bold text-[9px]"
                style={{ color: kindColor }}
              >
                {lastEvent.kind}
              </span>
            </div>
          </>
        ) : (
          <div className="font-mono text-[12px] text-muted-fg/60 pl-1 tracking-wide">
            <span className="text-muted-fg/40">›_</span> awaiting transmission…
          </div>
        )}
      </div>
    </button>
  );
}

export function AgentCardSkeleton() {
  return (
    <div className="panel p-5">
      <div className="flex items-center gap-3 mb-3.5">
        <Skeleton className="w-[46px] h-[46px] rounded-xl bg-elevated" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-24 bg-elevated" />
          <Skeleton className="h-3 w-40 bg-elevated" />
        </div>
        <Skeleton className="h-4 w-12 bg-elevated rounded-full" />
      </div>
      <Skeleton className="h-[54px] w-full bg-elevated rounded-lg" />
    </div>
  );
}
