import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAction, useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import type { Id } from "../../../convex/_generated/dataModel";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { withToken } from "@/lib/control";
import { Check, Plus, X } from "lucide-react";
import { parseIntent, dispatchAction, type ProposedAction } from "@/lib/concierge";

const QUICK_ACTIONS = [
  { id: "spawn",       emoji: "🤖", label: "Spawn a new agent",   sub: "Set up a new focused co-pilot" },
  { id: "configure",   emoji: "⚙️", label: "Configure strategy",   sub: "Tune risk params or strategy" },
  { id: "performance", emoji: "📊", label: "Check performance",    sub: "Ask about PnL, drawdown, trades" },
  { id: "custom",      emoji: "➕", label: "Type my own…",         sub: null },
] as const;
type QuickActionId = typeof QUICK_ACTIONS[number]["id"];

type MsgDoc = {
  _id: string;
  role: "user" | "assistant";
  content: string;
  partial_content?: string;
  is_streaming?: boolean;
  ts_ms: number;
};

type ThreadDoc = { _id: string; title: string };

type Props = {
  isOpen: boolean;
  onClose: () => void;
  prefill?: string;
  initialThreadId?: Id<"copilot_threads">;
};

function ActionConfirmCard({
  action, onConfirm, onCancel, loading, withdrawStep,
}: {
  action: ProposedAction;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
  withdrawStep: boolean;
}) {
  const isWithdraw = action.type === "withdraw";
  const destAddress = isWithdraw ? (action as Extract<ProposedAction, { type: "withdraw" }>).params.to_address : null;

  return (
    <div className="rounded-xl border border-yellow/30 bg-yellow/5 px-4 py-3 space-y-2.5">
      <div className="flex items-start gap-2">
        <span className="text-yellow text-[11px] font-mono font-bold uppercase tracking-widest mt-0.5">Action</span>
        <p className="font-mono text-[12px] text-text leading-relaxed flex-1">
          {withdrawStep && destAddress
            ? <>Sending to: <span className="text-yellow font-bold break-all">{destAddress}</span><br />Confirm address is correct.</>
            : action.summary}
        </p>
      </div>
      <div className="flex gap-2">
        <button onClick={onConfirm} disabled={loading}
          className="flex-1 flex items-center justify-center gap-1.5 bg-green/15 border border-green/30 text-green font-mono text-[11px] font-bold rounded-lg py-1.5 hover:bg-green/25 transition-colors cursor-pointer disabled:opacity-50">
          <Check className="w-3.5 h-3.5" />
          {loading ? "Executing…" : withdrawStep ? "Yes, send it" : "Confirm"}
        </button>
        <button onClick={onCancel} disabled={loading}
          className="flex-1 flex items-center justify-center gap-1.5 bg-elevated border border-border text-muted-fg font-mono text-[11px] rounded-lg py-1.5 hover:text-text transition-colors cursor-pointer disabled:opacity-50">
          <X className="w-3.5 h-3.5" />
          Cancel
        </button>
      </div>
    </div>
  );
}

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

