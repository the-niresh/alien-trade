import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { useQuery, useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { RegimeBadge } from "../components/RegimeBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { usd, ts } from "../lib/formatters";
import {
  Clock, CheckCircle2, XCircle, Loader2, Users, Search,
  ExternalLink, X, Zap, Radio, BarChart2, Bell, TrendingUp, Plus,
  Wallet, Copy, Check, RefreshCw,
} from "lucide-react";
import RAW_KOLS from "../data/kols.json";

type KolEntry = { taskId: string | null; handle: string; numListeners: number; numBoosts: number };

const ALL_KOLS: KolEntry[] = (RAW_KOLS as KolEntry[]).slice(0, 100);

const STATUS_STYLE: Record<string, string> = {
  queued:  "text-yellow border-yellow/30 bg-yellow/8",
  running: "text-cyan border-cyan/30 bg-cyan/8",
  done:    "text-green border-green/30 bg-green/8",
  failed:  "text-red border-red/30 bg-red/8",
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  queued:  <Clock className="w-3 h-3" />,
  running: <Loader2 className="w-3 h-3 animate-spin" />,
  done:    <CheckCircle2 className="w-3 h-3" />,
  failed:  <XCircle className="w-3 h-3" />,
};

type Position = {
  _id: string; symbol: string; quantity: number; avg_entry_price: number;
  current_price?: number; current_value_usd?: number; unrealized_pnl_usd: number;
  mode?: string; updated_ms?: number;
};

type AgentCommand = {
  _id: string; command_type: string; params?: string; status: string;
  queued_by?: string; queued_at_ms: number; updated_at_ms?: number; error?: string;
};

type Decision = {
  _id: string; symbol: string; regime: string; risk_verdict: string; timestamp_ms: number;
};

type Tab = "activity" | "kols" | "wallet";
type KolSubTab = "mylist" | "top";

type WalletState = {
  _id: string; address?: string;
  usdt: number; eth: number; bnb: number;
  bnb_usd: number; total_usd: number; updated_ms: number;
};

function xProfileUrl(handle: string) {
  return `https://x.com/${handle}`;
}

function InfluenceBar({ score, max, color = "cyan" }: { score: number; max: number; color?: string }) {
  const pct = Math.min(100, (score / max) * 100);
  return (
    <div className="w-16 h-1.5 bg-border/60 rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{
          width: `${pct}%`,
          background: `var(--${color})`,
          boxShadow: pct > 50 ? `0 0 6px var(--${color})` : undefined,
        }}
      />
    </div>
  );
}

function LiveDot({ color = "green" }: { color?: string }) {
  return (
    <span className="relative flex h-2 w-2 flex-shrink-0">
      <span
        className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60"
        style={{ background: `var(--${color})` }}
      />
      <span
        className="relative inline-flex rounded-full h-2 w-2"
        style={{ background: `var(--${color})` }}
      />
    </span>
  );
}

