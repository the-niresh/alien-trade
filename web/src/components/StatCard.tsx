import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type Tone = "positive" | "negative" | "neutral" | "warn";

const TONE: Record<Tone, { text: string; bar: string; glow: string; wash: string; ring: string }> = {
  positive: { text: "text-green",  bar: "bg-green",     glow: "glow-green",  wash: "tone-wash-positive", ring: "var(--green)" },
  negative: { text: "text-red",    bar: "bg-red",       glow: "glow-red",    wash: "tone-wash-negative", ring: "var(--red)" },
  neutral:  { text: "text-text",   bar: "bg-border-hi", glow: "",            wash: "tone-wash-neutral",  ring: "var(--border-hi)" },
  warn:     { text: "text-yellow", bar: "bg-yellow",    glow: "glow-yellow", wash: "tone-wash-warn",     ring: "var(--yellow)" },
};

type Props = {
  label: string;
  value: string;
  tone?: Tone;
  sub?: string;
  unit?: string;
  featured?: boolean;
  animKey?: string | number;
};

export function StatCard({ label, value, tone = "neutral", sub, unit, featured = false, animKey }: Props) {
  const t = TONE[tone];
  return (
    <div className={cn(
      "panel relative overflow-hidden flex flex-col justify-between",
      featured ? "p-5 min-h-[136px]" : "p-4 min-h-[108px]",
    )}>
      {/* Diagonal tone wash — fills bottom-left corner */}
      <span className={cn("absolute inset-0 pointer-events-none rounded-xl", t.wash)} />

      {/* Left accent bar — full height, gradient fade */}
      <span
        className="absolute left-0 top-0 bottom-0 w-[3px] rounded-r-full"
        style={{
          background: `linear-gradient(to bottom, transparent 0%, ${t.ring} 20%, ${t.ring} 80%, transparent 100%)`,
          opacity: 0.9,
          boxShadow: featured ? `2px 0 16px ${t.ring}60` : `2px 0 8px ${t.ring}40`,
        }}
      />

      {/* Header row */}
      <div className="flex items-center justify-between relative z-10">
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-fg">{label}</span>
        {unit && (
          <span className="font-mono text-[9px] tracking-[0.12em] uppercase text-border-hi">{unit}</span>
        )}
      </div>

      {/* Value */}
      <motion.div
        className={cn(
          "font-display font-bold leading-none tabular-nums relative z-10",
          featured ? "text-[42px]" : "text-[28px]",
          t.text, t.glow,
        )}
        key={animKey ?? value}
        initial={{ opacity: 0.3, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      >
        {value}
      </motion.div>

      {/* Footer */}
      <div className="flex items-center justify-between relative z-10 min-h-[16px]">
        {sub && (
          <span className="font-mono text-[11px] text-muted-fg tracking-wide">{sub}</span>
        )}
        {featured && (
          <span
            className="font-mono text-[9px] font-bold tracking-[0.18em] uppercase px-1.5 py-0.5 rounded"
            style={{
              color: t.ring,
              background: `color-mix(in oklab, ${t.ring} 10%, transparent)`,
              border: `1px solid color-mix(in oklab, ${t.ring} 25%, transparent)`,
            }}
          >
            LIVE
          </span>
        )}
      </div>
    </div>
  );
}
