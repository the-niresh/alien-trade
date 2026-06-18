import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAction, useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import type { Id } from "../../../convex/_generated/dataModel";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { withToken } from "@/lib/control";
import { Plus, X } from "lucide-react";

const CHIPS = [
  "What's the current regime?",
  "What was the last trade?",
  "What's my risk state?",
  "Why is the agent flat?",
];

type MsgDoc = {
  _id: string;
  role: "user" | "assistant";
  content: string;
  partial_content?: string;
  is_streaming?: boolean;
  ts_ms: number;
};

type ThreadDoc = { _id: string; title: string };

type Props = { isOpen: boolean; onClose: () => void; prefill?: string };

function ThinkingDots() {
  return (
    <div className="flex items-center gap-[5px]">
      {[0, 0.15, 0.3].map((delay, i) => (
        <motion.span key={i} className="block w-[5px] h-[5px] rounded-full"
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
  const [loading, setLoading]   = useState(false);
  const [lastPrefill, setLastPrefill] = useState("");
  const [activeThreadId, setActiveThreadId] = useState<Id<"copilot_threads"> | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const threads      = useQuery(api.copilot.threads) ?? [];
  const flatMsgs     = useQuery(api.copilot.messages, { limit: 40 }) ?? [];
  const threadMsgs   = useQuery(
    api.copilot.threadMessages,
    activeThreadId ? { thread_id: activeThreadId } : "skip",
  ) ?? [];
  const msgs: MsgDoc[] = (activeThreadId ? threadMsgs : flatMsgs) as MsgDoc[];

  const addMessage     = useMutation(api.copilot.addMessage);
  const createThread   = useMutation(api.copilot.createThread);
  const deleteThread   = useMutation(api.copilot.deleteThread);
  const startStream    = useMutation(api.copilot.startStreamingMessage);
  const finaliseStream = useMutation(api.copilot.finaliseStream);
  const ask            = useAction(api.copilot.ask);

  if (prefill && prefill !== lastPrefill) {
    setQuestion(prefill);
    setLastPrefill(prefill);
  }

  const newThread = async () => {
    const id = await createThread(withToken({ title: "New conversation" }));
    setActiveThreadId(id);
  };

  const handleDeleteThread = async (id: Id<"copilot_threads">) => {
    if (activeThreadId === id) setActiveThreadId(null);
    await deleteThread(withToken({ id }));
  };

  const send = async (q = question) => {
    const text = q.trim();
    if (!text || loading) return;
    setQuestion("");
    setLoading(true);
    try {
      await addMessage(withToken({ role: "user", content: text, sources_json: "[]", thread_id: activeThreadId ?? undefined }));
      // Start streaming assistant message
      const streamId = await startStream(withToken({ thread_id: activeThreadId ?? undefined }));
      const res = await ask(withToken({ question: text }));
      await finaliseStream(withToken({ id: streamId, content: res.answer, sources_json: JSON.stringify(res.sources) }));
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  };

  return (
    <Sheet open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent side="right" showCloseButton={false}
        className="w-[720px] max-sm:w-full p-0 flex flex-col gap-0 border-l-0 shadow-none bg-transparent overflow-hidden">
        <div className="absolute inset-0 bg-[#050508]" />
        <div className="absolute -top-16 -left-16 w-56 h-56 rounded-full pointer-events-none"
          style={{ background: "radial-gradient(circle, rgba(120,40,220,0.18) 0%, transparent 70%)", filter: "blur(32px)" }} />

        <div className="relative flex h-full">
          {/* Thread sidebar */}
          <div className={cn(
            "w-[140px] border-r border-border/40 flex flex-col flex-shrink-0 overflow-hidden transition-all",
            "max-sm:absolute max-sm:inset-y-0 max-sm:left-0 max-sm:z-20 max-sm:w-[200px] max-sm:bg-[#050508]",
            !sidebarOpen && "max-sm:hidden",
          )}>
            <div className="flex items-center justify-between px-3 py-2.5 border-b border-border/40">
              <span className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Threads</span>
              <button onClick={newThread}
                className="w-5 h-5 rounded flex items-center justify-center text-muted-fg hover:text-text hover:bg-elevated transition-colors cursor-pointer">
                <Plus className="w-3 h-3" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto py-1">
              <button
                onClick={() => setActiveThreadId(null)}
                className={cn(
                  "w-full text-left px-3 py-2 font-mono text-[11px] truncate cursor-pointer transition-colors",
                  activeThreadId === null ? "text-purple bg-purple/10" : "text-muted-fg hover:text-text hover:bg-elevated/50",
                )}>
                Default
              </button>
              {(threads as ThreadDoc[]).map((t) => (
                <div
                  key={t._id}
                  className={cn(
                    "group relative w-full flex items-center transition-colors",
                    activeThreadId === t._id ? "text-purple bg-purple/10" : "text-muted-fg hover:text-text hover:bg-elevated/50",
                  )}
                >
                  <button
                    onClick={() => setActiveThreadId(t._id as Id<"copilot_threads">)}
                    className="flex-1 text-left px-3 py-2 font-mono text-[11px] truncate cursor-pointer"
                  >
                    {t.title}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteThread(t._id as Id<"copilot_threads">);
                    }}
                    className="opacity-0 group-hover:opacity-100 flex-shrink-0 w-6 h-6 flex items-center justify-center text-muted-fg hover:text-red transition-all cursor-pointer mr-1"
                    aria-label="Delete thread"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Main chat area */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border/40">
              <div className="flex items-center gap-2">
                {/* Mobile sidebar toggle */}
                <button
                  onClick={() => setSidebarOpen((v) => !v)}
                  className="sm:hidden w-6 h-6 flex items-center justify-center text-muted-fg hover:text-text transition-colors cursor-pointer mr-1"
                  aria-label="Toggle threads"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
                <div className="w-2 h-2 rounded-full bg-purple" style={{ boxShadow: "0 0 8px var(--purple)" }} />
                <span className="font-display text-[14px] font-bold text-text">Co-Pilot</span>
              </div>
              <button onClick={onClose}
                className="w-7 h-7 rounded flex items-center justify-center text-muted-fg hover:text-text hover:bg-elevated transition-colors cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
              <AnimatePresence initial={false}>
                {msgs.map((m) => {
                  const displayText = m.is_streaming ? (m.partial_content ?? "") : m.content;
                  return (
                    <motion.div
                      key={m._id}
                      className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ type: "spring", stiffness: 420, damping: 32 }}
                    >
                      <div className={cn(
                        "max-w-[85%] rounded-xl px-3 py-2 font-mono text-[12px] leading-relaxed",
                        m.role === "user"
                          ? "bg-purple/15 text-text border border-purple/20"
                          : "bg-elevated text-text/90 border border-border/60",
                      )}>
                        {m.is_streaming && !displayText ? <ThinkingDots /> : displayText}
                        {m.is_streaming && displayText && (
                          <span className="inline-block w-[2px] h-[12px] bg-purple ml-0.5 animate-pulse" />
                        )}
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
              {loading && !msgs.some((m) => m.is_streaming) && (
                <div className="flex justify-start">
                  <div className="bg-elevated border border-border/60 rounded-xl px-3 py-2">
                    <ThinkingDots />
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Chips + Input */}
            <div className="px-4 py-3 border-t border-border/40 space-y-2">
              {msgs.length === 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {CHIPS.map((chip) => (
                    <button key={chip} onClick={() => send(chip)}
                      className="font-mono text-[10px] text-purple/80 border border-purple/20 rounded-full px-2.5 py-1 hover:bg-purple/10 transition-colors cursor-pointer">
                      {chip}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <input
                  className="flex-1 bg-bg border border-border/60 rounded-lg px-3 py-2 font-mono text-[12px] text-text placeholder:text-muted-fg focus:outline-none focus:border-purple/50"
                  placeholder="Ask the agent…"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                  disabled={loading}
                />
                <Button size="sm"
                  className="bg-purple text-white font-bold hover:bg-purple/80 cursor-pointer px-3"
                  onClick={() => send()} disabled={!question.trim() || loading}>
                  →
                </Button>
              </div>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
