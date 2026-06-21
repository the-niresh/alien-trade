import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { motion, AnimatePresence } from "framer-motion";
import { useAction, useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import type { Id } from "../../../convex/_generated/dataModel";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { withToken } from "@/lib/control";
import { Check, Plus, X } from "lucide-react";
import {
  parseIntent,
  dispatchAction,
  type ProposedAction,
} from "@/lib/concierge";

const SPAWN_STYLES_CONFIG = [
  {
    id: "conservative",
    emoji: "🛡️",
    label: "Conservative",
    desc: "Careful and selective",
    detail: "1.5×ATR stops · max 3% per position · 5% daily loss limit",
    goal: "Protect capital and grow steadily — tight stops, small positions, no chasing",
  },
  {
    id: "balanced",
    emoji: "⚖️",
    label: "Balanced",
    desc: "Patient and stable",
    detail: "2×ATR stops · max 5% per position · momentum-filtered entries",
    goal: "Capture momentum moves with moderate sizing and balanced risk-reward",
  },
  {
    id: "aggressive",
    emoji: "🚀",
    label: "Aggressive",
    desc: "Active and fast",
    detail: "3×ATR stops · max 10% per position · trend-following with full targets",
    goal: "Maximize trend capture — wider stops, larger positions, hold for full moves",
  },
  {
    id: "moonshot",
    emoji: "🌙",
    label: "Moonshot",
    desc: "One big bet, ride to the top",
    detail: "High conviction only · max 15% per position · minimal exits until target",
    goal: "Find the highest-conviction setup and ride it to full target with minimal interference",
  },
] as const;

const SPAWN_NAME_SUGGESTIONS: Record<string, string[]> = {
  conservative: ["Capital Guard", "Safe Start", "Cautious Sniper", "Steady Eddie"],
  balanced: ["Steady Momentum", "Balance Bot", "Mid-Range", "Equilibrium"],
  aggressive: ["Volume Chaser", "Trend Runner", "Momentum Max", "Alpha Hunter"],
  moonshot: ["Moon Hunter", "Alpha Seeker", "Gem Finder", "Diamond Hands"],
};

// Opening line of the guided spawn wizard. Single source of truth — referenced
// by every entry point that starts a spawn (quick-action card, "+ New", picker).
const SPAWN_INTRO =
  "Let's spin up a new agent. It'll trade on your behalf — starting in **paper mode** until you take it live.\n\nWhat style of trader should it be?";

const QUICK_ACTIONS = [
  {
    id: "spawn",
    emoji: "🤖",
    label: "Spawn a new agent",
    sub: "Set up a new focused co-pilot",
  },
  {
    id: "configure",
    emoji: "⚙️",
    label: "Configure strategy",
    sub: "Tune risk params or strategy",
  },
  {
    id: "performance",
    emoji: "📊",
    label: "Check performance",
    sub: "Ask about PnL, drawdown, trades",
  },
  { id: "custom", emoji: "➕", label: "Type my own…", sub: null },
] as const;
type QuickActionId = (typeof QUICK_ACTIONS)[number]["id"];

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
  startSpawn?: boolean;
};

function ActionConfirmCard({
  action,
  onConfirm,
  onCancel,
  loading,
  withdrawStep,
}: {
  action: ProposedAction;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
  withdrawStep: boolean;
}) {
  const isWithdraw = action.type === "withdraw";
  const destAddress = isWithdraw
    ? (action as Extract<ProposedAction, { type: "withdraw" }>).params
        .to_address
    : null;

  return (
    <div className="rounded-xl border border-yellow/30 bg-yellow/5 px-4 py-3 space-y-2.5">
      <div className="flex items-start gap-2">
        <span className="text-yellow text-[11px] font-mono font-bold uppercase tracking-widest mt-0.5">
          Action
        </span>
        <p className="font-mono text-[12px] text-text leading-relaxed flex-1">
          {withdrawStep && destAddress ? (
            <>
              Sending to:{" "}
              <span className="text-yellow font-bold break-all">
                {destAddress}
              </span>
              <br />
              Confirm address is correct.
            </>
          ) : (
            action.summary
          )}
        </p>
      </div>
      <div className="flex gap-2">
        <button
          onClick={onConfirm}
          disabled={loading}
          className="flex-1 flex items-center justify-center gap-1.5 bg-green/15 border border-green/30 text-green font-mono text-[11px] font-bold rounded-lg py-1.5 hover:bg-green/25 transition-colors cursor-pointer disabled:opacity-50"
        >
          <Check className="w-3.5 h-3.5" />
          {loading ? "Executing…" : withdrawStep ? "Yes, send it" : "Confirm"}
        </button>
        <button
          onClick={onCancel}
          disabled={loading}
          className="flex-1 flex items-center justify-center gap-1.5 bg-elevated border border-border text-muted-fg font-mono text-[11px] rounded-lg py-1.5 hover:text-text transition-colors cursor-pointer disabled:opacity-50"
        >
          <X className="w-3.5 h-3.5" />
          Cancel
        </button>
      </div>
    </div>
  );
}

