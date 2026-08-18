import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Send, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { GUIDE_ANSWERS, GUIDE_FALLBACK, GUIDE_INTRO, matchGuideAnswer } from "@/lib/guide";

/**
 * The chat a visitor gets.
 *
 * The real Co-Pilot needs the operator's control token and spends credits per
 * question, so it cannot be handed to anonymous visitors. This is the same
 * affordance - a chat you type into - backed by fixed local answers. It says so at
 * the top rather than implying a model is replying.
 */

type Turn = { role: "guide" | "you"; text: string; goTo?: string };

export function VisitorGuide({
  isOpen,
  onClose,
  onNavigate,
}: {
  isOpen: boolean;
  onClose: () => void;
  onNavigate?: (view: string) => void;
}) {
  const [turns, setTurns] = useState<Turn[]>([{ role: "guide", text: GUIDE_INTRO }]);
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, isOpen]);

  useEffect(() => {
    if (isOpen) inputRef.current?.focus();
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  const ask = (text: string) => {
    const q = text.trim();
    if (!q) return;
    const hit = matchGuideAnswer(q);
    setTurns((prev) => [
      ...prev,
      { role: "you", text: q },
      { role: "guide", text: hit?.answer ?? GUIDE_FALLBACK, goTo: hit?.goTo },
    ]);
    setInput("");
  };

  // Chips for questions not yet asked, so the list shrinks as they explore.
  const asked = new Set(turns.filter((t) => t.role === "you").map((t) => t.text.toLowerCase()));
  const remaining = GUIDE_ANSWERS.filter((a) => !asked.has(a.question.toLowerCase()));

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-40"
          />
          <motion.aside
            role="dialog"
            aria-label="Visitor guide"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 320, damping: 34 }}
            className="fixed right-0 top-0 h-full w-[420px] max-sm:w-full z-50 flex flex-col chrome border-l border-border"
          >
            <header className="flex items-start gap-3 px-5 py-4 border-b border-border">
              <div className="w-8 h-8 rounded-lg bg-cyan/10 border border-cyan/30 grid place-items-center flex-shrink-0">
                <Sparkles className="w-4 h-4 text-cyan" />
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="font-display text-[14px] font-bold text-text leading-tight">
                  Guide
                </h2>
                <p className="font-mono text-[10px] text-muted-fg mt-0.5">
                  fixed answers · no token needed
                </p>
              </div>
              <button
                onClick={onClose}
                aria-label="Close guide"
                className="text-muted-fg hover:text-text transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </header>

            <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-3">
              {turns.map((t, i) => (
                <div
                  key={i}
                  className={
                    t.role === "you"
                      ? "self-end max-w-[85%] rounded-xl rounded-br-sm bg-green/12 border border-green/25 px-3.5 py-2.5"
                      : "self-start max-w-[92%] rounded-xl rounded-bl-sm bg-elevated border border-border px-3.5 py-2.5"
                  }
                >
                  <p className="text-[13px] text-text/90 leading-relaxed whitespace-pre-line">
                    {t.text}
                  </p>
                  {t.goTo && onNavigate && (
                    <button
                      onClick={() => { onNavigate(t.goTo!); onClose(); }}
                      className="mt-2.5 inline-flex items-center gap-1 font-mono text-[11px] text-cyan hover:underline underline-offset-4 cursor-pointer"
                    >
                      Take me to {t.goTo} <ArrowRight className="w-3 h-3" />
                    </button>
                  )}
                </div>
              ))}
              <div ref={endRef} />
            </div>

            {remaining.length > 0 && (
              <div className="px-5 pb-3 flex flex-wrap gap-1.5 border-t border-border pt-3">
                {remaining.slice(0, 4).map((a) => (
                  <button
                    key={a.question}
                    onClick={() => ask(a.question)}
                    className="text-[11.5px] text-muted-fg hover:text-text border border-border hover:border-cyan/40 rounded-full px-2.5 py-1 transition-colors cursor-pointer text-left"
                  >
                    {a.question}
                  </button>
                ))}
              </div>
            )}

            <div className="px-5 py-3 border-t border-border flex gap-2">
              <Input
                ref={inputRef}
                value={input}
                placeholder="Ask about this project…"
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") ask(input); }}
                className="flex-1 bg-bg border-border text-text text-[13px] focus-visible:ring-cyan"
              />
              <Button
                onClick={() => ask(input)}
                disabled={!input.trim()}
                aria-label="Send"
                className="bg-cyan/15 border border-cyan/30 text-cyan hover:bg-cyan/25 cursor-pointer disabled:opacity-40"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
