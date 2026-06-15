import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type Tone = "positive" | "negative" | "neutral" | "warn";

const TONE_CLASS: Record<Tone, string> = {
  positive: "text-green",
  negative: "text-red",
  neutral:  "text-text",
  warn:     "text-yellow",
};

type Props = {
  label: string;
  value: string;
  tone?: Tone;
  sub?: string;
  animKey?: string | number;
};

export function StatCard({ label, value, tone = "neutral", sub, animKey }: Props) {
  return (
    <div className="bg-surface border border-border rounded-[14px] p-4">
      <div className="text-[11px] uppercase tracking-[0.6px] text-muted-fg mb-2">{label}</div>
      <motion.div
        className={cn("font-grotesk text-[26px] font-bold leading-none", TONE_CLASS[tone])}
        key={animKey ?? value}
        initial={{ scale: 1.06 }}
        animate={{ scale: 1 }}
        transition={{ duration: 0.25 }}
      >
        {value}
      </motion.div>
      {sub && <div className="text-[12px] text-muted-fg mt-1.5">{sub}</div>}
    </div>
  );
}