const THINKING_PHASES = [
  "PROCESSING",
  "ANALYZING",
  "REASONING",
  "COMPUTING",
] as const;

function ThinkingIndicator() {
  const [elapsed, setElapsed] = useState(0);
  const phase =
    THINKING_PHASES[
      Math.min(Math.floor(elapsed / 3), THINKING_PHASES.length - 1)
    ];

  useEffect(() => {
    const id = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-2" style={{ minWidth: 172 }}>
      {/* Status label + elapsed timer */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-[6px]">
          <motion.span
            className="block w-[6px] h-[6px] rounded-full flex-shrink-0"
            style={{
              background: "var(--green)",
              boxShadow: "0 0 8px var(--green)",
            }}
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
          />
          <span
            className="font-mono text-[10px] font-bold tracking-[0.18em] uppercase"
            style={{ color: "var(--green)" }}
          >
            {phase}
          </span>
        </div>
        <span
          className="font-mono text-[10px] tabular-nums"
          style={{ color: "var(--muted)" }}
        >
          {elapsed}s
        </span>
      </div>

      {/* Scanning beam bar */}
      <div
        className="relative h-[2px] rounded-full overflow-hidden"
        style={{ background: "oklch(14% 0 0)" }}
      >
        <motion.div
          className="absolute inset-y-0 rounded-full"
          style={{
            width: "38%",
            background:
              "linear-gradient(90deg, transparent, var(--green), var(--cyan), transparent)",
          }}
          animate={{ x: ["-38%", "265%"] }}
          transition={{ duration: 1.7, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>

      {/* Neural activity dots — alternating green / cyan */}
      <div className="flex items-center gap-[5px]">
        {(
          [
            { color: "var(--green)", size: 4, delay: 0 },
            { color: "var(--cyan)", size: 3, delay: 0.18 },
            { color: "var(--green)", size: 5, delay: 0.36 },
            { color: "var(--cyan)", size: 3, delay: 0.54 },
            { color: "var(--green)", size: 4, delay: 0.72 },
          ] as const
        ).map(({ color, size, delay }, i) => (
          <motion.span
            key={i}
            className="block rounded-full"
            style={{ width: size, height: size, background: color }}
            animate={{ opacity: [0.12, 1, 0.12], scale: [0.55, 1.35, 0.55] }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              delay,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>
    </div>
  );
}

// Shared markdown renderers — hoisted so they aren't re-created on every render.
const MARKDOWN_COMPONENTS = {
  h1: ({ children }: { children?: React.ReactNode }) => <p className="text-[13px] font-bold mb-1" style={{ color: "var(--cyan)" }}>{children}</p>,
  h2: ({ children }: { children?: React.ReactNode }) => <p className="text-[12px] font-bold mb-1" style={{ color: "var(--cyan)" }}>{children}</p>,
  h3: ({ children }: { children?: React.ReactNode }) => <p className="text-[11px] font-bold mb-0.5" style={{ color: "var(--green)" }}>{children}</p>,
  strong: ({ children }: { children?: React.ReactNode }) => <strong className="font-bold" style={{ color: "var(--text)" }}>{children}</strong>,
  em: ({ children }: { children?: React.ReactNode }) => <em className="italic" style={{ color: "var(--muted)" }}>{children}</em>,
  hr: () => <hr className="my-2 border-t border-border/50" />,
  ul: ({ children }: { children?: React.ReactNode }) => <ul className="my-1 space-y-0.5 pl-3">{children}</ul>,
  ol: ({ children }: { children?: React.ReactNode }) => <ol className="my-1 space-y-0.5 pl-3 list-decimal">{children}</ol>,
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className="flex items-start gap-1.5">
      <span style={{ color: "var(--green)" }} className="mt-[2px] flex-shrink-0">›</span>
      <span>{children}</span>
    </li>
  ),
  code: ({ children }: { children?: React.ReactNode }) => (
    <code className="px-1 py-0.5 rounded text-[11px]" style={{ background: "oklch(18% 0 0)", color: "var(--cyan)" }}>{children}</code>
  ),
  p: ({ children }: { children?: React.ReactNode }) => <p className="mb-1 last:mb-0">{children}</p>,
};

/**
 * Reveals `target` one steady stream of characters at a time via rAF, decoupling
 * the on-screen text from Convex's network-batched `partial_content` updates.
 * The reveal rate scales with backlog so it never falls far behind a fast stream,
 * but small deltas drip in smoothly instead of snapping.
 */
function useSmoothReveal(target: string, enabled: boolean): string {
  const [display, setDisplay] = useState(enabled ? "" : target);
  const targetRef = useRef(target);
  targetRef.current = target;
  const displayRef = useRef(display);
  displayRef.current = display;
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const stop = () => {
      if (rafRef.current != null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
    if (!enabled) {
      stop();
      setDisplay(targetRef.current);
      return;
    }
    const tick = () => {
      const tgt = targetRef.current;
      const cur = displayRef.current;
      if (cur === tgt) {
        rafRef.current = null; // caught up — stop spinning until target grows again
        return;
      }
      // Target shrank or diverged (final content replaced partial) — snap.
      let next: string;
      if (!tgt.startsWith(cur)) {
        next = tgt;
      } else {
        const backlog = tgt.length - cur.length;
        const step = Math.max(2, Math.round(backlog / 6));
        next = tgt.slice(0, cur.length + step);
      }
      displayRef.current = next;
      setDisplay(next);
      rafRef.current = next === tgt ? null : requestAnimationFrame(tick);
    };
    // Re-running on every `target` change restarts the loop if it had stopped.
    if (rafRef.current == null) rafRef.current = requestAnimationFrame(tick);
    return stop;
  }, [enabled, target]);

  return enabled ? display : target;
}

function MessageContent({
  text,
  role,
  streaming,
}: {
  text: string;
  role: "user" | "assistant";
  streaming: boolean;
}) {
  const display = useSmoothReveal(text, streaming);

  if (streaming && !display) return <ThinkingIndicator />;

  return (
    <>
      {role === "assistant" ? (
        <ReactMarkdown components={MARKDOWN_COMPONENTS}>{display}</ReactMarkdown>
      ) : (
        display
      )}
      {streaming && display && (
        <span
          className="inline-block w-[2px] h-[12px] ml-0.5 animate-pulse"
          style={{ background: "var(--green)" }}
        />
      )}
    </>
  );
}

export function CoPilotDrawer({
  isOpen,
  onClose,
  prefill = "",
  initialThreadId,
  startSpawn = false,
}: Props) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastPrefill, setLastPrefill] = useState("");
  const [activeThreadId, setActiveThreadId] =
    useState<Id<"copilot_threads"> | null>(initialThreadId ?? null);
  const [pendingAction, setPendingAction] = useState<ProposedAction | null>(
    null,
  );
  const [actionLoading, setActionLoading] = useState(false);
  const [withdrawConfirmStep, setWithdrawConfirmStep] = useState(false);
  const [defaultTabHidden, setDefaultTabHidden] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // Whether the view is pinned to the latest message. Flips false when the user
  // scrolls up to read history, so autoscroll never yanks them back down.
  const stickRef = useRef(true);
  const prevMsgCountRef = useRef(0);
  // Guards async state updates (send/stream) against firing after the drawer unmounts.
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const threads = useQuery(api.copilot.threads) ?? [];

  // Once any thread exists, always resolve to a thread — never show Default content.
  // If activeThreadId is null but threads exist, fall back to the first thread.
  // If threads are empty (all deleted), show nothing (empty array).
  const displayThreadId: Id<"copilot_threads"> | null = (() => {
    if (activeThreadId !== null) return activeThreadId;
    if (defaultTabHidden) {
      const first = (threads as ThreadDoc[])[0];
      return first ? (first._id as Id<"copilot_threads">) : null;
    }
    return null;
  })();

  const flatMsgs = useQuery(api.copilot.messages, { limit: 40 }) ?? [];
  const threadMsgs =
    useQuery(
      api.copilot.threadMessages,
      displayThreadId ? { thread_id: displayThreadId } : "skip",
    ) ?? [];
  const msgs: MsgDoc[] = (
    displayThreadId ? threadMsgs : defaultTabHidden ? [] : flatMsgs
  ) as MsgDoc[];

  const spawnedAgents = useQuery(api.spawnedAgents.list) ?? [];
  const addMessage = useMutation(api.copilot.addMessage);
  const createThread = useMutation(api.copilot.createThread);
  const renameThread = useMutation(api.copilot.renameThread);
  const deleteThread = useMutation(api.copilot.deleteThread);
  const startStream = useMutation(api.copilot.startStreamingMessage);
  const askStreaming = useAction(api.copilotNode.askStreaming);
  const setStrategy = useMutation(api.config.setStrategy);
  const updateLimits = useMutation(api.config.updateLimits);
  const setAutopilot = useMutation(api.config.setAutopilot);
  const setHalted = useMutation(api.config.setHalted);
  const setControl = useMutation(api.agentControl.set);
  const recordFeedback = useMutation(api.feedback.record);
  const enqueueCommand = useMutation(api.agentCommands.enqueue);

  // Spawn state machine
  type SpawnStep = "idle" | "awaiting_style" | "awaiting_name";
  const [spawnStep, setSpawnStep] = useState<SpawnStep>("idle");
  const [spawnStyle, setSpawnStyle] = useState("");
  const [spawnStyleId, setSpawnStyleId] = useState("");
  const [spawnGoal, setSpawnGoal] = useState("");
  const createAgent = useMutation(api.spawnedAgents.create);
  const [showAgentPicker, setShowAgentPicker] = useState(false);

  // Sync initialThreadId prop changes
  useEffect(() => {
    if (initialThreadId) setActiveThreadId(initialThreadId);
  }, [initialThreadId]);

  // One-way flag: once threads exist, hide Default permanently
  useEffect(() => {
    if (threads.length > 0) setDefaultTabHidden(true);
  }, [threads.length]);

  // Reset spawn wizard when switching threads (state must not leak across threads)
  useEffect(() => {
    setSpawnStep("idle");
    setSpawnStyle("");
    setSpawnStyleId("");
    setSpawnGoal("");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeThreadId]);

  // Reset spawn state on close; focus input + re-pin to bottom on open
  useEffect(() => {
    if (!isOpen) {
      setSpawnStep("idle");
      setSpawnStyle("");
      setSpawnStyleId("");
      setSpawnGoal("");
      setShowAgentPicker(false);
    } else {
      setTimeout(() => inputRef.current?.focus(), 80);
      stickRef.current = true;
      // Drawer content mounts/animates in — wait a tick, then jump to latest.
      setTimeout(() => {
        const el = scrollRef.current;
        if (el) el.scrollTop = el.scrollHeight;
      }, 120);
    }
  }, [isOpen]);

  // True whenever Convex has an in-flight streaming message — survives close/reopen
  const isStreaming = msgs.some((m) => m.is_streaming);

  // Track whether the user is pinned to the bottom; reading history releases the pin.
  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };

  // A new message (user send or a fresh assistant reply) always re-pins to bottom.
  useEffect(() => {
    if (msgs.length > prevMsgCountRef.current) stickRef.current = true;
    prevMsgCountRef.current = msgs.length;
  }, [msgs.length]);

  // While streaming, pin to bottom every frame. The text reveals smoothly
  // character-by-character (useSmoothReveal), so per-frame jumps read as a
  // smooth scroll — unlike scrollIntoView({smooth}) which restarts and stutters
  // on each network chunk.
  useEffect(() => {
    if (!isStreaming) return;
    let raf = 0;
    const pin = () => {
      const el = scrollRef.current;
      if (el && stickRef.current) el.scrollTop = el.scrollHeight;
      raf = requestAnimationFrame(pin);
    };
    raf = requestAnimationFrame(pin);
    return () => cancelAnimationFrame(raf);
  }, [isStreaming]);

  // Discrete (non-streaming) message changes get a single smooth glide to bottom.
  useEffect(() => {
    if (isStreaming || !stickRef.current) return;
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [msgs, isStreaming]);

  // Sync an incoming prefill into the input. In an effect, not during render —
  // calling setState in the render body forces a synchronous double-render.
  useEffect(() => {
    if (prefill && prefill !== lastPrefill) {
      setQuestion(prefill);
      setLastPrefill(prefill);
    }
  }, [prefill, lastPrefill]);

  // "+ New" entry point — open a fresh thread and auto-start the guided spawn flow.
  const [spawnKicked, setSpawnKicked] = useState(false);
  useEffect(() => {
    if (!isOpen) { setSpawnKicked(false); return; }
    if (!startSpawn || spawnKicked) return;
    setSpawnKicked(true);
    void beginSpawn();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, startSpawn, spawnKicked]);

  const openAgentPicker = () => {
    setActiveThreadId(null);
    setShowAgentPicker(true);
  };

  // Start the guided spawn wizard in a fresh thread. Used by the "+ New" entry
  // point and the agent picker's "Spawn a new agent" option.
  const beginSpawn = async () => {
    setShowAgentPicker(false);
    const id = await createThread(withToken({ title: "New agent" }));
    setActiveThreadId(id);
    await addMessage(withToken({
      role: "assistant",
      content: SPAWN_INTRO,
      sources_json: "[]",
      thread_id: id,
    }));
    setSpawnStep("awaiting_style");
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
        onDepositInfo: () => {
          setPendingAction(null); /* DepositView handled separately */
        },
      });
      await addMessage(
        withToken({
          role: "assistant",
          content: `✅ Done: ${pendingAction.summary}`,
          sources_json: "[]",
          thread_id: displayThreadId ?? undefined,
        }),
      );
      setPendingAction(null);
      setWithdrawConfirmStep(false);
    } catch (e) {
      setWithdrawConfirmStep(false);
      await addMessage(
        withToken({
          role: "assistant",
          content: `❌ Action failed: ${String(e)}`,
          sources_json: "[]",
          thread_id: displayThreadId ?? undefined,
        }),
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleQuickAction = (id: QuickActionId) => {
    if (id === "spawn") {
      // Start spawn flow — guided wizard
      void addMessage(
        withToken({
          role: "assistant",
          content: SPAWN_INTRO,
          sources_json: "[]",
          thread_id: displayThreadId ?? undefined,
        }),
      );
      setSpawnStep("awaiting_style");
    } else if (id === "custom") {
      inputRef.current?.focus();
    } else {
      const prefills: Record<string, string> = {
        configure: "Help me configure the strategy and risk parameters.",
        performance: "How is the agent performing? Show me PnL and drawdown.",
      };
      setQuestion(prefills[id] ?? "");
      inputRef.current?.focus();
    }
  };

  // Called when the user picks a style chip (or types a style freeform).
  const pickStyle = async (label: string, goal: string, styleId = "") => {
    setSpawnStyle(label);
    setSpawnStyleId(styleId);
    setSpawnGoal(goal);
    const config = SPAWN_STYLES_CONFIG.find((s) => s.id === styleId);
    const detail = config ? `\n*${config.detail}*` : "";
    await addMessage(withToken({ role: "user", content: label, sources_json: "[]", thread_id: displayThreadId ?? undefined }));
    await addMessage(withToken({
      role: "assistant",
      content: `**${label}** — ${goal}.${detail}\n\nWhat should we call it?`,
      sources_json: "[]",
      thread_id: displayThreadId ?? undefined,
    }));
    setSpawnStep("awaiting_name");
  };

  const send = async (q = question) => {
    const text = q.trim();
    if (!text || loading || isStreaming) return;
    setQuestion("");

    // ── Spawn state machine ────────────────────────────────────
    if (spawnStep === "awaiting_style") {
      await pickStyle(text, text);
      return;
    }

    if (spawnStep === "awaiting_name") {
      const name = text;
      await addMessage(withToken({ role: "user", content: name, sources_json: "[]", thread_id: displayThreadId ?? undefined }));
      const config = SPAWN_STYLES_CONFIG.find((s) => s.id === spawnStyleId);
      await createAgent({ name, goal: spawnGoal || spawnStyle || "General trading agent" });
      if (displayThreadId) void renameThread(withToken({ id: displayThreadId, title: name }));
      await addMessage(withToken({
        role: "assistant",
        content: `✅ **${name}** is spinning up in **paper mode**${config ? ` — ${config.desc.toLowerCase()}` : ""}.\n\n${config ? `*${config.detail}*\n\n` : ""}Find it in the Agents tab. I'll start scanning and report back.`,
        sources_json: "[]",
        thread_id: displayThreadId ?? undefined,
      }));
      setSpawnStep("idle");
      setSpawnStyle("");
      setSpawnStyleId("");
      setSpawnGoal("");
      return;
    }
    // ── End spawn state machine ────────────────────────────────

    setLoading(true);
    try {
      const intent = parseIntent(text);
      if (intent && intent.type !== "deposit_info") {
        await addMessage(
          withToken({
            role: "user",
            content: text,
            sources_json: "[]",
            thread_id: displayThreadId ?? undefined,
          }),
        );
        setPendingAction(intent);
        setLoading(false);
        return;
      }
      await addMessage(
        withToken({
          role: "user",
          content: text,
          sources_json: "[]",
          thread_id: displayThreadId ?? undefined,
        }),
      );

      const streamId = await startStream(
        withToken({ thread_id: displayThreadId ?? undefined }),
      );
      await askStreaming(withToken({
        question: text,
        stream_id: streamId,
        thread_id: displayThreadId ?? undefined,
      }));
    } finally {
      if (mountedRef.current) {
        setLoading(false);
        stickRef.current = true;
        setTimeout(() => {
          const el = scrollRef.current;
          if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
        }, 50);
      }
    }
  };

  return (
    <Sheet
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <SheetContent
        side="right"
        showCloseButton={false}
        className="w-[720px] max-sm:w-full p-0 flex flex-col gap-0 border-l-0 shadow-none bg-transparent overflow-hidden"
      >
        <div className="absolute inset-0 bg-bg border-l border-border" />
        <div
          className="absolute -top-16 -left-16 w-56 h-56 rounded-full pointer-events-none"
          style={{
            background:
              "radial-gradient(circle, rgba(120,40,220,0.18) 0%, transparent 70%)",
            filter: "blur(32px)",
          }}
        />

        <div className="relative flex flex-col h-full">
          {/* Horizontal thread tab bar */}
          <div className="flex items-center border-b border-border/40 flex-shrink-0">
            {/* Brand dot + label — fixed left, never scrolls */}
            <div className="flex items-center gap-1.5 px-3 flex-shrink-0 border-r border-border/40 h-10">
              <div
                className="w-2 h-2 rounded-full bg-purple"
                style={{ boxShadow: "0 0 8px var(--purple)" }}
              />
              <span className="font-display text-[13px] font-bold text-text whitespace-nowrap">
                Co-Pilot
              </span>
            </div>

            {/* Scrollable tabs area */}
            <div
              className="flex-1 flex items-center overflow-x-auto min-w-0"
              style={{ scrollbarWidth: "none" }}
            >
              {/* Default tab — hidden once any thread has ever been opened */}
              {!defaultTabHidden && (
                <button
                  onClick={() => setActiveThreadId(null)}
                  className={cn(
                    "flex-shrink-0 flex items-center h-10 px-3 font-mono text-[11px] border-r border-border/40 transition-colors cursor-pointer whitespace-nowrap relative",
                    activeThreadId === null
                      ? "text-purple bg-purple/8"
                      : "text-muted-fg hover:text-text hover:bg-elevated/50",
                  )}
                >
                  {activeThreadId === null && (
                    <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-purple rounded-t-full" />
                  )}
                  Default
                </button>
              )}

              {/* Named thread tabs */}
              {(threads as ThreadDoc[]).map((t) => (
                <div
                  key={t._id}
                  className={cn(
                    "group flex-shrink-0 flex items-center border-r border-border/40 transition-colors h-10 relative",
                    displayThreadId === t._id
                      ? "text-purple bg-purple/8"
                      : "text-muted-fg hover:text-text hover:bg-elevated/50",
                  )}
                >
                  {displayThreadId === t._id && (
                    <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-purple rounded-t-full" />
                  )}
                  <button
                    onClick={() => {
                      setActiveThreadId(t._id as Id<"copilot_threads">);
                      setShowAgentPicker(false);
                    }}
                    className="px-3 font-mono text-[11px] truncate max-w-[110px] cursor-pointer h-full flex items-center justify-center text-center"
                  >
                    {t.title}
                  </button>
                  {(threads as ThreadDoc[]).length > 1 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteThread(t._id as Id<"copilot_threads">);
                      }}
                      className="opacity-0 group-hover:opacity-100 w-5 h-5 flex items-center justify-center text-muted-fg hover:text-red transition-all cursor-pointer mr-1.5 flex-shrink-0"
                      aria-label="Delete thread"
                    >
                      <X className="w-2.5 h-2.5" />
                    </button>
                  )}
                </div>
              ))}

              {/* New thread — opens agent picker */}
              <button
                onClick={openAgentPicker}
                className="flex-shrink-0 w-9 h-10 flex items-center justify-center text-muted-fg hover:text-text hover:bg-elevated/50 transition-colors cursor-pointer border-r border-border/40"
                aria-label="New thread"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Close — fixed right, never scrolls */}
            <button
              onClick={onClose}
              className="flex-shrink-0 w-10 h-10 flex items-center justify-center text-muted-fg hover:text-text hover:bg-elevated transition-colors cursor-pointer border-l border-border/40"
              aria-label="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Chat area — full width below the tab bar */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Agent picker — shown when + is clicked */}
            {showAgentPicker && (
              <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
                <p className="font-mono text-[11px] text-muted-fg pb-1">Chat with an agent — or spawn a new one.</p>
                <button
                  onClick={() => void beginSpawn()}
                  className="w-full text-left border border-purple/40 bg-purple/5 rounded-xl px-3 py-2.5 hover:bg-purple/10 hover:border-purple/60 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="w-[26px] h-[26px] rounded-lg bg-purple/15 border border-purple/30 flex items-center justify-center flex-shrink-0">
                      <Plus className="w-3.5 h-3.5 text-purple" />
                    </span>
                    <div className="min-w-0">
                      <p className="font-mono text-[12px] text-text font-bold">Spawn a new agent</p>
                      <p className="font-mono text-[10px] text-muted-fg mt-0.5">Guided setup — starts in paper mode</p>
                    </div>
                  </div>
                </button>
                {spawnedAgents.length > 0 && (
                  <p className="font-mono text-[10px] text-muted-fg/50 uppercase tracking-widest pt-1.5">Existing agents</p>
                )}
                {spawnedAgents.map((agent) => (
                  <button
                    key={agent._id}
                    onClick={async () => {
                      const id = await createThread(withToken({ title: agent.name }));
                      setActiveThreadId(id);
                      setShowAgentPicker(false);
                    }}
                    className="w-full text-left border border-border/60 rounded-xl px-3 py-2.5 hover:bg-elevated/70 hover:border-purple/40 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start gap-2.5">
                      <span className="text-[15px] mt-0.5">🤖</span>
                      <div className="min-w-0">
                        <p className="font-mono text-[12px] text-text font-bold truncate">{agent.name}</p>
                        {agent.goal && (
                          <p className="font-mono text-[10px] text-muted-fg mt-0.5 truncate">{agent.goal}</p>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
            {/* Messages */}
            <div
              ref={scrollRef}
              onScroll={handleScroll}
              className={cn("flex-1 overflow-y-auto px-4 py-3 space-y-3", showAgentPicker && "hidden")}
              style={{ scrollBehavior: "auto" }}
            >
              <AnimatePresence initial={false}>
                {msgs.map((m) => {
                  const displayText = m.is_streaming
                    ? (m.partial_content ?? "")
                    : m.content;
                  return (
                    <motion.div
                      key={m._id}
                      className={cn(
                        "flex",
                        m.role === "user" ? "justify-end" : "justify-start",
                      )}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        type: "spring",
                        stiffness: 420,
                        damping: 32,
                      }}
                    >
                      <div
                        className={cn(
                          "max-w-[85%] rounded-xl px-3 py-2 font-mono text-[12px] leading-relaxed",
                          m.role === "user"
                            ? "bg-purple/15 text-text border border-purple/20"
                            : "bg-elevated text-text/90 border border-border/60",
                        )}
                      >
                        <MessageContent
                          text={displayText}
                          role={m.role}
                          streaming={!!m.is_streaming}
                        />
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
              {loading && !isStreaming && (
                <div className="flex justify-start">
                  <div className="bg-elevated border border-border/60 rounded-xl px-3 py-2.5">
                    <ThinkingIndicator />
                  </div>
                </div>
              )}
              {pendingAction && (
                <ActionConfirmCard
                  action={pendingAction}
                  onConfirm={confirmAction}
                  onCancel={() => {
                    setPendingAction(null);
                    setWithdrawConfirmStep(false);
                  }}
                  loading={actionLoading}
                  withdrawStep={withdrawConfirmStep}
                />
              )}
            </div>

            {/* Chips + Input */}
            {!showAgentPicker && <div className="px-4 py-3 border-t border-border/40 space-y-2">
              {/* Style picker chips */}
              {spawnStep === "awaiting_style" && (
                <div className="space-y-1.5 mb-1">
                  {SPAWN_STYLES_CONFIG.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => void pickStyle(`${s.emoji} ${s.label}`, s.goal, s.id)}
                      className="w-full text-left border border-border/60 rounded-xl px-3 py-2.5 hover:bg-elevated/70 hover:border-purple/40 transition-colors cursor-pointer"
                    >
                      <div className="flex items-start gap-2.5">
                        <span className="text-[16px] mt-0.5">{s.emoji}</span>
                        <div className="min-w-0">
                          <div className="flex items-baseline gap-2">
                            <p className="font-mono text-[12px] text-text font-bold">{s.label}</p>
                            <p className="font-mono text-[10px] text-muted-fg">{s.desc}</p>
                          </div>
                          <p className="font-mono text-[9px] text-muted-fg/70 mt-0.5 truncate">{s.detail}</p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
              {/* Name suggestion chips */}
              {spawnStep === "awaiting_name" && (
                <div className="flex flex-wrap gap-1.5 mb-1">
                  {(SPAWN_NAME_SUGGESTIONS[spawnStyleId] ?? []).map((name) => (
                    <button
                      key={name}
                      onClick={() => void send(name)}
                      className="border border-border/60 rounded-lg px-2.5 py-1.5 font-mono text-[11px] text-text hover:bg-elevated/70 hover:border-purple/40 transition-colors cursor-pointer"
                    >
                      {name}
                    </button>
                  ))}
                </div>
              )}
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
                          <p className="font-mono text-[12px] text-text font-bold">
                            {card.label}
                          </p>
                          {card.sub && (
                            <p className="font-mono text-[10px] text-muted-fg mt-0.5">
                              {card.sub}
                            </p>
                          )}
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
                  placeholder={
                    spawnStep === "awaiting_style" ? "Or describe the style in your own words…" :
                    spawnStep === "awaiting_name" ? "Or type a custom name…" :
                    "Ask the agent… (⌃↵ to send)"
                  }
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (
                      e.key === "Enter" &&
                      (!e.shiftKey || e.ctrlKey || e.metaKey)
                    ) {
                      e.preventDefault();
                      send();
                    }
                  }}
                  disabled={loading || isStreaming}
                />
                <Button
                  size="sm"
                  className="bg-purple text-white font-bold hover:bg-purple/80 cursor-pointer px-3"
                  onClick={() => send()}
                  disabled={!question.trim() || loading || isStreaming}
                >
                  →
                </Button>
              </div>
            </div>}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