export function CoPilotDrawer({ isOpen, onClose, prefill = "", initialThreadId }: Props) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading]   = useState(false);
  const [lastPrefill, setLastPrefill] = useState("");
  const [activeThreadId, setActiveThreadId] = useState<Id<"copilot_threads"> | null>(
    initialThreadId ?? null
  );
  const [pendingAction, setPendingAction] = useState<ProposedAction | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [withdrawConfirmStep, setWithdrawConfirmStep] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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
  const setStrategy    = useMutation(api.config.setStrategy);
  const updateLimits   = useMutation(api.config.updateLimits);
  const setAutopilot   = useMutation(api.config.setAutopilot);
  const setHalted      = useMutation(api.config.setHalted);
  const setControl     = useMutation(api.agentControl.set);
  const recordFeedback = useMutation(api.feedback.record);
  const enqueueCommand = useMutation(api.agentCommands.enqueue);

  // Spawn state machine
  type SpawnStep = "idle" | "awaiting_task" | "awaiting_name";
  const [spawnStep, setSpawnStep]        = useState<SpawnStep>("idle");
  const [spawnTaskSummary, setSpawnTask] = useState("");
  const createAgent = useMutation(api.spawnedAgents.create);

  // Sync initialThreadId prop changes
  useEffect(() => {
    if (initialThreadId) setActiveThreadId(initialThreadId);
  }, [initialThreadId]);

  // Reset spawn state on close; focus input on open
  useEffect(() => {
    if (!isOpen) {
      setSpawnStep("idle");
      setSpawnTask("");
    } else {
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [isOpen]);

  // Auto-scroll to bottom whenever messages change (streaming updates included)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

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

  const confirmAction = async () => {
    if (!pendingAction || actionLoading) return;
    if (pendingAction.type === "withdraw" && !withdrawConfirmStep) {
      setWithdrawConfirmStep(true);
      return;
    }
    setActionLoading(true);
    try {
      await dispatchAction(pendingAction, {
        setStrategy,
        updateLimits,
        setAutopilot,
        setHalted,
        setControl: (a) => setControl(a as Parameters<typeof setControl>[0]),
        recordFeedback,
        enqueueCommand,
        onDepositInfo: () => { setPendingAction(null); /* DepositView handled separately */ },
      });
      await addMessage(withToken({ role: "assistant", content: `✅ Done: ${pendingAction.summary}`, sources_json: "[]", thread_id: activeThreadId ?? undefined }));
      setPendingAction(null);
      setWithdrawConfirmStep(false);
    } catch (e) {
      setWithdrawConfirmStep(false);
      await addMessage(withToken({ role: "assistant", content: `❌ Action failed: ${String(e)}`, sources_json: "[]", thread_id: activeThreadId ?? undefined }));
    } finally {
      setActionLoading(false);
    }
  };

  const handleQuickAction = (id: QuickActionId) => {
    if (id === "spawn") {
      // Start spawn flow — inject a Co-Pilot message asking for the task
      void addMessage(withToken({
        role: "assistant",
        content: "Sure! What should this agent focus on? Describe its job in one or two sentences.",
        sources_json: "[]",
        thread_id: activeThreadId ?? undefined,
      }));
      setSpawnStep("awaiting_task");
    } else if (id === "custom") {
      inputRef.current?.focus();
    } else {
      const prefills: Record<string, string> = {
        configure:   "Help me configure the strategy and risk parameters.",
        performance: "How is the agent performing? Show me PnL and drawdown.",
      };
      setQuestion(prefills[id] ?? "");
      inputRef.current?.focus();
    }
  };

  const send = async (q = question) => {
    const text = q.trim();
    if (!text || loading) return;
    setQuestion("");

    // ── Spawn state machine ────────────────────────────────────
    if (spawnStep === "awaiting_task") {
      setSpawnTask(text);
      await addMessage(withToken({ role: "user", content: text, sources_json: "[]", thread_id: activeThreadId ?? undefined }));
      await addMessage(withToken({
        role: "assistant",
        content: "Got it. What should I call this agent?",
        sources_json: "[]",
        thread_id: activeThreadId ?? undefined,
      }));
      setSpawnStep("awaiting_name");
      return;
    }

    if (spawnStep === "awaiting_name") {
      const name = text;
      await addMessage(withToken({ role: "user", content: name, sources_json: "[]", thread_id: activeThreadId ?? undefined }));
      // Create the agent record
      await createAgent({
        name,
        task_summary: spawnTaskSummary,
        thread_id: activeThreadId ?? undefined,
      });
      await addMessage(withToken({
        role: "assistant",
        content: `✅ **${name}** is live. I'll work on: "${spawnTaskSummary}". You can find this agent in the Agents tab and your sidebar.`,
        sources_json: "[]",
        thread_id: activeThreadId ?? undefined,
      }));
      setSpawnStep("idle");
      setSpawnTask("");
      return;
    }
    // ── End spawn state machine ────────────────────────────────

    setLoading(true);
    try {
      const intent = parseIntent(text);
      if (intent && intent.type !== "deposit_info") {
        await addMessage(withToken({ role: "user", content: text, sources_json: "[]", thread_id: activeThreadId ?? undefined }));
        setPendingAction(intent);
        setLoading(false);
        return;
      }
      await addMessage(withToken({ role: "user", content: text, sources_json: "[]", thread_id: activeThreadId ?? undefined }));
      // Start streaming assistant message
      const streamId = await startStream(withToken({ thread_id: activeThreadId ?? undefined }));
      const res = await ask(withToken({ question: text }));
      await finaliseStream(withToken({ id: streamId, content: res.answer, sources_json: JSON.stringify(res.sources) }));
      // If agent returned a structured action, surface the confirm card
      if (res.action && !pendingAction) {
        setPendingAction(res.action as ProposedAction);
      }
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

        <div className="relative flex flex-col h-full">
          {/* Horizontal thread tab bar */}
          <div className="flex items-center border-b border-border/40 flex-shrink-0 overflow-x-auto"
            style={{ scrollbarWidth: "none" }}>

            {/* Brand dot + label (non-clickable, always visible) */}
            <div className="flex items-center gap-1.5 px-3 flex-shrink-0 border-r border-border/40 h-10">
              <div className="w-2 h-2 rounded-full bg-purple" style={{ boxShadow: "0 0 8px var(--purple)" }} />
              <span className="font-display text-[13px] font-bold text-text whitespace-nowrap">Co-Pilot</span>
            </div>

            {/* Default tab */}
            <button
              onClick={() => setActiveThreadId(null)}
              className={cn(
                "flex-shrink-0 flex items-center h-10 px-3 font-mono text-[11px] border-r border-border/40 transition-colors cursor-pointer whitespace-nowrap relative",
                activeThreadId === null
                  ? "text-purple bg-purple/8"
                  : "text-muted-fg hover:text-text hover:bg-elevated/50",
              )}>
              {activeThreadId === null && (
                <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-purple rounded-t-full" />
              )}
              Default
            </button>

            {/* Named thread tabs */}
            {(threads as ThreadDoc[]).map((t) => (
              <div key={t._id}
                className={cn(
                  "group flex-shrink-0 flex items-center border-r border-border/40 transition-colors h-10 relative",
                  activeThreadId === t._id ? "text-purple bg-purple/8" : "text-muted-fg hover:text-text hover:bg-elevated/50",
                )}>
                {activeThreadId === t._id && (
                  <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-purple rounded-t-full" />
                )}
                <button
                  onClick={() => setActiveThreadId(t._id as Id<"copilot_threads">)}
                  className="pl-3 pr-1 font-mono text-[11px] truncate max-w-[110px] cursor-pointer h-full flex items-center">
                  {t.title}
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteThread(t._id as Id<"copilot_threads">); }}
                  className="opacity-0 group-hover:opacity-100 w-5 h-5 flex items-center justify-center text-muted-fg hover:text-red transition-all cursor-pointer mr-1.5 flex-shrink-0"
                  aria-label="Delete thread">
                  <X className="w-2.5 h-2.5" />
                </button>
              </div>
            ))}

            {/* New thread */}
            <button onClick={newThread}
              className="flex-shrink-0 w-9 h-10 flex items-center justify-center text-muted-fg hover:text-text hover:bg-elevated/50 transition-colors cursor-pointer border-r border-border/40"
              aria-label="New thread">
              <Plus className="w-3.5 h-3.5" />
            </button>

            <div className="flex-1 min-w-0" />

            {/* Close */}
            <button onClick={onClose}
              className="flex-shrink-0 w-10 h-10 flex items-center justify-center text-muted-fg hover:text-text hover:bg-elevated transition-colors cursor-pointer border-l border-border/40"
              aria-label="Close">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Chat area — full width below the tab bar */}
          <div className="flex-1 flex flex-col overflow-hidden">

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
              {pendingAction && (
                <ActionConfirmCard
                  action={pendingAction}
                  onConfirm={confirmAction}
                  onCancel={() => { setPendingAction(null); setWithdrawConfirmStep(false); }}
                  loading={actionLoading}
                  withdrawStep={withdrawConfirmStep}
                />
              )}
              <div ref={bottomRef} />
            </div>

            {/* Chips + Input */}
            <div className="px-4 py-3 border-t border-border/40 space-y-2">
              {msgs.length === 0 && !pendingAction && spawnStep === "idle" && (
                <div className="space-y-1.5 mb-2">
                  {QUICK_ACTIONS.map((card) => (
                    <button
                      key={card.id}
                      onClick={() => handleQuickAction(card.id)}
                      className="w-full text-left border border-border/60 rounded-xl px-3 py-2.5 hover:bg-elevated/70 hover:border-border transition-colors cursor-pointer group"
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="text-[16px]">{card.emoji}</span>
                        <div>
                          <p className="font-mono text-[12px] text-text font-bold">{card.label}</p>
                          {card.sub && <p className="font-mono text-[10px] text-muted-fg mt-0.5">{card.sub}</p>}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  className="flex-1 bg-bg border border-border/60 rounded-lg px-3 py-2 font-mono text-[12px] text-text placeholder:text-muted-fg focus:outline-none focus:border-purple/50"
                  placeholder="Ask the agent… (⌃↵ to send)"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (!e.shiftKey || e.ctrlKey || e.metaKey)) {
                      e.preventDefault();
                      send();
                    }
                  }}
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

