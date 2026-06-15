import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useQuery, useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { KillSwitch } from "../components/KillSwitch";
import { withToken } from "../lib/control";
import { usd, pct } from "../lib/formatters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
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
      <h1 className="font-grotesk text-xl font-bold mb-2">Controls</h1>

      {/* Kill switch */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-2">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Emergency Stop</p>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-3 text-center">
          <KillSwitch halted={halted} onToggle={onKillToggle} hero />
          <p className="text-[13px] text-muted-fg">
            {halted ? "Agent is HALTED. Hold to resume trading." : "Hold for 1.5s to halt all trading."}
          </p>
          <div className="flex gap-2 justify-center">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="sm" className="border-border text-muted-fg hover:text-text">
                  {paused ? "Resume Agents" : "Pause Agents"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent className="bg-surface border-border">
                <AlertDialogHeader>
                  <AlertDialogTitle className="text-text">
                    {paused ? "Resume advisory agents?" : "Pause advisory agents?"}
                  </AlertDialogTitle>
                  <AlertDialogDescription className="text-muted-fg">
                    {paused ? "Agents will resume processing signals." : "Trading continues but advisory agents will pause."}
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel className="border-border text-muted-fg">Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    className="bg-cyan text-[#040d14] font-bold hover:bg-cyan/80"
                    onClick={() => setControl({ agents_paused: !paused, updated_by: "user" })}
                  >Confirm</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="sm" className="border-red/30 text-red bg-red/5 hover:bg-red/10">
                  Stop Response
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent className="bg-surface border-border">
                <AlertDialogHeader>
                  <AlertDialogTitle className="text-text">Stop current agent response?</AlertDialogTitle>
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
        </CardContent>
      </Card>

      {/* Trading mode */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-2">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Trading Mode</p>
        </CardHeader>
        <CardContent>
          {config === undefined ? <Skeleton className="h-10 w-full bg-elevated" /> : (
            <div className="flex bg-bg border border-border rounded-[10px] p-1 gap-1">
              {(["testnet", "paper", "mainnet"] as const).map((m) => {
                const isActive = mode === m;
                const activeClass = m === "testnet" ? "bg-cyan/10 text-cyan"
                  : m === "paper" ? "bg-yellow/10 text-yellow"
                  : "bg-red/10 text-red";
                if (m === "mainnet") {
                  return (
                    <AlertDialog key={m}>
                      <AlertDialogTrigger asChild>
                        <button
                          className={cn(
                            "flex-1 py-2 px-3 rounded-lg text-[12px] font-bold uppercase tracking-[0.4px] transition-colors",
                            isActive ? activeClass : "text-muted-fg hover:text-text"
                          )}
                          disabled={isActive}
                        >LIVE</button>
                      </AlertDialogTrigger>
                      <AlertDialogContent className="bg-surface border-border">
                        <AlertDialogHeader>
                          <AlertDialogTitle className="text-text">Switch to LIVE mainnet?</AlertDialogTitle>
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
                      "flex-1 py-2 px-3 rounded-lg text-[12px] font-bold uppercase tracking-[0.4px] transition-colors",
                      isActive ? activeClass : "text-muted-fg hover:text-text"
                    )}
                    disabled={isActive}
                    onClick={() => setTradingMode({ trading_mode: m })}
                  >{m}</button>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Strategy */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-2">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Strategy</p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-2">
            {STRATEGIES.map((s) => (
              <button key={s.name}
                className={cn(
                  "bg-elevated border-[1.5px] border-border rounded-xl p-3.5 cursor-pointer text-left transition-colors hover:border-border-hi",
                  active === s.name && "border-cyan bg-cyan/5"
                )}
                onClick={() => setStrategy({ strategy_name: s.name })}
              >
                <div className="font-bold text-[14px] text-text mb-1">{s.label}</div>
                <div className="text-[12px] text-muted-fg leading-snug">{s.blurb}</div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Equity floor */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-2">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Equity Floor</p>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-[13px] text-muted-fg">
            {floor > 0
              ? <><strong className="text-text">Floor: {usd(floor)}</strong> — agent halts if equity drops below this.</>
              : "Disabled — agent trades until manually halted."}
          </p>
          <div className="flex gap-2">
            <Input
              type="number" min="0" placeholder="e.g. 50"
              value={floorInput} onChange={(e) => setFloorInput(e.target.value)}
              className="w-32 bg-bg border-border text-text font-mono text-[13px] focus-visible:ring-cyan"
            />
            <Button size="sm" className="bg-cyan text-[#040d14] font-bold hover:bg-cyan/80"
              onClick={onSetFloor} disabled={!floorInput}>Set</Button>
            {floor > 0 && (
              <Button size="sm" variant="outline" className="border-border text-muted-fg hover:text-text"
                onClick={() => updateLimits({ equity_floor: 0 })}>Remove</Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Autopilot */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-0">
          <div className="flex justify-between items-center">
            <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Autopilot</p>
            <Button size="sm"
              className={cn(
                ap?.enabled
                  ? "bg-cyan text-[#040d14] font-bold hover:bg-cyan/80"
                  : "border border-border text-muted-fg bg-elevated hover:text-text"
              )}
              onClick={() => setAutopilot({ autopilot: { ...(ap ?? {}), enabled: !(ap?.enabled ?? false) } as Parameters<typeof setAutopilot>[0]["autopilot"] })}
            >{ap?.enabled ? "ON" : "OFF"}</Button>
          </div>
        </CardHeader>
        {ap?.enabled && (
          <CardContent className="space-y-2.5 mt-3">
            {[
              { label: "Take profit %",        key: "profit_target_pct" },
              { label: "Trailing give-back %", key: "trailing_giveback_pct" },
              { label: "Daily target %",       key: "daily_profit_target_pct" },
            ].map(({ label, key }) => (
              <div key={key} className="flex justify-between items-center gap-2">
                <span className="text-[13px] text-muted-fg">{label}</span>
                <Input
                  type="number" min="0" placeholder="—"
                  className="w-20 bg-bg border-border text-text font-mono text-[13px] focus-visible:ring-cyan"
                  defaultValue={(ap as unknown as Record<string, number | undefined>)[key] != null
                    ? (((ap as unknown as Record<string, number | undefined>)[key] as number) * 100).toFixed(1) : ""}
                  onBlur={(e) => {
                    const v = parseFloat(e.target.value);
                    setAutopilot({ autopilot: { ...ap, [key]: isNaN(v) ? undefined : v / 100 } as Parameters<typeof setAutopilot>[0]["autopilot"] });
                  }}
                />
              </div>
            ))}
          </CardContent>
        )}
      </Card>

      {/* Risk caps */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-0">
          <div className="flex justify-between items-center">
            <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Risk Caps</p>
            <Button size="sm" variant="outline" className="border-border text-muted-fg hover:text-text"
              onClick={() => setShowSliders(!showSliders)}>
              {showSliders ? "Hide" : "Edit"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="mt-3">
          <AnimatePresence>
            {showSliders && config && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }} className="overflow-hidden space-y-4 mb-4">
                {[
                  { label: "Max position",     key: "max_position_usd",     min: 100, max: 10000, step: 100, fmt: usd },
                  { label: "Daily loss limit", key: "daily_loss_limit_usd", min: 50,  max: 2000,  step: 50,  fmt: usd },
                ].map(({ label, key, min, max, step, fmt }) => (
                  <div key={key}>
                    <div className="flex justify-between text-[12px] mb-2">
                      <span className="text-muted-fg">{label}</span>
                      <span className="font-semibold">{fmt((config as unknown as Record<string, number>)[key])}</span>
                    </div>
                    <Slider
                      min={min} max={max} step={step}
                      defaultValue={[(config as unknown as Record<string, number>)[key]]}
                      onValueCommit={([v]) => updateLimits({ [key]: v })}
                    />
                  </div>
                ))}
                <div>
                  <div className="flex justify-between text-[12px] mb-2">
                    <span className="text-muted-fg">Max drawdown</span>
                    <span className="font-semibold">{pct(config.max_drawdown_pct)}</span>
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
            <div className="space-y-1">
              <p className="text-[13px] text-muted-fg">Max position: <strong className="text-text">{usd(config.max_position_usd)}</strong></p>
              <p className="text-[13px] text-muted-fg">Daily loss limit: <strong className="text-text">{usd(config.daily_loss_limit_usd)}</strong></p>
              <p className="text-[13px] text-muted-fg">Max drawdown: <strong className="text-text">{pct(config.max_drawdown_pct)}</strong></p>
            </div>
          )}
          {!config && <Skeleton className="h-20 w-full bg-elevated" />}
        </CardContent>
      </Card>
    </div>
  );
}
