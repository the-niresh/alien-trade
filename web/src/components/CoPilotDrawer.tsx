import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAction, useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

const CHIPS = [
  "What's the current regime?",
  "What was the last trade?",
  "What's my risk state?",
  "Why is the agent flat?",
];

type Props = { isOpen: boolean; onClose: () => void; prefill?: string };

function ThinkingDots() {
  return (
    <div className="flex items-center gap-[5px]">
      {[0, 0.15, 0.3].map((delay, i) => (
        <motion.span
          key={i}
          className="block w-[5px] h-[5px] rounded-full"
          style={{ background: "var(--purple)" }}
          animate={{ opacity: [0.15, 1, 0.15], scale: [0.7, 1.15, 0.7] }}
          transition={{ duration: 1.0, repeat: Infinity, delay, ease: "easeInOut" }}
        />
      ))}
    </div>
  );
}

export function CoPilotDrawer({ isOpen, onClose, prefill = "" }: Props) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastPrefill, setLastPrefill] = useState("");
  const msgs = useQuery(api.copilot.messages, { limit: 40 }) ?? [];
  const addMessage = useMutation(api.copilot.addMessage);
  const ask = useAction(api.copilot.ask);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  if (prefill && prefill !== lastPrefill) {
    setQuestion(prefill);
    setLastPrefill(prefill);
  }

  const send = async (q = question) => {
    const text = q.trim();
    if (!text || loading) return;
    setQuestion("");
    setLoading(true);
    try {
      await addMessage({ role: "user", content: text, sources_json: "[]" });
      const res = await ask({ question: text });
      await addMessage({ role: "assistant", content: res.answer, sources_json: JSON.stringify(res.sources) });
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  };

  return (
    <Sheet open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent
        side="right"
        showCloseButton={false}
        className="w-[420px] max-sm:w-full p-0 flex flex-col gap-0 border-l-0 shadow-none bg-transparent overflow-hidden"
        style={{ background: "transparent" }}
      >
        {/* Outer shell — deep void with purple atmosphere */}
        <div className="absolute inset-0 bg-[#050508]" />

        {/* Ambient glow blob — top left */}
        <div className="absolute -top-16 -left-16 w-56 h-56 rounded-full pointer-events-none"
          style={{
            background: "radial-gradient(circle, rgba(120,40,220,0.18) 0%, transparent 70%)",
            filter: "blur(32px)",
          }}
        />
        {/* Ambient glow blob — bottom right */}
        <div className="absolute -bottom-20 -right-8 w-48 h-48 rounded-full pointer-events-none"
          style={{
            background: "radial-gradient(circle, rgba(80,20,160,0.12) 0%, transparent 70%)",
            filter: "blur(40px)",
          }}
        />

        {/* Subtle vertical grid lines */}
        <div className="absolute inset-0 pointer-events-none opacity-[0.025]"
          style={{
            backgroundImage: "repeating-linear-gradient(90deg, #fff 0px, #fff 1px, transparent 1px, transparent 40px)",
          }}
        />

        {/* Left edge accent bar */}
        <div className="absolute left-0 inset-y-0 w-[1px] pointer-events-none"
          style={{
            background: "linear-gradient(to bottom, transparent 0%, rgba(120,40,220,0.6) 20%, rgba(120,40,220,0.4) 80%, transparent 100%)",
          }}
        />

        {/* Content stack — all relative to sit above the absolute bg */}
        <div className="relative flex flex-col h-full min-h-0">

          {/* ── Header ── */}
          <div className="flex-shrink-0 relative px-5 pt-5 pb-4">
            {/* header bottom border with gradient fade */}
            <div className="absolute bottom-0 left-0 right-0 h-[1px]"
              style={{ background: "linear-gradient(to right, transparent, rgba(120,40,220,0.4) 30%, rgba(120,40,220,0.4) 70%, transparent)" }}
            />

            {/* Title row — stays clear of the close button zone (right-4 = 40px) */}
            <div className="flex items-center gap-3 pr-8">
              {/* Live status indicator */}
              <span className="relative flex-shrink-0 flex h-[9px] w-[9px]">
                <span className="absolute inline-flex h-full w-full rounded-full opacity-50 animate-ping"
                  style={{ background: "var(--purple)" }} />
                <span className="relative inline-flex h-[9px] w-[9px] rounded-full"
                  style={{
                    background: "var(--purple)",
                    boxShadow: "0 0 8px var(--purple), 0 0 20px rgba(120,40,220,0.5)",
                  }}
                />
              </span>

              <span
                className="font-display text-[17px] font-bold tracking-[0.2em] uppercase"
                style={{
                  color: "var(--purple)",
                  textShadow: "0 0 24px rgba(120,40,220,0.7), 0 0 48px rgba(120,40,220,0.3)",
                }}
              >
                Co-Pilot
              </span>
            </div>

            {/* Sub-label row — metadata below title, away from X button */}
            <div className="mt-1.5 pl-[21px] flex items-center gap-2">
              <span className="font-mono text-[9px] tracking-[0.22em] uppercase"
                style={{ color: "rgba(120,40,220,0.45)" }}>
                Neural Link
              </span>
              <span className="font-mono text-[9px]" style={{ color: "rgba(120,40,220,0.25)" }}>·</span>
              <span className="font-mono text-[9px] tracking-[0.16em] uppercase"
                style={{ color: "rgba(120,40,220,0.35)" }}>
                Active
              </span>
            </div>

            {/* Custom close button — flush top-right, styled to theme */}
            <button
              onClick={onClose}
              className="absolute top-4 right-4 flex items-center justify-center w-7 h-7 rounded-md transition-all cursor-pointer"
              style={{
                background: "rgba(120,40,220,0.08)",
                border: "1px solid rgba(120,40,220,0.2)",
                color: "rgba(120,40,220,0.5)",
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLButtonElement).style.background = "rgba(120,40,220,0.18)";
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(180,80,255,0.9)";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLButtonElement).style.background = "rgba(120,40,220,0.08)";
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(120,40,220,0.5)";
              }}
              aria-label="Close co-pilot"
            >
              <X size={13} />
            </button>
          </div>

          {/* ── Quick chips ── */}
          <div className="flex-shrink-0 flex flex-wrap gap-1.5 px-4 pt-3 pb-2">
            {CHIPS.map((c) => (
              <button
                key={c}
                onClick={() => { send(c); }}
                className="group flex items-center gap-1.5 font-mono text-[9px] tracking-[0.06em] px-2.5 py-[5px] rounded-[5px] transition-all cursor-pointer"
                style={{
                  background: "rgba(120,40,220,0.05)",
                  border: "1px solid rgba(120,40,220,0.18)",
                  color: "rgba(180,120,255,0.55)",
                }}
                onMouseEnter={e => {
                  const el = e.currentTarget as HTMLButtonElement;
                  el.style.background = "rgba(120,40,220,0.14)";
                  el.style.borderColor = "rgba(120,40,220,0.45)";
                  el.style.color = "rgba(200,150,255,0.9)";
                  el.style.boxShadow = "0 0 10px rgba(120,40,220,0.15)";
                }}
                onMouseLeave={e => {
                  const el = e.currentTarget as HTMLButtonElement;
                  el.style.background = "rgba(120,40,220,0.05)";
                  el.style.borderColor = "rgba(120,40,220,0.18)";
                  el.style.color = "rgba(180,120,255,0.55)";
                  el.style.boxShadow = "none";
                }}
              >
                <span style={{ color: "rgba(120,40,220,0.4)" }}>›</span>
                {c}
              </button>
            ))}
          </div>

          {/* Divider */}
          <div className="flex-shrink-0 mx-4 h-[1px]"
            style={{ background: "linear-gradient(to right, transparent, rgba(120,40,220,0.15) 50%, transparent)" }}
          />

          {/* ── Messages ── */}
          <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4 min-h-0"
            style={{ scrollbarWidth: "thin", scrollbarColor: "rgba(120,40,220,0.2) transparent" }}>

            {msgs.length === 0 && (
              <div className="flex flex-col items-center justify-center flex-1 gap-4 py-16 text-center select-none">
                {/* Orbital ring */}
                <div className="relative flex items-center justify-center">
                  <motion.div
                    className="w-14 h-14 rounded-full"
                    style={{ border: "1px solid rgba(120,40,220,0.3)" }}
                    animate={{ rotate: 360 }}
                    transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
                  >
                    <span className="absolute -top-[3px] left-1/2 -translate-x-1/2 w-[5px] h-[5px] rounded-full"
                      style={{ background: "var(--purple)", boxShadow: "0 0 6px var(--purple)" }} />
                  </motion.div>
                  <div className="absolute w-6 h-6 rounded-full"
                    style={{ background: "radial-gradient(circle, rgba(120,40,220,0.5), rgba(80,20,160,0.2))" }} />
                </div>
                <div className="space-y-1">
                  <p className="font-mono text-[10px] tracking-[0.2em] uppercase"
                    style={{ color: "rgba(120,40,220,0.5)" }}>
                    Neural link ready
                  </p>
                  <p className="text-[12px] leading-relaxed max-w-[200px]"
                    style={{ color: "rgba(255,255,255,0.25)" }}>
                    Ask about regime, last trade, risk state, or anything
                  </p>
                </div>
              </div>
            )}

            <AnimatePresence initial={false}>
              {msgs.map((m) => (
                <motion.div
                  key={m._id}
                  className={cn("flex flex-col gap-1", m.role === "user" ? "items-end" : "items-start")}
                  initial={{ opacity: 0, y: 10, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ type: "spring", stiffness: 420, damping: 32 }}
                >
                  {/* Role label */}
                  <span className="font-mono text-[8px] font-bold tracking-[0.22em] uppercase px-1"
                    style={{ color: m.role === "user" ? "rgba(0,200,220,0.45)" : "rgba(140,60,240,0.5)" }}>
                    {m.role === "user" ? "You" : "Co-Pilot"}
                  </span>

                  {/* Bubble */}
                  <div
                    className={cn(
                      "px-3.5 py-2.5 text-[13px] leading-relaxed max-w-[90%]",
                      m.role === "user"
                        ? "rounded-2xl rounded-br-[4px]"
                        : "rounded-2xl rounded-bl-[4px]",
                    )}
                    style={m.role === "user" ? {
                      background: "rgba(0,200,220,0.06)",
                      border: "1px solid rgba(0,200,220,0.2)",
                      color: "rgba(200,245,255,0.88)",
                      boxShadow: "0 0 20px rgba(0,200,220,0.06), inset 0 1px 0 rgba(0,200,220,0.1)",
                    } : {
                      background: "rgba(120,40,220,0.07)",
                      border: "1px solid rgba(120,40,220,0.2)",
                      color: "rgba(230,220,255,0.82)",
                      boxShadow: "0 0 20px rgba(120,40,220,0.07), inset 0 1px 0 rgba(120,40,220,0.12)",
                    }}
                  >
                    {m.content}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Thinking indicator */}
            {loading && (
              <motion.div
                className="flex flex-col gap-1 items-start"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <span className="font-mono text-[8px] font-bold tracking-[0.22em] uppercase px-1"
                  style={{ color: "rgba(140,60,240,0.5)" }}>
                  Co-Pilot
                </span>
                <div
                  className="px-4 py-3 rounded-2xl rounded-bl-[4px]"
                  style={{
                    background: "rgba(120,40,220,0.07)",
                    border: "1px solid rgba(120,40,220,0.2)",
                    boxShadow: "0 0 20px rgba(120,40,220,0.07)",
                  }}
                >
                  <ThinkingDots />
                </div>
              </motion.div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* ── Input bar ── */}
          <div className="flex-shrink-0"
            style={{ background: "rgba(8,5,15,0.95)", borderTop: "1px solid rgba(120,40,220,0.15)" }}>
            {/* Top gradient accent */}
            <div className="h-[1px]"
              style={{ background: "linear-gradient(to right, transparent, rgba(120,40,220,0.35) 30%, rgba(120,40,220,0.35) 70%, transparent)" }}
            />

            <div className="flex items-center gap-2 px-4 py-3">
              {/* Terminal prompt glyph */}
              <span className="font-mono text-[15px] flex-shrink-0 select-none"
                style={{ color: "rgba(120,40,220,0.45)" }}>
                ›
              </span>

              <input
                ref={inputRef}
                type="text"
                placeholder="Ask anything…"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                disabled={loading}
                className="flex-1 bg-transparent text-[13px] font-mono outline-none border-none min-w-0 placeholder:opacity-25"
                style={{ color: "rgba(230,220,255,0.85)", caretColor: "var(--purple)" }}
              />

              <button
                onClick={() => send()}
                disabled={loading || !question.trim()}
                className="flex-shrink-0 font-mono text-[10px] font-bold tracking-[0.18em] uppercase px-3 py-1.5 rounded-[5px] transition-all cursor-pointer disabled:cursor-default"
                style={!loading && question.trim() ? {
                  background: "rgba(120,40,220,0.18)",
                  border: "1px solid rgba(120,40,220,0.45)",
                  color: "rgba(180,100,255,0.95)",
                  boxShadow: "0 0 14px rgba(120,40,220,0.25)",
                } : {
                  background: "rgba(120,40,220,0.05)",
                  border: "1px solid rgba(120,40,220,0.12)",
                  color: "rgba(120,40,220,0.3)",
                }}
              >
                {loading ? "…" : "Ask"}
              </button>
            </div>

            {/* Bottom glow line */}
            <div className="h-[1px]"
              style={{ background: "linear-gradient(to right, transparent, rgba(120,40,220,0.2) 50%, transparent)" }}
            />
          </div>

        </div>
      </SheetContent>
    </Sheet>
  );
}
