import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type Props = {
  halted: boolean;
  onToggle: () => void;
  hero?: boolean;
};

const HOLD_MS = 1500;
const TICK_MS = 50;

export function KillSwitch({ halted, onToggle, hero = false }: Props) {
  const [progress, setProgress] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startHold = () => {
    if (timerRef.current) return;
    let elapsed = 0;
    timerRef.current = setInterval(() => {
      elapsed += TICK_MS;
      const p = Math.min(elapsed / HOLD_MS, 1);
      setProgress(p);
      if (p >= 1) { stopHold(); onToggle(); }
    }, TICK_MS);
  };

  const stopHold = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setProgress(0);
  };

  const deg   = progress * 360;
  const color = halted ? "var(--green)" : "var(--red)";
  const size  = hero ? "w-[120px] h-[120px]" : "w-11 h-11";
  const inner = halted ? "bg-[#01120a] text-green" : "bg-[#12040a] text-red";
  const textSz = hero ? "text-sm font-black tracking-wider" : "text-[8px] font-black tracking-wide";

  return (
    <motion.button
      className={cn(
        "kill-switch rounded-full border-none cursor-pointer p-[3px] flex items-center justify-center flex-shrink-0",
        size
      )}
      style={{ background: `conic-gradient(${color} ${deg}deg, var(--border) ${deg}deg)` }}
      onMouseDown={startHold}
      onMouseUp={stopHold}
      onMouseLeave={stopHold}
      onTouchStart={(e) => { e.preventDefault(); startHold(); }}
      onTouchEnd={stopHold}
      animate={!halted && progress === 0
        ? { boxShadow: ["0 0 0px #ff306000", "0 0 14px #ff306050", "0 0 0px #ff306000"] }
        : {}}
      transition={{ duration: 2, repeat: Infinity }}
      title={halted ? "Hold to resume trading" : "Hold to halt trading"}
    >
      <span className={cn(
        "kill-switch__inner w-full h-full rounded-full flex items-center justify-center",
        inner, textSz
      )}>
        {progress > 0 ? `${Math.round(progress * 100)}%` : halted ? "RESUME" : "KILL"}
      </span>
    </motion.button>
  );
}
