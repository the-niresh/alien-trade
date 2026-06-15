import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useAction, useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";

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
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div className="copilot-overlay"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div className="copilot-drawer"
            initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 320, damping: 32 }}
          >
            <div className="copilot-drawer__header">
              <span className="copilot-drawer__title">Co-Pilot</span>
              <button className="btn btn--ghost btn--sm" onClick={onClose}>✕ Close</button>
            </div>

            <div className="copilot-drawer__chips">
              {CHIPS.map((c) => (
                <button key={c} className="chip" onClick={() => send(c)}>{c}</button>
              ))}
            </div>

            <div className="copilot-drawer__messages">
              {msgs.length === 0 && (
                <div style={{ color: "var(--muted)", fontSize: 13, fontStyle: "italic", padding: "8px 0" }}>
                  Ask anything — regime, last trade, risk state…
                </div>
              )}
              <AnimatePresence initial={false}>
                {msgs.map((m) => (
                  <motion.div key={m._id}
                    className={`chat-msg chat-msg--${m.role}`}
                    initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                  >
                    <div className="chat-msg__role">{m.role === "user" ? "You" : "CoPilot"}</div>
                    <div>{m.content}</div>
                  </motion.div>
                ))}
              </AnimatePresence>
              {loading && (
                <motion.div className="chat-msg chat-msg--assistant"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                >
                  <div className="chat-msg__role">CoPilot</div>
                  <motion.span animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 1.2, repeat: Infinity }}>
                    thinking…
                  </motion.span>
                </motion.div>
              )}
              <div ref={bottomRef} />
            </div>

            <div className="copilot-drawer__input-row">
              <input
                className="num-input"
                style={{ flex: 1, width: "auto" }}
                placeholder="Ask the co-pilot…"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                disabled={loading}
              />
              <button className="btn btn--primary btn--sm" onClick={() => send()}
                disabled={loading || !question.trim()}>
                {loading ? "…" : "Ask"}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
