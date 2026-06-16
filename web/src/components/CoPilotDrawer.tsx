import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAction, useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const CHIPS = [
  "What's the current regime?",
  "What was the last trade?",
  "What's my risk state?",
  "Why is the agent flat?",
];

type Props = { isOpen: boolean; onClose: () => void; prefill?: string };

export function CoPilotDrawer({ isOpen, onClose, prefill = "" }: Props) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastPrefill, setLastPrefill] = useState("");
  const msgs = useQuery(api.copilot.messages, { limit: 40 }) ?? [];
  const addMessage = useMutation(api.copilot.addMessage);
  const ask = useAction(api.copilot.ask);
  const bottomRef = useRef<HTMLDivElement>(null);

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
        className="w-[420px] max-sm:w-full bg-surface border-l border-border p-0 flex flex-col gap-0"
      >
        <SheetHeader className="px-5 py-4 border-b border-border chrome">
          <SheetTitle className="font-display text-[16px] font-bold text-purple tracking-wide flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-purple" style={{ boxShadow: "0 0 8px var(--purple)" }} />
            Co-Pilot
          </SheetTitle>
        </SheetHeader>

        {/* Quick chips */}
        <div className="flex gap-1.5 px-5 pt-3 pb-0 flex-wrap">
          {CHIPS.map((c) => (
            <button key={c}
              className="bg-elevated border border-border rounded-full px-3 py-1 text-[12px] text-muted-fg hover:text-text hover:border-border-hi transition-colors"
              onClick={() => send(c)}
            >{c}</button>
          ))}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-2.5">
          {msgs.length === 0 && (
            <p className="text-muted-fg text-[13px] italic py-2">Ask anything — regime, last trade, risk state…</p>
          )}
          <AnimatePresence initial={false}>
            {msgs.map((m) => (
              <motion.div key={m._id}
                className={`px-3.5 py-2.5 rounded-xl text-[13px] leading-relaxed max-w-[92%] ${
                  m.role === "user"
                    ? "bg-cyan/5 border border-cyan/15 self-end"
                    : "bg-elevated border border-border self-start"
                }`}
                initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
              >
                <div className={`text-[10px] font-bold mb-1 ${m.role === "user" ? "text-cyan" : "text-purple"}`}>
                  {m.role === "user" ? "You" : "CoPilot"}
                </div>
                <div>{m.content}</div>
              </motion.div>
            ))}
          </AnimatePresence>
          {loading && (
            <motion.div className="bg-elevated border border-border rounded-xl px-3.5 py-2.5 self-start text-[13px]"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <div className="text-[10px] font-bold text-purple mb-1">CoPilot</div>
              <motion.span animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 1.2, repeat: Infinity }}>
                thinking…
              </motion.span>
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input row */}
        <div className="flex gap-2 px-5 py-3 border-t border-border">
          <Input
            placeholder="Ask the co-pilot…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            disabled={loading}
            className="flex-1 bg-bg border-border text-text text-[13px] focus-visible:ring-purple"
          />
          <Button size="sm"
            className="bg-purple text-white font-bold hover:bg-purple/80 cursor-pointer"
            onClick={() => send()}
            disabled={loading || !question.trim()}
          >{loading ? "…" : "Ask"}</Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
