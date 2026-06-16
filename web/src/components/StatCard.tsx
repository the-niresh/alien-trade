import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type Tone = "positive" | "negative" | "neutral" | "warn";

const TONE: Record<Tone, { text: string; bar: string; glow: string }> = {
  positive: { text: "text-green",     bar: "bg-green",  glow: "glow-green" },
  negative: { text: "text-red",       bar: "bg-red",    glow: "glow-red" },
  neutral:  { text: "text-text",      bar: "bg-border-hi", glow: "" },
  warn:     { text: "text-yellow",    bar: "bg-yellow", glow: "" },
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
      featured ? "p-5 min-h-[124px]" : "p-4 min-h-[104px]",
    )}>
      {/* tone accent bar */}
      <span className={cn("absolute left-0 top-4 bottom-4 w-[3px] rounded-r-full opacity-80", t.bar)} />

      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-fg">{label}</span>
        {unit && <span className="font-mono text-[10px] text-border-hi">{unit}</span>}
      </div>

      <motion.div
        className={cn(
          "font-display font-bold leading-none tabular-nums",
          featured ? "text-[40px]" : "text-[27px]",
          t.text, t.glow,
        )}
        key={animKey ?? value}
        initial={{ opacity: 0.4, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
      >
        {value}
      </motion.div>

      <div className="h-[14px]">
        {sub && <span className="font-mono text-[11px] text-muted-fg">{sub}</span>}
      </div>
    </div>
  );
}