export function TrackersView() {
  const [tab, setTab] = useState<Tab>("activity");
  const [kolSub, setKolSub] = useState<KolSubTab>("mylist");
  const [search, setSearch] = useState("");
  const [addInput, setAddInput] = useState("");

  // KOL My List — persisted in Convex social_sources
  const sources = useQuery(api.social.getSources);
  const addSourceMut = useMutation(api.social.addSource);
  const removeSourceMut = useMutation(api.social.removeSource);

  const myListSources = useMemo(() =>
    (sources ?? []).filter((s) => s.platform === "twitter" && s.enabled),
    [sources]
  );
  const myListHandles = useMemo(() => myListSources.map((s) => s.handle), [myListSources]);

  // Seed with top 5 KOLs on first load if the table is empty
  const seededRef = useRef(false);
  useEffect(() => {
    if (seededRef.current || sources === undefined || sources.length > 0) return;
    seededRef.current = true;
    for (const k of ALL_KOLS.slice(0, 5)) {
      addSourceMut({ platform: "twitter", handle: k.handle, label: k.handle, weight: 1 });
    }
  }, [sources, addSourceMut]);
  const [alertsOpen, setAlertsOpen] = useState(true);

  const [copied, setCopied] = useState(false);

  type TrackedWallet = { id: string; address: string; label: string; group: string; addedMs: number };
  const [trackedWallets, setTrackedWallets] = useState<TrackedWallet[]>([]);
  const [addWalletOpen, setAddWalletOpen] = useState(false);
  const [walletFormAddr, setWalletFormAddr] = useState("");
  const [walletFormLabel, setWalletFormLabel] = useState("");

  const addTrackedWallet = useCallback(() => {
    const addr = walletFormAddr.trim();
    if (!addr) return;
    setTrackedWallets((prev) => [...prev, {
      id: `${Date.now()}`,
      address: addr,
      label: walletFormLabel.trim() || addr.slice(0, 8) + "…",
      group: "Main",
      addedMs: Date.now(),
    }]);
    setWalletFormAddr(""); setWalletFormLabel(""); setAddWalletOpen(false);
  }, [walletFormAddr, walletFormLabel]);

  const removeTrackedWallet = useCallback((id: string) => {
    setTrackedWallets((prev) => prev.filter((w) => w.id !== id));
  }, []);

  const closeAddWalletModal = useCallback(() => {
    setAddWalletOpen(false); setWalletFormAddr(""); setWalletFormLabel("");
  }, []);

  useEffect(() => {
    if (!addWalletOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") closeAddWalletModal(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [addWalletOpen, closeAddWalletModal]);

  const positions   = useQuery(api.positions.open) ?? [];
  const commands    = useQuery(api.agentCommands.list, { limit: 20 }) ?? [];
  const decisions   = useQuery(api.decisions.recent, { limit: 1 }) ?? [];
  const walletState = useQuery(api.walletState.get) as WalletState | null | undefined;

  const copyAddress = useCallback(() => {
    const addr = walletState?.address;
    if (!addr) return;
    navigator.clipboard.writeText(addr).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [walletState?.address]);

  const typedPositions = positions as Position[];
  const typedCommands  = commands as AgentCommand[];
  const typedDecisions = decisions as Decision[];

  const kolsWithInfluence = useMemo(() =>
    ALL_KOLS.map((k) => ({
      ...k,
      influence: Math.round(k.numListeners * Math.log10(Math.max(k.numBoosts, 10))),
    })),
    []
  );
  const maxInfluence = kolsWithInfluence[0]?.influence ?? 1;

  const topKols = useMemo(() => {
    const q = search.toLowerCase();
    return kolsWithInfluence.filter((k) =>
      !q || k.handle.toLowerCase().includes(q)
    );
  }, [kolsWithInfluence, search]);

  const myKols = useMemo(() => {
    const q = search.toLowerCase();
    return myListHandles
      .map((h) => kolsWithInfluence.find((k) => k.handle === h))
      .filter((k): k is NonNullable<typeof k> => !!k && (!q || k.handle.toLowerCase().includes(q)));
  }, [myListHandles, kolsWithInfluence, search]);

  const activeKols = kolSub === "mylist" ? myKols : topKols;

  const removeFromList = useCallback((handle: string) => {
    const src = myListSources.find((s) => s.handle === handle);
    if (src) removeSourceMut({ id: src._id });
  }, [myListSources, removeSourceMut]);

  const addToList = useCallback((handle: string) => {
    const clean = handle.replace(/^@/, "").trim().toLowerCase();
    if (!clean) return;
    if (!myListHandles.includes(clean)) {
      addSourceMut({ platform: "twitter", handle: clean, label: clean, weight: 1 });
    }
    setAddInput("");
  }, [myListHandles, addSourceMut]);

  const isInMyList = useCallback((handle: string) => myListHandles.includes(handle), [myListHandles]);

  const ongoing = typedCommands.filter((c) => c.status === "running");
  const pending = typedCommands.filter((c) => c.status === "queued");
  const recent  = typedCommands.filter((c) => c.status === "done" || c.status === "failed").slice(0, 5);
  const nextDecision = typedDecisions[0];
  const positionsLoading = positions === undefined;
  const commandsLoading  = commands === undefined;

  return (
    <div className="max-w-[900px] mx-auto space-y-4">
      {/* Header */}
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span className="h-[2px] w-4 bg-cyan rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--cyan)" }} />
          Live Agent Activity
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Trackers</h1>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 border-b border-border pb-0">
        {(["activity", "kols", "wallet"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "font-mono text-[11px] px-3 py-2 border-b-2 -mb-px transition-colors cursor-pointer",
              tab === t ? "border-cyan text-cyan" : "border-transparent text-muted-fg hover:text-text",
            )}
          >
            {t === "activity" ? "Activity" : t === "wallet" ? (
              <span className="flex items-center gap-1.5"><Wallet className="w-3 h-3" />Wallet</span>
            ) : (
              <span className="flex items-center gap-1.5">
                KOL Feed
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-cyan/15 text-cyan border border-cyan/25">
                  {myListHandles.length}
                </span>
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ─── WALLET TAB ─── */}
      {tab === "wallet" && (
        <div className="space-y-3">
          {/* Agent wallet banner — enhanced */}
          <div className="panel relative overflow-hidden">
            {/* Corner atmosphere glow */}
            <div
              className="absolute pointer-events-none"
              style={{
                top: -80, right: -60, width: 260, height: 260, borderRadius: "50%",
                background: "radial-gradient(circle, color-mix(in oklab, var(--green) 13%, transparent), transparent 70%)",
              }}
            />
            <header className="relative flex items-center justify-between gap-3 px-3.5 pt-3 pb-2">
              <span className="panel-label" style={{ "--tick": "var(--green)" } as React.CSSProperties}>
                Agent Wallet · BSC
              </span>
              <div className="flex items-center gap-1.5">
                <LiveDot color="green" />
                <span className="font-mono text-[10px] text-green">self-custody</span>
              </div>
            </header>
            <div className="relative px-3.5 pb-4 space-y-3">
              {walletState === undefined ? (
                <Skeleton className="h-20 w-full rounded-xl" />
              ) : !walletState ? (
                <div className="flex items-center gap-2 py-3 font-mono text-[12px] text-muted-fg">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Waiting for agent to report wallet state…
                </div>
              ) : (
                <>
                  {walletState.address && (
                    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-elevated border border-border">
                      <span className="font-mono text-[9px] uppercase tracking-widest text-muted-fg/60 flex-shrink-0">Address</span>
                      <span className="font-mono text-[10px] text-cyan truncate flex-1 min-w-0">{walletState.address}</span>
                      <button onClick={copyAddress} className="flex-shrink-0 p-1 rounded hover:bg-cyan/10 text-muted-fg hover:text-cyan transition-colors cursor-pointer">
                        {copied ? <Check className="w-3 h-3 text-green" /> : <Copy className="w-3 h-3" />}
                      </button>
                      <a href={`https://bscscan.com/address/${walletState.address}`} target="_blank" rel="noopener noreferrer"
                        className="flex-shrink-0 p-1 rounded hover:bg-cyan/10 text-muted-fg hover:text-cyan transition-colors">
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  )}

                  {/* Hero total */}
                  <div className="flex flex-col items-center py-3">
                    <span className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-fg/50 mb-1.5">Total Portfolio Value</span>
                    <span
                      className="font-display text-[40px] font-bold tabular-nums tracking-tight"
                      style={{ color: "var(--text)", textShadow: "0 0 56px color-mix(in oklab, var(--green) 50%, transparent)" }}
                    >
                      {usd(walletState.total_usd)}
                    </span>
                  </div>

                  {/* Token cards — 3 col with per-token glow */}
                  <div className="grid grid-cols-3 gap-2">
                    {([
                      { label: "USDT", value: walletState.usdt.toFixed(2),  color: "green",  note: "stablecoin" },
                      { label: "ETH",  value: walletState.eth.toFixed(4),   color: "cyan",   note: "scored" },
                      { label: "BNB",  value: walletState.bnb.toFixed(4),   color: "yellow", note: "gas only" },
                    ] as const).map(({ label, value, color, note }) => (
                      <div
                        key={label}
                        className="relative flex flex-col gap-1 px-3 py-2.5 rounded-xl border overflow-hidden"
                        style={{
                          borderColor: `color-mix(in oklab, var(--${color}) 22%, var(--border))`,
                          background:  `color-mix(in oklab, var(--${color}) 5%, var(--elevated))`,
                        }}
                      >
                        <div
                          className="absolute top-0 right-0 w-14 h-14 pointer-events-none"
                          style={{ background: `radial-gradient(circle at 80% 15%, color-mix(in oklab, var(--${color}) 22%, transparent), transparent 70%)` }}
                        />
                        <span className="font-mono text-[9px] uppercase tracking-widest font-bold" style={{ color: `var(--${color})`, opacity: 0.75 }}>{label}</span>
                        <span className="font-mono text-[15px] font-bold tabular-nums" style={{ color: `var(--${color})` }}>{value}</span>
                        <span className="font-mono text-[8px] text-muted-fg/40">{note}</span>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center gap-1.5 font-mono text-[9px] text-muted-fg/40">
                    <RefreshCw className="w-2.5 h-2.5" />
                    updated {ts(walletState.updated_ms)}
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Tracked wallets */}
          <Panel
            label="Tracked Wallets"
            tick="purple"
            action={
              <button
                onClick={() => setAddWalletOpen(true)}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-cyan/10 border border-cyan/25 text-cyan text-[11px] font-mono font-bold hover:bg-cyan/20 transition-colors cursor-pointer"
              >
                <Plus className="w-3 h-3" />
                Add Wallet
              </button>
            }
          >
            {trackedWallets.length === 0 ? (
              <div className="flex flex-col items-center gap-3 py-8">
                <Wallet className="w-8 h-8 text-muted-fg/20" />
                <div className="text-center space-y-0.5">
                  <p className="font-mono text-[12px] text-muted-fg">No wallets tracked yet.</p>
                  <p className="font-mono text-[10px] text-muted-fg/60">Add a BSC wallet to monitor whale activity.</p>
                </div>
                <button
                  onClick={() => setAddWalletOpen(true)}
                  className="px-4 py-1.5 rounded-lg bg-cyan/10 border border-cyan/25 text-cyan text-[11px] font-mono font-bold hover:bg-cyan/20 transition-colors cursor-pointer"
                >
                  Add Wallet
                </button>
              </div>
            ) : (
              <div>
                {/* Column headers */}
                <div className="grid gap-x-3 px-1 pb-1.5 font-mono text-[9px] uppercase tracking-[0.18em] text-muted-fg/50 border-b border-border/30"
                  style={{ gridTemplateColumns: "1fr 5rem 3.5rem 1.5rem" }}>
                  <span>Name</span>
                  <span>Added</span>
                  <span>Group</span>
                  <span />
                </div>
                <div className="divide-y divide-border/10">
                  {trackedWallets.map((w) => (
                    <div key={w.id} className="group grid gap-x-3 items-center px-1 py-2 hover:bg-elevated/40 transition-colors"
                      style={{ gridTemplateColumns: "1fr 5rem 3.5rem 1.5rem" }}>
                      <div className="min-w-0">
                        <div className="font-mono text-[11px] font-bold text-text truncate">{w.label}</div>
                        <a
                          href={`https://bscscan.com/address/${w.address}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-[9px] text-muted-fg/60 hover:text-cyan truncate block"
                        >
                          {w.address.slice(0, 10)}…{w.address.slice(-6)}
                        </a>
                      </div>
                      <span className="font-mono text-[10px] text-muted-fg tabular-nums">{ts(w.addedMs)}</span>
                      <span className="font-mono text-[10px] text-muted-fg">{w.group}</span>
                      <button
                        onClick={() => removeTrackedWallet(w.id)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded text-muted-fg/50 hover:text-red hover:bg-red/10 cursor-pointer"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Panel>

          {/* Gas notice */}
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-yellow/5 border border-yellow/15 font-mono text-[10px] text-muted-fg">
            <Zap className="w-3.5 h-3.5 text-yellow flex-shrink-0" />
            <span>Scoring tokens: <span className="text-text">ETH · CAKE · UNI · LINK · AAVE</span> — BNB is gas only.</span>
          </div>

          {/* ─── ADD WALLET MODAL ─── */}
          {addWalletOpen && (
            <div
              className="fixed inset-0 z-[100] flex items-center justify-center p-4"
              role="dialog"
              aria-modal="true"
              aria-label="Add BSC Wallet"
            >
              <div
                className="absolute inset-0 bg-black/65 backdrop-blur-sm"
                onClick={closeAddWalletModal}
              />
              <div
                className="relative z-10 w-full max-w-sm rounded-2xl overflow-hidden"
                style={{
                  background: "var(--surface)",
                  border: "1px solid color-mix(in oklab, var(--cyan) 30%, var(--border))",
                  boxShadow: "0 0 0 1px color-mix(in oklab, var(--cyan) 10%, transparent), 0 24px 64px rgba(0,0,0,0.8)",
                }}
              >
                <div
                  className="absolute inset-0 pointer-events-none"
                  style={{ background: "radial-gradient(ellipse 90% 50% at 50% -5%, color-mix(in oklab, var(--cyan) 10%, transparent), transparent)" }}
                />
                <div className="relative flex items-start justify-between px-5 pt-5 pb-4 border-b border-border">
                  <div>
                    <div className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-fg/50 mb-1">Tracked Wallets</div>
                    <div className="font-display text-[18px] font-bold text-text">Add BSC Wallet</div>
                    <div className="font-mono text-[10px] text-muted-fg/50 mt-0.5">Monitor whale activity on-chain</div>
                  </div>
                  <button
                    onClick={closeAddWalletModal}
                    className="mt-0.5 p-1.5 rounded-lg hover:bg-elevated text-muted-fg hover:text-text transition-colors cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="relative px-5 py-4 space-y-3">
                  <div className="space-y-1.5">
                    <label className="block font-mono text-[10px] uppercase tracking-wider text-muted-fg/70">
                      Wallet Address <span className="text-red text-[9px]">*</span>
                    </label>
                    <input
                      autoFocus
                      value={walletFormAddr}
                      onChange={(e) => setWalletFormAddr(e.target.value)}
                      placeholder="0x… wallet address"
                      className="w-full px-3 py-2.5 rounded-xl bg-elevated border border-border text-[12px] font-mono text-text placeholder:text-muted-fg/30 focus:outline-none focus:border-cyan/50 focus:ring-1 focus:ring-cyan/20 transition-colors"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="block font-mono text-[10px] uppercase tracking-wider text-muted-fg/70">
                      Label <span className="font-normal text-muted-fg/40 normal-case">(optional)</span>
                    </label>
                    <input
                      value={walletFormLabel}
                      onChange={(e) => setWalletFormLabel(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && addTrackedWallet()}
                      placeholder="e.g. Whale #1, Smart Money"
                      className="w-full px-3 py-2.5 rounded-xl bg-elevated border border-border text-[12px] font-mono text-text placeholder:text-muted-fg/30 focus:outline-none focus:border-cyan/50 focus:ring-1 focus:ring-cyan/20 transition-colors"
                    />
                  </div>
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={addTrackedWallet}
                      disabled={!walletFormAddr.trim()}
                      className="flex-1 py-2.5 rounded-xl font-mono text-[12px] font-bold transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                      style={{
                        background: "color-mix(in oklab, var(--cyan) 14%, transparent)",
                        border: "1px solid color-mix(in oklab, var(--cyan) 35%, transparent)",
                        color: "var(--cyan)",
                      }}
                    >
                      Track Wallet
                    </button>
                    <button
                      onClick={closeAddWalletModal}
                      className="px-5 py-2.5 rounded-xl font-mono text-[12px] text-muted-fg hover:text-text transition-colors cursor-pointer"
                      style={{ background: "var(--elevated)", border: "1px solid var(--border)" }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ─── KOL FEED TAB ─── */}
      {tab === "kols" && (
        <div className="space-y-3">
          {/* Toolbar */}
          <div className="flex items-center gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-fg/50" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filter handles…"
                className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-elevated border border-border text-[12px] font-mono text-text placeholder:text-muted-fg/40 focus:outline-none focus:border-cyan/50 focus:ring-1 focus:ring-cyan/20 transition-colors"
              />
            </div>
            {/* Add handle */}
            <div className="flex items-center gap-1">
              <input
                value={addInput}
                onChange={(e) => setAddInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addToList(addInput)}
                placeholder="@handle"
                className="w-24 px-2.5 py-1.5 rounded-lg bg-elevated border border-border text-[12px] font-mono text-text placeholder:text-muted-fg/40 focus:outline-none focus:border-green/50 focus:ring-1 focus:ring-green/20 transition-colors"
              />
              <button
                onClick={() => addToList(addInput)}
                disabled={!addInput.trim()}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-green/10 border border-green/25 text-green text-[11px] font-mono font-bold hover:bg-green/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
              >
                <Plus className="w-3 h-3" />
                Add
              </button>
            </div>
            {/* Alerts toggle */}
            <button
              onClick={() => setAlertsOpen((v) => !v)}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[11px] font-mono transition-colors cursor-pointer",
                alertsOpen
                  ? "bg-cyan/10 border-cyan/30 text-cyan"
                  : "bg-elevated border-border text-muted-fg hover:text-text",
              )}
            >
              <Bell className="w-3 h-3" />
              Alerts
            </button>
          </div>

          {/* Sub-tabs */}
          <div className="flex items-center gap-1">
            {(["mylist", "top"] as KolSubTab[]).map((s) => (
              <button
                key={s}
                onClick={() => setKolSub(s)}
                className={cn(
                  "font-mono text-[10px] px-2.5 py-1 rounded-md border transition-colors cursor-pointer",
                  kolSub === s
                    ? "bg-cyan/10 border-cyan/30 text-cyan"
                    : "bg-elevated border-border text-muted-fg hover:text-text",
                )}
              >
                {s === "mylist" ? `My List (${myListHandles.length})` : `Top Subscriptions (${ALL_KOLS.length})`}
              </button>
            ))}
            <div className="ml-auto flex items-center gap-1.5">
              <LiveDot color="green" />
              <span className="font-mono text-[10px] text-green">Sentiment signal active</span>
            </div>
          </div>

          {/* Main layout: list + alerts panel */}
          <div className={cn("flex gap-3 items-start", alertsOpen ? "flex-row" : "")}>
            {/* ── KOL List ── */}
            <div className="flex-1 min-w-0 panel">
              <header className="flex items-center justify-between gap-3 px-3.5 pt-3 pb-2">
                <span className="panel-label" style={{ "--tick": "var(--cyan)" } as React.CSSProperties}>
                  {kolSub === "mylist"
                  ? <span>My Tracked Handles <span className="font-mono text-[9px] text-yellow ml-1">← sentiment source</span></span>
                  : "Top KOL Subscriptions"
                }
                </span>
                <span className="font-mono text-[10px] text-muted-fg flex items-center gap-1">
                  <Users className="w-3 h-3" />
                  {activeKols.length}
                </span>
              </header>

              {/* Column headers */}
              <div className="grid gap-x-3 px-3.5 pb-1.5 font-mono text-[9px] uppercase tracking-[0.18em] text-muted-fg/50 border-b border-border/30"
                style={{ gridTemplateColumns: "1.4rem 1fr 4.5rem 2.5rem 4rem 1.5rem" }}>
                <span>#</span>
                <span>Handle</span>
                <span className="text-right">Listeners</span>
                <span className="text-right">Boosts</span>
                <span className="text-right">Signal</span>
                <span />
              </div>

              <div className="max-h-[480px] overflow-y-auto divide-y divide-border/10 pb-2">
                {activeKols.length === 0 && (
                  <div className="flex flex-col items-center gap-2 py-8">
                    <Users className="w-6 h-6 text-muted-fg/30" />
                    <p className="font-mono text-[11px] text-muted-fg">
                      {search ? "No handles match your filter" : "No handles in My List yet"}
                    </p>
                    {!search && kolSub === "mylist" && (
                      <p className="font-mono text-[10px] text-muted-fg/60">
                        Switch to Top Subscriptions to add handles
                      </p>
                    )}
                  </div>
                )}
                {activeKols.map((k, i) => (
                  <div
                    key={k.handle}
                    className="group grid gap-x-3 items-center px-3.5 py-2 hover:bg-elevated/50 transition-colors"
                    style={{
                      gridTemplateColumns: "1.4rem 1fr 4.5rem 2.5rem 4rem 1.5rem",
                      animationDelay: `${i * 18}ms`,
                    }}
                  >
                    {/* Rank */}
                    <span className="font-mono text-[9px] text-muted-fg/40 tabular-nums">{i + 1}</span>

                    {/* Handle — links to X/Twitter profile */}
                    <a
                      href={xProfileUrl(k.handle)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 min-w-0 group/link"
                    >
                      <span className="font-mono text-[12px] font-bold text-cyan group-hover/link:text-cyan group-hover/link:underline underline-offset-2 truncate">
                        @{k.handle}
                      </span>
                      <ExternalLink className="w-2.5 h-2.5 text-cyan/40 opacity-0 group-hover/link:opacity-100 transition-opacity flex-shrink-0" />
                    </a>

                    {/* Listeners */}
                    <span className="font-mono text-[11px] text-text tabular-nums text-right">
                      {k.numListeners >= 1000
                        ? `${(k.numListeners / 1000).toFixed(1)}k`
                        : k.numListeners.toLocaleString()}
                    </span>

                    {/* Boosts */}
                    <span className="font-mono text-[10px] text-muted-fg tabular-nums text-right">
                      {(k.numBoosts / 1000).toFixed(0)}k
                    </span>

                    {/* Influence bar */}
                    <div className="flex items-center gap-1.5 justify-end">
                      <InfluenceBar score={k.influence} max={maxInfluence} color="cyan" />
                    </div>

                    {/* Action: remove or add */}
                    <div className="flex justify-end">
                      {kolSub === "mylist" ? (
                        <button
                          onClick={() => removeFromList(k.handle)}
                          className="p-0.5 rounded text-muted-fg/30 hover:text-red hover:bg-red/10 transition-colors cursor-pointer"
                          title="Remove from My List"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      ) : (
                        <button
                          onClick={() => isInMyList(k.handle) ? removeFromList(k.handle) : addToList(k.handle)}
                          className={cn(
                            "opacity-0 group-hover:opacity-100 transition-all p-0.5 rounded cursor-pointer text-[9px] font-mono",
                            isInMyList(k.handle)
                              ? "text-red/70 hover:text-red hover:bg-red/10"
                              : "text-green/70 hover:text-green hover:bg-green/10",
                          )}
                          title={isInMyList(k.handle) ? "Remove from My List" : "Add to My List"}
                        >
                          {isInMyList(k.handle) ? <X className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* ── Alerts Side Panel ── */}
            {alertsOpen && (
              <div className="w-52 flex-shrink-0 space-y-2">
                {/* Live monitoring */}
                <div className="panel">
                  <header className="flex items-center justify-between gap-2 px-3 pt-3 pb-2">
                    <span className="panel-label text-[10px]" style={{ "--tick": "var(--green)" } as React.CSSProperties}>
                      Twitter Alerts
                    </span>
                    <LiveDot color="green" />
                  </header>
                  <div className="px-3 pb-3 space-y-2">
                    <div className="font-mono text-[10px] text-muted-fg leading-relaxed">
                      Only handles in <span className="text-cyan font-bold">My List</span> drive the{" "}
                      <span className="text-yellow font-bold">sentiment signal</span>. Add or remove handles to control what the agent reads.
                    </div>
                    <div className="flex items-center gap-2 py-1.5 px-2 rounded-lg bg-green/6 border border-green/15">
                      <Radio className="w-3 h-3 text-green flex-shrink-0 animate-pulse" />
                      <div>
                        <div className="font-mono text-[10px] font-bold text-green">{myListHandles.length} signal source{myListHandles.length !== 1 ? "s" : ""}</div>
                        <div className="font-mono text-[9px] text-muted-fg">feeds sentiment via CMC</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Signal breakdown */}
                <div className="panel">
                  <header className="px-3 pt-3 pb-2">
                    <span className="panel-label text-[10px]" style={{ "--tick": "var(--cyan)" } as React.CSSProperties}>
                      Signal Feed
                    </span>
                  </header>
                  <div className="px-3 pb-3 space-y-1.5">
                    {[
                      { icon: <BarChart2 className="w-3 h-3" />, label: "Listener reach", value: `${(myKols.reduce((a, k) => a + k.numListeners, 0) / 1000).toFixed(0)}k`, color: "cyan" },
                      { icon: <Zap className="w-3 h-3" />, label: "Avg influence", value: myKols.length ? Math.round(myKols.reduce((a, k) => a + k.influence, 0) / myKols.length).toLocaleString() : "—", color: "yellow" },
                      { icon: <TrendingUp className="w-3 h-3" />, label: "Top handle", value: myKols[0] ? `@${myKols[0].handle.slice(0, 12)}` : "—", color: "green" },
                    ].map(({ icon, label, value, color }) => (
                      <div key={label} className="flex items-center gap-2 py-1">
                        <span style={{ color: `var(--${color})` }} className="flex-shrink-0">{icon}</span>
                        <div className="flex-1 min-w-0">
                          <div className="font-mono text-[9px] text-muted-fg">{label}</div>
                          <div className="font-mono text-[10px] font-bold text-text truncate">{value}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Top Subscriptions preview */}
                <div className="panel">
                  <header className="px-3 pt-3 pb-2">
                    <span className="panel-label text-[10px]" style={{ "--tick": "var(--purple)" } as React.CSSProperties}>
                      Top Subscriptions
                    </span>
                  </header>
                  <div className="px-3 pb-3 space-y-1">
                    <div className="font-mono text-[9px] text-muted-fg mb-1.5">
                      Most influential from CMC
                    </div>
                    {kolsWithInfluence.slice(0, 5).map((k) => (
                      <div key={k.handle} className="flex items-center gap-2">
                        <LiveDot color={isInMyList(k.handle) ? "green" : "yellow"} />
                        <a
                          href={xProfileUrl(k.handle)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-[10px] text-cyan hover:underline underline-offset-2 truncate flex-1"
                        >
                          @{k.handle}
                        </a>
                        {isInMyList(k.handle) && (
                          <span className="font-mono text-[8px] text-green/70 flex-shrink-0">tracked</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── ACTIVITY TAB ─── */}
      {tab === "activity" && (
        <>
          {/* Ongoing — open positions */}
          <Panel
            label="Ongoing Trades"
            tick="green"
            action={
              <span className={cn(
                "font-mono text-[10px] px-2 py-0.5 rounded border",
                typedPositions.length > 0
                  ? "text-green border-green/30 bg-green/8"
                  : "text-muted-fg border-border",
              )}>
                {positionsLoading ? "…" : `${typedPositions.length} open`}
              </span>
            }
          >
            {positionsLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-10 w-full rounded-lg" />
                <Skeleton className="h-10 w-full rounded-lg" />
              </div>
            ) : typedPositions.length === 0 ? (
              <div className="flex items-center gap-2 py-3 font-mono text-[11px] text-muted-fg">
                <span className="animate-pulse text-green">▮</span>
                0 active positions — monitoring for entries
              </div>
            ) : (
              <div className="space-y-2">
                {typedPositions.map((p) => {
                  const pnlPos = p.unrealized_pnl_usd >= 0;
                  return (
                    <div key={p._id} className="flex items-center gap-3 rounded-lg bg-bg/50 border border-border px-3 py-2.5">
                      <span className="font-mono font-bold text-cyan text-[13px] w-14">{p.symbol}</span>
                      <span className="font-mono text-[11px] text-muted-fg">{p.quantity.toFixed(6)}</span>
                      <span className="font-mono text-[11px] text-muted-fg ml-1">@ {usd(p.avg_entry_price)}</span>
                      <span className={cn("ml-auto font-mono text-[12px] font-bold", pnlPos ? "text-green" : "text-red")}>
                        {pnlPos ? "+" : ""}{usd(p.unrealized_pnl_usd)}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </Panel>

          {nextDecision && (() => {
            const isAllow = nextDecision.risk_verdict === "allow";
            const verdictColor = isAllow ? "var(--green)" : "var(--red)";
            return (
              <Panel label="Next Decision" tick="cyan">
                <div
                  className="rounded-lg border px-4 py-3 overflow-hidden"
                  style={{
                    borderColor: `color-mix(in oklab, ${verdictColor} 25%, var(--border))`,
                    background: `linear-gradient(135deg, color-mix(in oklab, ${verdictColor} 8%, transparent) 0%, transparent 60%), var(--bg)`,
                  }}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex flex-col gap-1">
                      <span className="font-mono text-[9px] tracking-[0.2em] uppercase text-muted-fg">Symbol</span>
                      <span className="font-mono font-bold text-cyan text-[15px] glow-cyan">{nextDecision.symbol}</span>
                    </div>
                    <div className="w-px h-8 bg-border mx-1" />
                    <div className="flex flex-col gap-1">
                      <span className="font-mono text-[9px] tracking-[0.2em] uppercase text-muted-fg">Regime</span>
                      <RegimeBadge regime={nextDecision.regime} />
                    </div>
                    <div className="ml-auto flex flex-col items-end gap-1">
                      <span className="font-mono text-[9px] tracking-[0.2em] uppercase text-muted-fg">Risk Verdict</span>
                      <span
                        className="font-display text-[18px] font-bold tracking-[0.12em] uppercase"
                        style={{ color: verdictColor, textShadow: `0 0 20px color-mix(in oklab, ${verdictColor} 60%, transparent)` }}
                      >
                        {nextDecision.risk_verdict}
                      </span>
                    </div>
                  </div>
                </div>
              </Panel>
            );
          })()}

          {(ongoing.length > 0 || pending.length > 0) && (
            <Panel
              label="Pending Commands"
              tick="yellow"
              action={
                <span className="font-mono text-[10px] text-yellow border border-yellow/30 bg-yellow/8 px-2 py-0.5 rounded">
                  {ongoing.length + pending.length} queued
                </span>
              }
            >
              <div className="space-y-1.5">
                {[...ongoing, ...pending].map((c) => (
                  <div key={c._id} className="flex items-center gap-3 rounded-lg bg-bg/40 border border-border px-3 py-2.5 font-mono">
                    <span className="text-[11px] text-muted-fg/50 select-none">&gt;_</span>
                    <span className="text-[12px] text-text flex-1">{c.command_type}</span>
                    <span className={cn("flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border", STATUS_STYLE[c.status] ?? STATUS_STYLE["queued"])}>
                      {STATUS_ICON[c.status]}{c.status}
                    </span>
                    <span className="text-[10px] text-muted-fg w-16 text-right">{ts(c.queued_at_ms)}</span>
                  </div>
                ))}
              </div>
            </Panel>
          )}

          {recent.length > 0 && (
            <Panel label="Command History" tick="cyan">
              <div className="space-y-1.5">
                {recent.map((c) => (
                  <div key={c._id} className="flex items-center gap-3 rounded-lg bg-bg/40 border border-border px-3 py-2.5 font-mono">
                    <span className="text-[11px] text-muted-fg/50 select-none">&gt;_</span>
                    <span className="text-[12px] text-text flex-1">{c.command_type}</span>
                    {c.error && <span className="text-[10px] text-red truncate max-w-[180px]">{c.error}</span>}
                    <span className={cn("flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border", STATUS_STYLE[c.status] ?? STATUS_STYLE["done"])}>
                      {STATUS_ICON[c.status]}{c.status}
                    </span>
                    <span className="text-[10px] text-muted-fg w-16 text-right">{ts(c.queued_at_ms)}</span>
                  </div>
                ))}
              </div>
            </Panel>
          )}

          {!commandsLoading && ongoing.length === 0 && pending.length === 0 && recent.length === 0 && (
            <Panel label="Command History" tick="cyan">
              <div className="flex items-center gap-3 py-3 font-mono">
                <span className="text-[11px] text-muted-fg/50 select-none">&gt;_</span>
                <p className="text-[12px] text-muted-fg">No commands dispatched yet.</p>
              </div>
            </Panel>
          )}
        </>
      )}
    </div>
  );
}
