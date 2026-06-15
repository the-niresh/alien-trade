import { motion } from "framer-motion";
import { ts } from "../lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";

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
  const dotColor = isActive ? "var(--green)" : isRecent ? "var(--yellow)" : "var(--border-hi)";

  return (
    <div
      className="bg-surface border border-border rounded-2xl p-5 cursor-pointer transition-colors hover:bg-elevated"
      onClick={onClick}
    >
      <div className="flex items-center gap-3 mb-3">
        <motion.div
          className="w-[42px] h-[42px] rounded-full flex items-center justify-center text-[13px] font-black flex-shrink-0"
          style={{ color: def.color, background: def.bg, border: `1.5px solid ${def.color}40` }}
          animate={isActive
            ? { boxShadow: [`0 0 8px ${def.color}40`, `0 0 20px ${def.color}80`, `0 0 8px ${def.color}40`] }
            : { scale: [1, 1.03, 1] }}
          transition={{ duration: isActive ? 1.5 : 4, repeat: Infinity, ease: "easeInOut" }}
        >
          {def.label}
        </motion.div>
        <div className="flex-1">
          <div className="font-grotesk text-[16px] font-bold" style={{ color: def.color }}>{def.name}</div>
          <div className="text-[12px] text-muted-fg">{def.role}</div>
        </div>
        <motion.div
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ background: dotColor }}
          animate={isActive ? { opacity: [1, 0.4, 1] } : {}}
          transition={{ duration: 1, repeat: Infinity }}
        />
      </div>
      {lastEvent ? (
        <>
          <div className="text-[13px] text-text/80 leading-relaxed line-clamp-2">{lastEvent.headline}</div>
          <div className="text-[11px] text-muted-fg mt-2">{ts(lastEvent.ts_ms)} · {lastEvent.kind}</div>
        </>
      ) : (
        <div className="text-[13px] text-muted-fg italic">No activity yet</div>
      )}
    </div>
  );
}

export function AgentCardSkeleton() {
  return (
    <div className="bg-surface border border-border rounded-2xl p-5">
      <div className="flex items-center gap-3 mb-3">
        <Skeleton className="w-[42px] h-[42px] rounded-full bg-elevated" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-24 bg-elevated" />
          <Skeleton className="h-3 w-40 bg-elevated" />
        </div>
      </div>
      <Skeleton className="h-8 w-full bg-elevated" />
    </div>
  );
}
