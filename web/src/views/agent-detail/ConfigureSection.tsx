import { useQuery, useMutation } from "convex/react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "../../../../convex/_generated/api";
import { withToken } from "@/lib/control";
import { cn } from "@/lib/utils";
import type { DetailAgent } from "./types";

const STRATEGIES = ["momentum", "contrarian", "balanced", "defensive"];
const MODES = ["paper", "testnet", "mainnet"] as const;

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">{label}</label>
      {hint && <span className="font-mono text-[10px] text-muted-fg/50">{hint}</span>}
      {children}
    </div>
  );
}

const inputCls = "font-mono text-[12px] bg-surface border border-border/40 rounded px-3 py-2 text-text focus:outline-none focus:border-green/50";

export function ConfigureSection({ agent }: { agent: DetailAgent }) {
  if (agent.kind === "primary") return <PrimaryConfigure />;
  return <SpawnedConfigure agent={agent} />;
}

function PrimaryConfigure() {
  const config = useQuery(api.config.get);
  const updateLimits = useMutation(api.config.updateLimits);
  const setStrategy = useMutation(api.config.setStrategy);
  const setTradingMode = useMutation(api.config.setTradingMode);

  const [maxPos, setMaxPos] = useState("");
  const [dailyLoss, setDailyLoss] = useState("");
  const [maxDd, setMaxDd] = useState("");
  const [floor, setFloor] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!config || dirty) return;
    setMaxPos(String(config.max_position_usd));
    setDailyLoss(String(config.daily_loss_limit_usd));
    setMaxDd(String((config.max_drawdown_pct * 100).toFixed(1)));
    setFloor(String(config.equity_floor ?? 0));
  }, [config, dirty]);

  async function save() {
    setSaving(true);
    try {
      await updateLimits(withToken({
        max_position_usd: Number(maxPos),
        daily_loss_limit_usd: Number(dailyLoss),
        max_drawdown_pct: Number(maxDd) / 100,
        equity_floor: Number(floor),
      }));
      toast.success("Risk limits updated");
      setDirty(false);
    } catch (e) {
      toast.error(`Save failed — ${String(e).includes("token") ? "pair the cockpit first" : "check token"}`);
    } finally {
      setSaving(false);
    }
  }

  const onEdit = (setter: (v: string) => void) => (v: string) => { setter(v); setDirty(true); };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] text-muted-fg uppercase tracking-widest">Risk limits — drawdown-first</span>
        {dirty && <span className="font-mono text-[10px] text-yellow-400">Unsaved</span>}
      </div>

      <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
        <Field label="Per-trade size (USD)" hint="Max USD per position.">
          <input className={inputCls} value={maxPos} onChange={(e) => onEdit(setMaxPos)(e.target.value)} inputMode="decimal" />
        </Field>
        <Field label="Daily loss limit (USD)" hint="Halt for the day past this loss.">
          <input className={inputCls} value={dailyLoss} onChange={(e) => onEdit(setDailyLoss)(e.target.value)} inputMode="decimal" />
        </Field>
        <Field label="Max drawdown %" hint="Circuit-breaker depth.">
          <input className={inputCls} value={maxDd} onChange={(e) => onEdit(setMaxDd)(e.target.value)} inputMode="decimal" />
        </Field>
        <Field label="Equity floor (USD)" hint="Halt if portfolio drops below. 0 = off.">
          <input className={inputCls} value={floor} onChange={(e) => onEdit(setFloor)(e.target.value)} inputMode="decimal" />
        </Field>
      </div>

      <Field label="Strategy">
        <div className="flex gap-1.5 flex-wrap">
          {STRATEGIES.map((s) => (
            <button key={s} disabled={saving}
              onClick={async () => {
                try { await setStrategy(withToken({ strategy_name: s })); toast.success(`Strategy → ${s}`); }
                catch { toast.error("Pair the cockpit to change strategy"); }
              }}
              className={cn("font-mono text-[11px] border rounded px-3 py-2 uppercase tracking-widest transition-colors",
                config?.strategy_name === s ? "bg-green/15 text-green border-green/30" : "text-muted-fg border-border/30 hover:border-border/60")}>
              {s}
            </button>
          ))}
        </div>
      </Field>

      <Field label="Trading mode">
        <div className="flex gap-1.5">
          {MODES.map((m) => (
            <button key={m} disabled={saving}
              onClick={async () => {
                try { await setTradingMode(withToken({ trading_mode: m })); toast.success(`Mode → ${m}`); }
                catch { toast.error("Pair the cockpit to change mode"); }
              }}
              className={cn("font-mono text-[11px] border rounded px-3 py-2 uppercase tracking-widest transition-colors",
                config?.trading_mode === m ? "bg-purple/15 text-purple border-purple/30" : "text-muted-fg border-border/30 hover:border-border/60")}>
              {m}
            </button>
          ))}
        </div>
      </Field>

      <button onClick={save} disabled={saving || !dirty}
        className="font-mono text-[12px] bg-green/20 text-green border border-green/30 rounded px-4 py-2.5 hover:bg-green/30 transition-colors disabled:opacity-40 uppercase tracking-widest self-start">
        {saving ? "Saving…" : "Save risk limits"}
      </button>
    </div>
  );
}

function SpawnedConfigure({ agent }: { agent: DetailAgent }) {
  const update = useMutation(api.spawnedAgents.update);
  const [goal, setGoal] = useState(agent.goal ?? "");
  const [spec, setSpec] = useState(agent.trigger?.spec ?? "4h");
  const [mode, setMode] = useState<"paper" | "live">(agent.mode === "live" ? "live" : "paper");
  const [saving, setSaving] = useState(false);

  async function save() {
    if (!agent.id) return;
    setSaving(true);
    try {
      await update({ id: agent.id, goal, trigger: { kind: "schedule", spec }, mode });
      toast.success("Agent updated");
    } catch (e) {
      toast.error(`Save failed — ${String(e)}`);
    } finally { setSaving(false); }
  }

  return (
    <div className="flex flex-col gap-4">
      <Field label="Goal">
        <textarea className={cn(inputCls, "resize-none")} rows={2} value={goal} onChange={(e) => setGoal(e.target.value)} />
      </Field>
      <Field label="Run cadence">
        <select className={inputCls} value={spec} onChange={(e) => setSpec(e.target.value)}>
          <option value="1h">Every hour</option>
          <option value="4h">Every 4 hours</option>
          <option value="24h">Daily</option>
        </select>
      </Field>
      <Field label="Mode">
        <div className="flex gap-1.5">
          {(["paper", "live"] as const).map((m) => (
            <button key={m} onClick={() => setMode(m)}
              className={cn("font-mono text-[11px] border rounded px-3 py-2 uppercase tracking-widest transition-colors",
                mode === m ? "bg-purple/15 text-purple border-purple/30" : "text-muted-fg border-border/30 hover:border-border/60")}>{m}</button>
          ))}
        </div>
      </Field>
      <button onClick={save} disabled={saving}
        className="font-mono text-[12px] bg-green/20 text-green border border-green/30 rounded px-4 py-2.5 hover:bg-green/30 transition-colors disabled:opacity-40 uppercase tracking-widest self-start">
        {saving ? "Saving…" : "Save agent"}
      </button>
    </div>
  );
}
