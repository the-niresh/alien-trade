import { useQuery, useMutation } from "convex/react";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "../../../convex/_generated/api";
import { withToken } from "@/lib/control";
import { cn } from "@/lib/utils";

const KINDS = ["price", "regime", "drawdown", "equity"] as const;
type Kind = (typeof KINDS)[number];
const TOKENS = ["ETH", "CAKE", "UNI", "LINK", "AAVE"];
const REGIMES = ["TREND", "CHOP", "CRASH", "HIGH_VOL"];

const inputCls = "font-mono text-[11px] bg-surface border border-border/40 rounded px-2 py-1.5 text-text focus:outline-none focus:border-green/50";

function summary(w: { kind: string; target: string; op: string; threshold: number }): string {
  if (w.kind === "price") return `${w.target} ${w.op === "lt" ? "<" : ">"} ${w.threshold}`;
  if (w.kind === "regime") return `regime = ${w.target}`;
  if (w.kind === "drawdown") return `drawdown ${w.op === "lt" ? "<" : ">"} ${w.threshold}%`;
  return `equity ${w.op === "lt" ? "<" : ">"} $${w.threshold}`;
}

export function WatchesPanel() {
  const watches = useQuery(api.watches.list, { limit: 50 }) ?? [];
  const create = useMutation(api.watches.create);
  const cancel = useMutation(api.watches.cancel);

  const [kind, setKind] = useState<Kind>("price");
  const [target, setTarget] = useState("CAKE");
  const [op, setOp] = useState<"lt" | "gt">("lt");
  const [threshold, setThreshold] = useState("");
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);

  const isRegime = kind === "regime";
  const needsTarget = kind === "price" || kind === "regime";

  async function add() {
    setBusy(true);
    try {
      await create(withToken({
        kind,
        label: label || undefined,
        target: needsTarget ? target : undefined,
        op: isRegime ? undefined : op,
        threshold: isRegime ? undefined : Number(threshold),
      }));
      toast.success("Watch armed");
      setThreshold(""); setLabel("");
    } catch (e) {
      const msg = String(e);
      toast.error(`Failed - ${msg.includes("token") ? "pair the cockpit first" : msg.slice(0, 70)}`);
    } finally { setBusy(false); }
  }

  const active = watches.filter((w) => w.status === "active");

  return (
    <div className="panel p-4 mt-6 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] text-text uppercase tracking-widest">Watches - deterministic monitor</span>
        <span className="font-mono text-[9px] text-muted-fg/50 uppercase tracking-widest">no LLM until one fires</span>
      </div>

      {/* Add form */}
      <div className="flex items-end gap-2 flex-wrap">
        <select className={inputCls} value={kind} onChange={(e) => setKind(e.target.value as Kind)}>
          {KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
        </select>

        {kind === "price" && (
          <select className={inputCls} value={target} onChange={(e) => setTarget(e.target.value)}>
            {TOKENS.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        )}
        {kind === "regime" && (
          <select className={inputCls} value={target} onChange={(e) => setTarget(e.target.value)}>
            {REGIMES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        )}

        {!isRegime && (
          <>
            <select className={inputCls} value={op} onChange={(e) => setOp(e.target.value as "lt" | "gt")}>
              <option value="lt">below</option>
              <option value="gt">above</option>
            </select>
            <input className={cn(inputCls, "w-[90px]")} placeholder="threshold" value={threshold}
              onChange={(e) => setThreshold(e.target.value)} inputMode="decimal" />
          </>
        )}

        <input className={cn(inputCls, "w-[120px]")} placeholder="label (optional)" value={label}
          onChange={(e) => setLabel(e.target.value)} />

        <button onClick={add} disabled={busy || (!isRegime && threshold === "")}
          className="font-mono text-[11px] bg-green/20 text-green border border-green/30 rounded px-3 py-1.5 hover:bg-green/30 transition-colors disabled:opacity-40 uppercase tracking-widest">
          {busy ? "…" : "Arm watch"}
        </button>
      </div>

      {/* Active watches */}
      {active.length === 0 ? (
        <p className="font-mono text-[11px] text-muted-fg/50">No active watches. Arm one above - the loop checks it every cycle with zero token cost until it trips.</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {active.map((w) => (
            <div key={w._id} className="flex items-center justify-between gap-2 border-t border-border/20 pt-1.5">
              <div className="flex items-center gap-2 min-w-0">
                <span className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0",
                  w.last_state === "fired" ? "bg-red" : "bg-green")}
                  style={w.last_state === "fired" ? {} : { boxShadow: "0 0 5px var(--green)" }} />
                <span className="font-mono text-[11px] text-text truncate">
                  {w.label ? <span className="text-muted-fg/70">{w.label}: </span> : null}{summary(w)}
                </span>
                {w.last_state === "fired" && (
                  <span className="font-mono text-[8px] text-red border border-red/30 rounded px-1 py-0.5 uppercase tracking-widest flex-shrink-0">fired</span>
                )}
              </div>
              <button onClick={async () => {
                try { await cancel(withToken({ id: w._id })); toast.success("Watch cancelled"); }
                catch { toast.error("Pair the cockpit to cancel"); }
              }}
                className="font-mono text-[10px] text-muted-fg/60 hover:text-red transition-colors flex-shrink-0">cancel</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
