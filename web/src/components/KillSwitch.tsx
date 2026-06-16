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

  const deg     = progress * 360;
  const color   = halted ? "var(--green)" : "var(--red)";
  const size    = hero ? "w-[124px] h-[124px]" : "w-11 h-11";
  const inner   = halted ? "bg-[#02140c] text-green" : "bg-[#160510] text-red";
  const textSz  = hero ? "text-base font-black tracking-[0.12em]" : "text-[8px] font-black tracking-wide";
  const holding = progress > 0;

  return (
    <div className={cn("relative flex items-center justify-center flex-shrink-0", size)}>
      {/* concentric pulse rings — hero, idle (armed) only */}
      {hero && !halted && !holding && (
        <>
          <span className="kill-ring" />
          <span className="kill-ring" style={{ animationDelay: "1.2s" }} />
        </>
      )}

      <motion.button
        className={cn(
          "kill-switch rounded-full border-none cursor-pointer p-[3px] flex items-center justify-center w-full h-full relative z-10",
        )}
        style={{ background: `conic-gradient(${color} ${deg}deg, var(--border) ${deg}deg)` }}
        onMouseDown={startHold}
        onMouseUp={stopHold}
        onMouseLeave={stopHold}
        onTouchStart={(e) => { e.preventDefault(); startHold(); }}
        onTouchEnd={stopHold}
        animate={!halted && !holding
          ? { boxShadow: ["0 0 0px #ff2d6e00", "0 0 18px #ff2d6e55", "0 0 0px #ff2d6e00"] }
          : { boxShadow: holding ? `0 0 22px ${color}` : "0 0 0px transparent" }}
        transition={{ duration: 2, repeat: holding ? 0 : Infinity }}
        title={halted ? "Hold to resume trading" : "Hold to halt trading"}
        aria-label={halted ? "Resume trading" : "Halt all trading"}
      >
        <span className={cn(
          "kill-switch__inner w-full h-full rounded-full flex flex-col items-center justify-center gap-0.5",
          inner, textSz,
        )}>
          {hero && !holding && (
            <span className="text-[9px] font-mono tracking-[0.2em] opacity-60">
              {halted ? "SYSTEM" : "EMERGENCY"}
            </span>
          )}
          <span>{holding ? `${Math.round(progress * 100)}%` : halted ? "RESUME" : "KILL"}</span>
        </span>
      </motion.button>
    </div>
  );
}
