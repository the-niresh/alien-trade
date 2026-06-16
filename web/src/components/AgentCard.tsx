import { motion } from "framer-motion";
import { ts } from "../lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type AgentDef = {
  name: string;
  label: string;
  color: string;
  bg: string;
  role: string;
};

export const AGENT_DEFS: AgentDef[] = [
  { name: "CoPilot",    label: "CP", color: "var(--cyan)",   bg: "#00d4ff18", role: "Answers your questions about the market, regime and trades." },
  { name: "Historian",  label: "HI", color: "var(--yellow)", bg: "#ffd60a18", role: "Queries the Second Brain for institutional memory before each trade." },
  { name: "Researcher", label: "RE", color: "var(--purple)", bg: "#a855f718", role: "Auto-researches market anomalies and builds the research digest." },
  { name: "Reflector",  label: "RF", color: "var(--red)",    bg: "#ff306018", role: "Writes structured reflections after every trade for Hermes learning." },
];

type LastEvent = { ts_ms: number; kind: string; headline: string };
type Props = { def: AgentDef; lastEvent?: LastEvent; onClick: () => void };

export function AgentCard({ def, lastEvent, onClick }: Props) {
  const now = Date.now();
  const ageSec = lastEvent ? (now - lastEvent.ts_ms) / 1000 : Infinity;
  const isActive = ageSec < 60;
  const isRecent = ageSec < 300;
  const status   = isActive ? "ONLINE" : isRecent ? "ACTIVE" : "IDLE";
  const dotColor = isActive ? "var(--green)" : isRecent ? "var(--yellow)" : "var(--border-hi)";

  return (
    <button
      className="panel group relative w-full text-left p-5 cursor-pointer transition-all hover:-translate-y-0.5 hover:border-border-hi overflow-hidden"
      onClick={onClick}
    >
      {/* accent wash in agent colour */}
      <span
        className="absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-[0.07] blur-xl transition-opacity group-hover:opacity-15"
        style={{ background: def.color }}
      />

      <div className="flex items-center gap-3 mb-3 relative">
        <motion.div
          className="w-[44px] h-[44px] rounded-xl flex items-center justify-center font-mono text-[13px] font-bold flex-shrink-0"
          style={{ color: def.color, background: def.bg, border: `1px solid ${def.color}40` }}
          animate={isActive
            ? { boxShadow: [`0 0 6px ${def.color}30`, `0 0 22px ${def.color}70`, `0 0 6px ${def.color}30`] }
            : {}}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        >
          {def.label}
        </motion.div>
        <div className="flex-1 min-w-0">
          <div className="font-display text-[15px] font-bold tracking-wide" style={{ color: def.color }}>{def.name}</div>
          <div className="text-[12px] text-muted-fg leading-snug line-clamp-1">{def.role}</div>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <motion.span
            className="w-2 h-2 rounded-full"
            style={{ background: dotColor, boxShadow: isActive ? `0 0 8px ${dotColor}` : "none" }}
            animate={isActive ? { opacity: [1, 0.35, 1] } : {}}
            transition={{ duration: 1, repeat: Infinity }}
          />
          <span className="font-mono text-[9px] tracking-[0.12em]" style={{ color: dotColor }}>{status}</span>
        </div>
      </div>

      <div className="rounded-lg bg-bg/60 border border-border px-3 py-2.5">
        {lastEvent ? (
          <>
            <div className="text-[12.5px] text-text/85 leading-relaxed line-clamp-2">{lastEvent.headline}</div>
            <div className="font-mono text-[10px] text-muted-fg mt-1.5 flex items-center gap-1.5">
              <span>{ts(lastEvent.ts_ms)}</span>
              <span className="text-border-hi">·</span>
              <span className="uppercase tracking-wide">{lastEvent.kind}</span>
            </div>
          </>
        ) : (
          <div className={cn("text-[12.5px] text-muted-fg italic")}>Awaiting first transmission…</div>
        )}
      </div>
    </button>
  );
}

export function AgentCardSkeleton() {
  return (
    <div className="panel p-5">
      <div className="flex items-center gap-3 mb-3">
        <Skeleton className="w-[44px] h-[44px] rounded-xl bg-elevated" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-24 bg-elevated" />
          <Skeleton className="h-3 w-40 bg-elevated" />
        </div>
      </div>
      <Skeleton className="h-12 w-full bg-elevated rounded-lg" />
    </div>
  );
}
