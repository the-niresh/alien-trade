import { motion } from "framer-motion";

type Tone = "positive" | "negative" | "neutral" | "warn";

const TONE_COLOR: Record<Tone, string> = {
  positive: "var(--green)",
  negative: "var(--red)",
  neutral:  "var(--text)",
  warn:     "var(--yellow)",
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
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <motion.div
        className="stat-value"
        style={{ color: TONE_COLOR[tone] }}
        key={animKey ?? value}
        initial={{ scale: 1.06 }}
        animate={{ scale: 1 }}
        transition={{ duration: 0.25 }}
      >
        {value}
      </motion.div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}
