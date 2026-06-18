import { motion } from "framer-motion";
import { Bot } from "lucide-react";
import { Button } from "@/components/ui/button";

type Props = { onStart: () => void };

export function StartTradingCTA({ onStart }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="panel rounded-2xl border border-border p-6 flex flex-col items-center gap-4 text-center"
      style={{ background: "radial-gradient(ellipse at 50% 0%, rgba(52,255,174,0.06) 0%, transparent 70%)" }}
    >
      <div
        className="w-12 h-12 rounded-2xl bg-green/10 border border-green/20 flex items-center justify-center"
        style={{ boxShadow: "0 0 24px rgba(52,255,174,0.15)" }}
      >
        <Bot className="w-6 h-6 text-green" />
      </div>
      <div>
        <h2 className="font-display text-[18px] font-bold text-text mb-1">
          Autonomous AI Trading Agent
        </h2>
        <p className="font-mono text-[12px] text-muted-fg max-w-xs leading-relaxed">
          Your agent is live and watching the market. Configure strategy, set risk limits, and track trades — all through the Co-Pilot.
        </p>
      </div>
      <Button
        onClick={onStart}
        className="bg-green text-[#04140c] font-bold px-6 py-2.5 h-auto hover:bg-green/80 cursor-pointer flex items-center gap-2"
      >
        <Bot className="w-4 h-4" />
        Start Trading with AI
      </Button>
    </motion.div>
  );
}
