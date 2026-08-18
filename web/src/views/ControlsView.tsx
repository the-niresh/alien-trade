import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useQuery, useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { KillSwitch } from "../components/KillSwitch";
import { Panel } from "../components/Panel";
import { withToken } from "../lib/control";
import { SPONSOR_CONTROLS } from "../lib/sponsorRegistry";
import { ControlCard } from "../components/CommandPanel";
import { usd, pct } from "../lib/formatters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";

const STRATEGIES = [
  { name: "momentum",   label: "Momentum",   blurb: "Rides confirmed uptrends." },
  { name: "contrarian", label: "Contrarian", blurb: "Buys fear, trims greed. Best in down/choppy markets." },
  { name: "balanced",   label: "Balanced",   blurb: "Momentum + derivatives + fear." },
  { name: "defensive",  label: "Defensive",  blurb: "Rare high-conviction longs. Minimises drawdown." },
];

export function ControlsView() {
  const config  = useQuery(api.config.get);
  const control = useQuery(api.agentControl.get);
  const [floorInput, setFloorInput] = useState("");
  const [showSliders, setShowSliders] = useState(false);

  const _setHalted      = useMutation(api.config.setHalted);
  const _setTradingMode = useMutation(api.config.setTradingMode);
  const _updateLimits   = useMutation(api.config.updateLimits);
  const _setControl     = useMutation(api.agentControl.set);
  const _setStrategy    = useMutation(api.config.setStrategy);
  const _setAutopilot   = useMutation(api.config.setAutopilot);
  const setHalted      = (a: Parameters<typeof _setHalted>[0])      => _setHalted(withToken(a));
  const setTradingMode = (a: Parameters<typeof _setTradingMode>[0]) => _setTradingMode(withToken(a));
  const updateLimits   = (a: Parameters<typeof _updateLimits>[0])   => _updateLimits(withToken(a));
  const setControl     = (a: Parameters<typeof _setControl>[0])     => _setControl(withToken(a));
  const setStrategy    = (a: Parameters<typeof _setStrategy>[0])    => _setStrategy(withToken(a));
  const setAutopilot   = (a: Parameters<typeof _setAutopilot>[0])   => _setAutopilot(withToken(a));

  const halted = config?.halted ?? false;
  const paused = control?.agents_paused ?? false;
  const mode   = config?.trading_mode;
  const floor  = config?.equity_floor ?? 0;
  const active = config?.strategy_name ?? "balanced";
  const ap     = config?.autopilot;

  const onKillToggle = () => {
    setHalted({ halted: !halted });
    setControl({ trading_halted: !halted, updated_by: "user" });
  };
  const onSetFloor = () => {
    const v = parseFloat(floorInput);
    if (!isNaN(v) && v >= 0) { updateLimits({ equity_floor: v }); setFloorInput(""); }
  };

  return (
    <div className="max-w-[680px] mx-auto space-y-4">
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-red rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--red)" }} />
          Command Override
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Controls</h1>
      </div>

      {/* ── Section 1: Autonomous Agent Controls ── */}
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-green rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--green)" }} />
          Autonomous Agent Controls
        </div>
        <p className="font-mono text-[11px] text-muted-fg/70">Scored path. Agent reads these each cycle.</p>
      </div>

      {/* Kill switch */}
      <Panel label="Emergency Stop" tick="red">
        <div className="flex flex-col items-center gap-4 text-center py-2">
          <KillSwitch halted={halted} onToggle={onKillToggle} hero />
          <p className="font-mono text-[12px] text-muted-fg">
            {halted ? "Agent is HALTED - hold to resume trading." : "Hold for 1.5s to halt all trading."}
          </p>
          <div className="flex gap-2 justify-center">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="sm" className="border-border text-muted-fg hover:text-text cursor-pointer">
                  {paused ? "Resume Agents" : "Pause Agents"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent className="panel border-border">
                <AlertDialogHeader>
                  <AlertDialogTitle className="text-text font-display">
                    {paused ? "Resume advisory agents?" : "Pause advisory agents?"}
                  </AlertDialogTitle>
                  <AlertDialogDescription className="text-muted-fg">
                    {paused ? "Agents will resume processing signals." : "Trading continues but advisory agents will pause."}
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel className="border-border text-muted-fg">Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    className="bg-green text-[#04140c] font-bold hover:bg-green/80"
                    onClick={() => setControl({ agents_paused: !paused, updated_by: "user" })}
                  >Confirm</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="sm" className="border-red/30 text-red bg-red/5 hover:bg-red/10 cursor-pointer">
                  Stop Response
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent className="panel border-border">
                <AlertDialogHeader>
                  <AlertDialogTitle className="text-text font-display">Stop current agent response?</AlertDialogTitle>
                  <AlertDialogDescription className="text-muted-fg">
                    This will cancel the in-flight agent action. Cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel className="border-border text-muted-fg">Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    className="bg-red text-white font-bold hover:bg-red/80"
                    onClick={() => setControl({ stop_response_id: String(Date.now()), updated_by: "user" })}
                  >Stop Response</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </Panel>

      {/* Trading mode */}
      <Panel label="Trading Mode" tick="cyan">
        {config === undefined ? <Skeleton className="h-10 w-full bg-elevated" /> : (
          <div className="flex bg-bg border border-border rounded-[10px] p-1 gap-1">
            {(["testnet", "paper", "mainnet"] as const).map((m) => {
              const isActive = mode === m;
              const activeClass = m === "testnet" ? "bg-cyan/12 text-cyan border border-cyan/25"
                : m === "paper" ? "bg-yellow/12 text-yellow border border-yellow/25"
                : "bg-red/12 text-red border border-red/25";
              if (m === "mainnet") {
                return (
                  <AlertDialog key={m}>
                    <AlertDialogTrigger asChild>
                      <button
                        className={cn(
                          "flex-1 py-2 px-3 rounded-lg font-mono text-[11px] font-bold uppercase tracking-[0.14em] transition-colors cursor-pointer",
                          isActive ? activeClass : "text-muted-fg hover:text-text"
                        )}
                        disabled={isActive}
                      >LIVE</button>
                    </AlertDialogTrigger>
                    <AlertDialogContent className="panel border-border">
                      <AlertDialogHeader>
                        <AlertDialogTitle className="text-text font-display">Switch to LIVE mainnet?</AlertDialogTitle>
                        <AlertDialogDescription className="text-muted-fg">
                          This will trade real funds via TWAK-signed transactions. Make sure your wallet is funded.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel className="border-border text-muted-fg">Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          className="bg-red text-white font-bold hover:bg-red/80"
                          onClick={() => setTradingMode({ trading_mode: "mainnet" })}
                        >Go LIVE</AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                );
              }
              return (
                <button key={m}
                  className={cn(
                    "flex-1 py-2 px-3 rounded-lg font-mono text-[11px] font-bold uppercase tracking-[0.14em] transition-colors cursor-pointer",
                    isActive ? activeClass : "text-muted-fg hover:text-text"
                  )}
                  disabled={isActive}
                  onClick={() => setTradingMode({ trading_mode: m })}
                >{m}</button>
              );
            })}
          </div>
        )}
      </Panel>

      {/* Strategy */}
      <Panel label="Strategy">
        <div className="grid grid-cols-2 gap-2 max-sm:grid-cols-1">
          {STRATEGIES.map((s) => {
            const sel = active === s.name;
            return (
              <button key={s.name}
                className={cn(
                  "relative rounded-xl p-3.5 cursor-pointer text-left transition-all border overflow-hidden",
                  sel
                    ? "border-green/55 bg-green/[0.07]"
                    : "border-border bg-elevated hover:border-border-hi hover:-translate-y-0.5 hover:bg-elevated/80"
                )}
                style={sel ? {
                  boxShadow: "0 0 20px color-mix(in oklab, var(--green) 10%, transparent), inset 0 1px 0 color-mix(in oklab, var(--green) 15%, transparent)",
                } : {}}
                onClick={() => setStrategy({ strategy_name: s.name })}
              >
                {/* Selected wash */}
                {sel && (
                  <span className="absolute inset-0 pointer-events-none rounded-xl"
                    style={{ background: "linear-gradient(135deg, color-mix(in oklab, var(--green) 8%, transparent) 0%, transparent 60%)" }}
                  />
                )}
                <div className="flex items-center gap-2 mb-1.5 relative">
                  {sel
                    ? <span className="h-2 w-2 rounded-full bg-green flex-shrink-0" style={{ boxShadow: "0 0 10px var(--green)" }} />
                    : <span className="h-2 w-2 rounded-full bg-border flex-shrink-0" />
                  }
                  <span className={cn("font-display text-[14px] font-bold", sel ? "text-green" : "text-text")}>
                    {s.label}
                  </span>
                </div>
                <div className={cn("text-[12px] leading-snug relative", sel ? "text-text/70" : "text-muted-fg")}>
                  {s.blurb}
                </div>
              </button>
            );
          })}
        </div>
      </Panel>

      {/* Equity floor */}
      <Panel label="Equity Floor" tick="yellow">
        <div className="space-y-3">
          <p className="text-[13px] text-muted-fg">
            {floor > 0
              ? <><strong className="text-text font-mono">Floor {usd(floor)}</strong> - agent halts if equity drops below this.</>
              : "Disabled - agent trades until manually halted."}
          </p>
          <div className="flex gap-2">
            <Input
              type="number" min="0" placeholder="e.g. 50"
              value={floorInput} onChange={(e) => setFloorInput(e.target.value)}
              className="w-32 bg-bg border-border text-text font-mono text-[13px] focus-visible:ring-green"
            />
            <Button size="sm" className="bg-green text-[#04140c] font-bold hover:bg-green/80 cursor-pointer"
              onClick={onSetFloor} disabled={!floorInput}>Set</Button>
            {floor > 0 && (
              <Button size="sm" variant="outline" className="border-border text-muted-fg hover:text-text cursor-pointer"
                onClick={() => updateLimits({ equity_floor: 0 })}>Remove</Button>
            )}
          </div>
        </div>
      </Panel>

      {/* Autopilot */}
      <Panel label="Autopilot" tick="cyan" action={
        <Button size="sm"
          className={cn("cursor-pointer font-mono tracking-wider",
            ap?.enabled
              ? "bg-green text-[#04140c] font-bold hover:bg-green/80"
              : "border border-border text-muted-fg bg-elevated hover:text-text"
          )}
          onClick={() => setAutopilot({ autopilot: { ...(ap ?? {}), enabled: !(ap?.enabled ?? false) } as Parameters<typeof setAutopilot>[0]["autopilot"] })}
        >{ap?.enabled ? "● ON" : "OFF"}</Button>
      }>
        {ap?.enabled ? (
          <div className="space-y-2.5">
            {[
              { label: "Take profit %",        key: "profit_target_pct" },
              { label: "Trailing give-back %", key: "trailing_giveback_pct" },
              { label: "Daily target %",       key: "daily_profit_target_pct" },
            ].map(({ label, key }) => (
              <div key={key} className="flex justify-between items-center gap-2">
                <span className="text-[13px] text-muted-fg">{label}</span>
                <Input
                  type="number" min="0" placeholder="-"
                  className="w-20 bg-bg border-border text-text font-mono text-[13px] focus-visible:ring-green"
                  defaultValue={(ap as unknown as Record<string, number | undefined>)[key] != null
                    ? (((ap as unknown as Record<string, number | undefined>)[key] as number) * 100).toFixed(1) : ""}
                  onBlur={(e) => {
                    const v = parseFloat(e.target.value);
                    setAutopilot({ autopilot: { ...ap, [key]: isNaN(v) ? undefined : v / 100 } as Parameters<typeof setAutopilot>[0]["autopilot"] });
                  }}
                />
              </div>
            ))}
          </div>
        ) : (
          <p className="font-mono text-[12px] text-muted-fg">// autopilot disabled - manual exits only</p>
        )}
      </Panel>

      {/* Risk caps */}
      <Panel label="Risk Caps" action={
        <Button size="sm" variant="outline" className="border-border text-muted-fg hover:text-text cursor-pointer"
          onClick={() => setShowSliders(!showSliders)}>
          {showSliders ? "Hide" : "Edit"}
        </Button>
      }>
        <AnimatePresence>
          {showSliders && config && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }} className="overflow-hidden space-y-4 mb-4">
              {[
                { label: "Max position",     key: "max_position_usd",     min: 100, max: 10000, step: 100, fmt: usd },
                { label: "Daily loss limit", key: "daily_loss_limit_usd", min: 50,  max: 2000,  step: 50,  fmt: usd },
              ].map(({ label, key, min, max, step, fmt }) => (
                <div key={key}>
                  <div className="flex justify-between font-mono text-[12px] mb-2">
                    <span className="text-muted-fg">{label}</span>
                    <span className="font-semibold text-text">{fmt((config as unknown as Record<string, number>)[key])}</span>
                  </div>
                  <Slider
                    min={min} max={max} step={step}
                    defaultValue={[(config as unknown as Record<string, number>)[key]]}
                    onValueCommit={([v]) => updateLimits({ [key]: v })}
                  />
                </div>
              ))}
              <div>
                <div className="flex justify-between font-mono text-[12px] mb-2">
                  <span className="text-muted-fg">Max drawdown</span>
                  <span className="font-semibold text-text">{pct(config.max_drawdown_pct)}</span>
                </div>
                <Slider
                  min={1} max={50} step={1}
                  defaultValue={[Math.round(config.max_drawdown_pct * 100)]}
                  onValueCommit={([v]) => updateLimits({ max_drawdown_pct: v / 100 })}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        {!showSliders && config && (
          <div className="grid grid-cols-3 gap-2 max-sm:grid-cols-1">
            {[
              { label: "Max position", val: usd(config.max_position_usd) },
              { label: "Daily loss", val: usd(config.daily_loss_limit_usd) },
              { label: "Max drawdown", val: pct(config.max_drawdown_pct) },
            ].map((r) => (
              <div key={r.label} className="rounded-lg bg-bg/50 border border-border px-3 py-2.5">
                <div className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-fg mb-1">{r.label}</div>
                <div className="font-mono text-[14px] font-semibold text-text tabular-nums">{r.val}</div>
              </div>
            ))}
          </div>
        )}
        {!config && <Skeleton className="h-20 w-full bg-elevated" />}
      </Panel>

      {/* ── Section 2: Manual Operator Tools ── */}
      <div className="mt-6 mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-yellow rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--yellow)" }} />
          Manual Operator Tools
        </div>
        <p className="font-mono text-[11px] text-muted-fg/70">TWAK-signed. Off the scored path. Every action is audited.</p>
      </div>
      <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
        {SPONSOR_CONTROLS
          .filter((c) => c.transport === "imperative" || (c.transport === "read" && c.readEndpoint))
          .map((c) => <ControlCard key={c.id} control={c} />)}
      </div>
    </div>
  );
}
