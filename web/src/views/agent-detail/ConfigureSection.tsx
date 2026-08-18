import { useQuery, useMutation } from "convex/react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "../../../../convex/_generated/api";
import { withToken } from "@/lib/control";
import { cn } from "@/lib/utils";
import { Slider } from "@/components/ui/slider";
import type { DetailAgent } from "./types";

const STRATEGIES = ["momentum", "contrarian", "balanced", "defensive"];
const MODES = ["paper", "testnet", "mainnet"] as const;
// The eligible market - BSC spot allowlist. These are the only tokens the agent may trade.
const ELIGIBLE_TOKENS = ["ETH", "CAKE", "UNI", "LINK", "AAVE"];

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="panel p-4 flex flex-col gap-3">
      <div className="flex flex-col gap-0.5">
        <span className="font-mono text-[10px] text-text uppercase tracking-widest">{title}</span>
        {hint && <span className="font-mono text-[10px] text-muted-fg/50">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

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

function SliderField({ label, hint, value, min, max, step, suffix, onChange }: {
  label: string; hint?: string; value: number; min: number; max: number; step: number; suffix: string;
  onChange: (v: number) => void;
}) {
  return (
    <Field label={label} hint={hint}>
      <div className="flex items-center gap-3">
        <Slider value={[value]} min={min} max={max} step={step}
          onValueChange={(v) => onChange(v[0])} className="flex-1" />
        <span className="font-mono text-[12px] text-text tabular-nums w-[64px] text-right">{value.toFixed(suffix === "%" ? 0 : 1)}{suffix}</span>
      </div>
    </Field>
  );
}

export function ConfigureSection({ agent }: { agent: DetailAgent }) {
  if (agent.kind === "primary") return <PrimaryConfigure />;
  return <SpawnedConfigure agent={agent} />;
}

function PrimaryConfigure() {
  const config = useQuery(api.config.get);
  const updateLimits = useMutation(api.config.updateLimits);
  const setStrategy = useMutation(api.config.setStrategy);
  const setTradingMode = useMutation(api.config.setTradingMode);
  const setAutopilot = useMutation(api.config.setAutopilot);

  // ── Sizing & risk ──
  const [maxPos, setMaxPos] = useState("");
  const [dailyLoss, setDailyLoss] = useState("");
  const [maxDd, setMaxDd] = useState(15);
  const [floor, setFloor] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!config || dirty) return;
    setMaxPos(String(config.max_position_usd));
    setDailyLoss(String(config.daily_loss_limit_usd));
    setMaxDd(Number((config.max_drawdown_pct * 100).toFixed(1)));
    setFloor(String(config.equity_floor ?? 0));
  }, [config, dirty]);

  const onEdit = (setter: (v: string) => void) => (v: string) => { setter(v); setDirty(true); };
  const onSlide = (setter: (v: number) => void) => (v: number) => { setter(v); setDirty(true); };

  async function saveRisk() {
    setSaving(true);
    try {
      await updateLimits(withToken({
        max_position_usd: Number(maxPos),
        daily_loss_limit_usd: Number(dailyLoss),
        max_drawdown_pct: maxDd / 100,
        equity_floor: Number(floor),
      }));
      toast.success("Risk limits updated");
      setDirty(false);
    } catch (e) {
      toast.error(`Save failed - ${String(e).includes("token") ? "pair the cockpit first" : "check token"}`);
    } finally { setSaving(false); }
  }

  // ── Eligible market (token allowlist) ──
  const allowlist = config?.token_allowlist ?? ELIGIBLE_TOKENS;
  async function toggleToken(sym: string) {
    const next = allowlist.includes(sym) ? allowlist.filter((t) => t !== sym) : [...allowlist, sym];
    if (next.length === 0) { toast.error("Keep at least one eligible token"); return; }
    try {
      await updateLimits(withToken({ token_allowlist: next }));
      toast.success(`${sym} ${allowlist.includes(sym) ? "removed" : "added"}`);
    } catch { toast.error("Pair the cockpit to edit the market"); }
  }

  // ── Autopilot (capital manager) ──
  const ap = config?.autopilot;
  const [apLoaded, setApLoaded] = useState(false);
  const [apEnabled, setApEnabled] = useState(false);
  const [apProtect, setApProtect] = useState(true);
  const [apTarget, setApTarget] = useState(20);
  const [apTrailing, setApTrailing] = useState(15);
  const [apDaily, setApDaily] = useState(10);
  const [apCooldown, setApCooldown] = useState("6");
  const [apOpen, setApOpen] = useState(false);
  const [apSaving, setApSaving] = useState(false);

  useEffect(() => {
    if (!config || apLoaded) return;
    if (ap) {
      setApEnabled(ap.enabled);
      setApProtect(ap.protect_principal ?? true);
      setApTarget((ap.profit_target_pct ?? 0.2) * 100);
      setApTrailing((ap.trailing_giveback_pct ?? 0.15) * 100);
      setApDaily((ap.daily_profit_target_pct ?? 0.1) * 100);
      setApCooldown(String(ap.loss_cooldown_hours ?? 6));
    }
    setApLoaded(true);
  }, [config, ap, apLoaded]);

  async function saveAutopilot() {
    setApSaving(true);
    try {
      await setAutopilot(withToken({
        autopilot: {
          enabled: apEnabled,
          protect_principal: apProtect,
          profit_target_pct: apTarget / 100,
          trailing_giveback_pct: apTrailing / 100,
          daily_profit_target_pct: apDaily / 100,
          loss_cooldown_hours: Number(apCooldown),
        },
      }));
      toast.success("Autopilot updated");
    } catch (e) {
      toast.error(`Save failed - ${String(e).includes("token") ? "pair the cockpit first" : "check token"}`);
    } finally { setApSaving(false); }
  }

  const chipCls = (active: boolean, tone: "green" | "purple") => cn(
    "font-mono text-[11px] border rounded px-3 py-2 uppercase tracking-widest transition-colors",
    active
      ? tone === "green" ? "bg-green/15 text-green border-green/30" : "bg-purple/15 text-purple border-purple/30"
      : "text-muted-fg border-border/30 hover:border-border/60",
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Sizing & Risk */}
      <Section title="Sizing & risk - drawdown-first" hint="Hard caps the engine reads every cycle.">
        <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
          <Field label="Per-trade size (USD)" hint="Max USD per position.">
            <input className={inputCls} value={maxPos} onChange={(e) => onEdit(setMaxPos)(e.target.value)} inputMode="decimal" />
          </Field>
          <Field label="Daily loss limit (USD)" hint="Halt for the day past this loss.">
            <input className={inputCls} value={dailyLoss} onChange={(e) => onEdit(setDailyLoss)(e.target.value)} inputMode="decimal" />
          </Field>
          <Field label="Equity floor (USD)" hint="Halt if portfolio drops below. 0 = off.">
            <input className={inputCls} value={floor} onChange={(e) => onEdit(setFloor)(e.target.value)} inputMode="decimal" />
          </Field>
          <SliderField label="Max drawdown" hint="Circuit-breaker depth." value={maxDd} min={1} max={50} step={1} suffix="%" onChange={onSlide(setMaxDd)} />
        </div>
        <div className="flex items-center gap-3">
          <button onClick={saveRisk} disabled={saving || !dirty}
            className="font-mono text-[12px] bg-green/20 text-green border border-green/30 rounded px-4 py-2.5 hover:bg-green/30 transition-colors disabled:opacity-40 uppercase tracking-widest self-start">
            {saving ? "Saving…" : "Save risk limits"}
          </button>
          {dirty && <span className="font-mono text-[10px] text-yellow-400">Unsaved</span>}
        </div>
      </Section>

      {/* Eligible market */}
      <Section title="Eligible market - BSC spot" hint="The only tokens the agent may trade. Spot-long-only on PancakeSwap via TWAK.">
        <div className="flex gap-1.5 flex-wrap">
          {ELIGIBLE_TOKENS.map((sym) => (
            <button key={sym} onClick={() => toggleToken(sym)} className={chipCls(allowlist.includes(sym), "green")}>
              {sym}
            </button>
          ))}
        </div>
      </Section>

      {/* Strategy + mode */}
      <Section title="Strategy & mode">
        <Field label="Strategy">
          <div className="flex gap-1.5 flex-wrap">
            {STRATEGIES.map((s) => (
              <button key={s} disabled={saving}
                onClick={async () => {
                  try { await setStrategy(withToken({ strategy_name: s })); toast.success(`Strategy → ${s}`); }
                  catch { toast.error("Pair the cockpit to change strategy"); }
                }}
                className={chipCls(config?.strategy_name === s, "green")}>{s}</button>
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
                className={chipCls(config?.trading_mode === m, "purple")}>{m}</button>
            ))}
          </div>
        </Field>
      </Section>

      {/* Autopilot (advanced) */}
      <Section title="Autopilot - capital manager" hint="Profit-lock, trailing giveback, and recycle gates. Most can leave defaults.">
        <button onClick={() => setApOpen((o) => !o)}
          className="font-mono text-[11px] text-muted-fg hover:text-text self-start uppercase tracking-widest">
          {apOpen ? "▾ Hide advanced" : "▸ Show advanced"}
        </button>
        {apOpen && (
          <div className="flex flex-col gap-3 pt-1">
            <div className="flex gap-1.5">
              <button onClick={() => setApEnabled((v) => !v)} className={chipCls(apEnabled, "green")}>
                {apEnabled ? "Enabled" : "Disabled"}
              </button>
              <button onClick={() => setApProtect((v) => !v)} className={chipCls(apProtect, "purple")}>
                {apProtect ? "Protect principal" : "No principal lock"}
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
              <SliderField label="Profit target" hint="Lock gains past this." value={apTarget} min={0} max={100} step={1} suffix="%" onChange={setApTarget} />
              <SliderField label="Trailing giveback" hint="Exit on pullback from peak." value={apTrailing} min={0} max={50} step={1} suffix="%" onChange={setApTrailing} />
              <SliderField label="Daily profit target" hint="Bank & cool down for the day." value={apDaily} min={0} max={50} step={1} suffix="%" onChange={setApDaily} />
              <Field label="Loss cooldown (hours)" hint="Pause after a losing cycle.">
                <input className={inputCls} value={apCooldown} onChange={(e) => setApCooldown(e.target.value)} inputMode="decimal" />
              </Field>
            </div>
            <button onClick={saveAutopilot} disabled={apSaving}
              className="font-mono text-[12px] bg-green/20 text-green border border-green/30 rounded px-4 py-2.5 hover:bg-green/30 transition-colors disabled:opacity-40 uppercase tracking-widest self-start">
              {apSaving ? "Saving…" : "Save autopilot"}
            </button>
          </div>
        )}
      </Section>
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
      toast.error(`Save failed - ${String(e)}`);
    } finally { setSaving(false); }
  }

  return (
    <div className="flex flex-col gap-4">
      <Section title="Mandate & schedule">
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
        <Field label="Mode" hint="Paper observes & notifies; live can place real trades.">
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
      </Section>

      <Section title="Eligible market - BSC spot" hint="Inherited from the live trader. Agents observe the same allowlist.">
        <div className="flex gap-1.5 flex-wrap">
          {ELIGIBLE_TOKENS.map((sym) => (
            <span key={sym} className="font-mono text-[11px] border border-border/30 text-muted-fg rounded px-3 py-2 uppercase tracking-widest">{sym}</span>
          ))}
        </div>
      </Section>
    </div>
  );
}
