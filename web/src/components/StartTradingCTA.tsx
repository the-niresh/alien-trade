import { motion } from "framer-motion";
import { Bot } from "lucide-react";
import { Button } from "@/components/ui/button";

type Props = { onStart: () => void };

export function StartTradingCTA({ onStart }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="panel rounded-xl border border-border px-4 py-3 flex items-center justify-between gap-4"
      style={{ background: "linear-gradient(90deg, rgba(52,255,174,0.05) 0%, transparent 55%)" }}
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-9 h-9 rounded-xl bg-green/10 border border-green/20 flex items-center justify-center flex-shrink-0">
          <Bot className="w-[18px] h-[18px] text-green" />
        </div>
        <div className="min-w-0">
          <div className="font-mono text-[10px] text-green tracking-[0.18em] uppercase flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-green animate-pulse" /> Agent live
          </div>
          <p className="font-mono text-[12px] text-muted-fg truncate">
            Tune strategy, risk limits and trades through the Co-Pilot.
          </p>
        </div>
      </div>
      <Button
        onClick={onStart}
        className="bg-green text-[#04140c] font-bold px-4 py-2 h-auto hover:bg-green/80 cursor-pointer flex items-center gap-2 flex-shrink-0"
      >
        <Bot className="w-4 h-4" />
        Open Co-Pilot
      </Button>
    </motion.div>
  );
}
