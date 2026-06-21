import { useState, useMemo } from "react";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { cn } from "@/lib/utils";
import { usd, ts } from "../lib/formatters";
import {
  ArrowUpRight, ArrowDownRight, ExternalLink, Clock,
  CheckCircle2, XCircle, Loader2, RefreshCw, Filter,
} from "lucide-react";

type Tab = "trades" | "commands" | "ledger";

const BSCSCAN = "https://bscscan.com/tx/";

const MODE_STYLE: Record<string, string> = {
  mainnet: "text-orange-400 border-orange-400/30 bg-orange-400/10",
  paper:   "text-cyan-400   border-cyan-400/30   bg-cyan-400/10",
  testnet: "text-purple-400 border-purple-400/30 bg-purple-400/10",
};

const STATUS_STYLE: Record<string, string> = {
  queued:  "text-yellow-400 bg-yellow-400/10 border-yellow-400/30",
  running: "text-cyan-400   bg-cyan-400/10   border-cyan-400/30",
  done:    "text-green-400  bg-green-400/10  border-green-400/30",
  failed:  "text-red-400    bg-red-400/10    border-red-400/30",
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  queued:  <Clock className="w-3 h-3" />,
  running: <Loader2 className="w-3 h-3 animate-spin" />,
  done:    <CheckCircle2 className="w-3 h-3" />,
  failed:  <XCircle className="w-3 h-3" />,
};

function Chip({
  label, active, onClick, color,
}: { label: string; active: boolean; onClick: () => void; color?: string }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-2.5 py-1 rounded-full text-xs border transition-all",
        active
          ? color ?? "border-cyan-400 bg-cyan-400/15 text-cyan-300"
          : "border-white/15 bg-white/5 text-white/40 hover:text-white/70 hover:border-white/30",
      )}
    >
      {label}
    </button>
  );
}

function TxLink({ hash }: { hash?: string }) {
  if (!hash) return <span className="text-white/30 text-xs">—</span>;
  const short = hash.slice(0, 8) + "…" + hash.slice(-6);
  return (
    <a
      href={BSCSCAN + hash}
      target="_blank"
      rel="noopener noreferrer"
      className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
    >
      {short}<ExternalLink className="w-3 h-3" />
    </a>
  );
}

function FilterBar({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-2 py-2 px-1">
      <Filter className="w-3.5 h-3.5 text-white/30 shrink-0" />
      {children}
    </div>
  );
}

function Divider() {
  return <span className="w-px h-4 bg-white/10 shrink-0" />;
}

export function HistoryView() {
  const [tab, setTab] = useState<Tab>("trades");

  // ── filter state ────────────────────────────────────────────────────
  // trades
  const [tradeMode, setTradeMode]   = useState<string>("all");
  const [tradeSide, setTradeSide]   = useState<string>("all");
  const [tradeSymbol, setTradeSymbol] = useState<string>("all");

  // commands
  const [cmdType,   setCmdType]   = useState<string>("all");
  const [cmdStatus, setCmdStatus] = useState<string>("all");

  // ledger
  const [ledgerDir, setLedgerDir] = useState<string>("all"); // all / gain / loss

  // ── data ────────────────────────────────────────────────────────────
  const tradesRaw   = useQuery(api.trades.recent,      { limit: 200 });
  const commandsRaw = useQuery(api.agentCommands.list, { limit: 100 });
  const ledgerRaw   = useQuery(api.ledger.history,     { limit: 200 });

  // ── derived filter options (from actual data) ────────────────────────
  const tradeSymbols = useMemo(() => {
    if (!tradesRaw) return [];
    return [...new Set(tradesRaw.map((t) => t.symbol))].sort();
  }, [tradesRaw]);

  const cmdTypes = useMemo(() => {
    if (!commandsRaw) return [];
    return [...new Set((commandsRaw as any[]).map((c) => c.command_type))].sort();
  }, [commandsRaw]);

  // ── filtered slices ──────────────────────────────────────────────────
  const trades = useMemo(() => {
    if (!tradesRaw) return tradesRaw;
    return tradesRaw.filter((t) => {
      if (tradeMode   !== "all" && t.mode   !== tradeMode)   return false;
      if (tradeSide   !== "all" && t.side   !== tradeSide)   return false;
      if (tradeSymbol !== "all" && t.symbol !== tradeSymbol) return false;
      return true;
    });
  }, [tradesRaw, tradeMode, tradeSide, tradeSymbol]);

  const commands = useMemo(() => {
    if (!commandsRaw) return commandsRaw;
    return (commandsRaw as any[]).filter((c) => {
      if (cmdType   !== "all" && c.command_type !== cmdType)   return false;
      if (cmdStatus !== "all" && c.status       !== cmdStatus) return false;
      return true;
    });
  }, [commandsRaw, cmdType, cmdStatus]);

  const ledger = useMemo(() => {
    if (!ledgerRaw) return ledgerRaw;
    return ledgerRaw.filter((l) => {
      if (ledgerDir === "gain" && l.realized_pnl_usd <  0) return false;
      if (ledgerDir === "loss" && l.realized_pnl_usd >= 0) return false;
      return true;
    });
  }, [ledgerRaw, ledgerDir]);

  // ── tab count shows filtered count vs total ──────────────────────────
  const tabs: { id: Tab; label: string; count?: number; total?: number }[] = [
    { id: "trades",   label: "Trades",   count: trades?.length,   total: tradesRaw?.length   },
    { id: "commands", label: "Commands", count: commands?.length, total: commandsRaw?.length },
    { id: "ledger",   label: "Ledger",   count: ledger?.length,   total: ledgerRaw?.length   },
  ];

  return (
    <div className="p-4 space-y-3">
      {/* Tab bar */}
      <div className="flex gap-1 border-b border-white/10">
        {tabs.map((t) => {
          const filtered = t.count !== undefined && t.total !== undefined && t.count !== t.total;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
                tab === t.id
                  ? "border-cyan-400 text-cyan-400"
                  : "border-transparent text-white/50 hover:text-white/80",
              )}
            >
              {t.label}
              {t.count !== undefined && (
                <span className="ml-2 text-xs text-white/30">
                  {filtered ? `${t.count}/${t.total}` : `(${t.count})`}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ── Trades tab ─────────────────────────────────────────────────── */}
      {tab === "trades" && (
        <>
          <FilterBar>
            {/* Mode */}
            <span className="text-white/30 text-xs">Mode</span>
            {(["all", "mainnet", "paper", "testnet"] as const).map((m) => (
              <Chip
                key={m}
                label={m === "all" ? "All" : m}
                active={tradeMode === m}
                onClick={() => setTradeMode(m)}
                color={m !== "all" ? cn("border", MODE_STYLE[m]) : undefined}
              />
            ))}
            <Divider />
            {/* Side */}
            <span className="text-white/30 text-xs">Side</span>
            <Chip label="All"  active={tradeSide === "all"}  onClick={() => setTradeSide("all")} />
            <Chip label="Buy"  active={tradeSide === "buy"}  onClick={() => setTradeSide("buy")}
              color="border-green-500/40 bg-green-500/10 text-green-400" />
            <Chip label="Sell" active={tradeSide === "sell"} onClick={() => setTradeSide("sell")}
              color="border-red-500/40 bg-red-500/10 text-red-400" />
            {tradeSymbols.length > 0 && (
              <>
                <Divider />
                <span className="text-white/30 text-xs">Symbol</span>
                <Chip label="All" active={tradeSymbol === "all"} onClick={() => setTradeSymbol("all")} />
                {tradeSymbols.map((s) => (
                  <Chip key={s} label={s} active={tradeSymbol === s} onClick={() => setTradeSymbol(s)} />
                ))}
              </>
            )}
          </FilterBar>

          <Panel label="Trade History" className="overflow-x-auto">
            {trades === undefined ? (
              <div className="flex justify-center py-8"><RefreshCw className="animate-spin w-5 h-5 text-white/30" /></div>
            ) : trades.length === 0 ? (
              <p className="text-white/40 text-sm text-center py-8">No trades match the current filters.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-white/40 text-xs border-b border-white/8">
                    <th className="text-left py-2 pr-4">Time</th>
                    <th className="text-left py-2 pr-4">Symbol</th>
                    <th className="text-left py-2 pr-4">Side</th>
                    <th className="text-right py-2 pr-4">Size</th>
                    <th className="text-right py-2 pr-4">Fill Price</th>
                    <th className="text-right py-2 pr-4">Fee+Gas</th>
                    <th className="text-left py-2 pr-4">Mode</th>
                    <th className="text-left py-2">Tx</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t) => (
                    <tr key={t._id} className="border-b border-white/5 hover:bg-white/3">
                      <td className="py-2 pr-4 text-white/50 whitespace-nowrap">{ts(t.timestamp_ms)}</td>
                      <td className="py-2 pr-4 font-mono text-white/80">{t.symbol}</td>
                      <td className="py-2 pr-4">
                        <span className={cn(
                          "flex items-center gap-1 font-semibold text-xs",
                          t.side === "buy" ? "text-green-400" : "text-red-400",
                        )}>
                          {t.side === "buy"
                            ? <ArrowUpRight className="w-3.5 h-3.5" />
                            : <ArrowDownRight className="w-3.5 h-3.5" />}
                          {t.side.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2 pr-4 text-right font-mono">{usd(t.size_usd)}</td>
                      <td className="py-2 pr-4 text-right font-mono">{usd(t.fill_price)}</td>
                      <td className="py-2 pr-4 text-right font-mono text-white/60">
                        {usd(t.fee_usd + t.gas_usd)}
                      </td>
                      <td className="py-2 pr-4">
                        <span className={cn(
                          "text-xs px-1.5 py-0.5 rounded border",
                          MODE_STYLE[t.mode] ?? "text-white/40 border-white/20 bg-white/5",
                        )}>
                          {t.mode}
                        </span>
                      </td>
                      <td className="py-2"><TxLink hash={t.tx_hash} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>
        </>
      )}

      {/* ── Commands tab ───────────────────────────────────────────────── */}
      {tab === "commands" && (
        <>
          <FilterBar>
            {/* Type */}
            <span className="text-white/30 text-xs">Type</span>
            <Chip label="All" active={cmdType === "all"} onClick={() => setCmdType("all")} />
            {cmdTypes.map((t) => (
              <Chip key={t} label={t} active={cmdType === t} onClick={() => setCmdType(t)} />
            ))}
            <Divider />
            {/* Status */}
            <span className="text-white/30 text-xs">Status</span>
            {(["all", "queued", "running", "done", "failed"] as const).map((s) => (
              <Chip
                key={s}
                label={s === "all" ? "All" : s}
                active={cmdStatus === s}
                onClick={() => setCmdStatus(s)}
                color={s !== "all" ? cn("border", STATUS_STYLE[s]) : undefined}
              />
            ))}
          </FilterBar>

          <Panel label="Operator Command History" className="overflow-x-auto">
            {commands === undefined ? (
              <div className="flex justify-center py-8"><RefreshCw className="animate-spin w-5 h-5 text-white/30" /></div>
            ) : commands.length === 0 ? (
              <p className="text-white/40 text-sm text-center py-8">No commands match the current filters.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-white/40 text-xs border-b border-white/8">
                    <th className="text-left py-2 pr-4">Time</th>
                    <th className="text-left py-2 pr-4">Type</th>
                    <th className="text-left py-2 pr-4">Params</th>
                    <th className="text-left py-2 pr-4">Status</th>
                    <th className="text-left py-2">Result / Error</th>
                  </tr>
                </thead>
                <tbody>
                  {commands.map((c) => {
                    let paramsDisplay = "";
                    try {
                      const p = JSON.parse(c.params || "{}");
                      if (c.command_type === "convert") {
                        paramsDisplay = `${p.from_token} → ${p.to_token}  $${Number(p.usd ?? 0).toFixed(2)}`;
                      } else if (c.command_type === "withdraw") {
                        paramsDisplay = `${p.amount} ${p.token} → ${(p.to_address || "").slice(0, 10)}…`;
                      } else {
                        paramsDisplay = Object.keys(p).length ? JSON.stringify(p) : "{}";
                      }
                    } catch { paramsDisplay = c.params || ""; }

                    return (
                      <tr key={c._id} className="border-b border-white/5 hover:bg-white/3">
                        <td className="py-2 pr-4 text-white/50 whitespace-nowrap">{ts(c.queued_at_ms)}</td>
                        <td className="py-2 pr-4 font-mono text-white/80">{c.command_type}</td>
                        <td className="py-2 pr-4 text-white/60 text-xs max-w-[200px] truncate">{paramsDisplay}</td>
                        <td className="py-2 pr-4">
                          <span className={cn(
                            "flex items-center gap-1 text-xs px-1.5 py-0.5 rounded border w-fit",
                            STATUS_STYLE[c.status] ?? "text-white/40 border-white/20",
                          )}>
                            {STATUS_ICON[c.status]}
                            {c.status}
                          </span>
                        </td>
                        <td className="py-2 text-xs max-w-[260px]">
                          {c.error ? (
                            <span className="text-red-400 truncate block" title={c.error}>{c.error}</span>
                          ) : c.result ? (
                            <span className="text-green-400/70 truncate block">{c.result}</span>
                          ) : (
                            <span className="text-white/20">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </Panel>
        </>
      )}

      {/* ── Ledger tab ─────────────────────────────────────────────────── */}
      {tab === "ledger" && (
        <>
          <FilterBar>
            <span className="text-white/30 text-xs">Trade PnL</span>
            <Chip label="All"        active={ledgerDir === "all"}  onClick={() => setLedgerDir("all")} />
            <Chip label="Profitable" active={ledgerDir === "gain"} onClick={() => setLedgerDir("gain")}
              color="border-green-500/40 bg-green-500/10 text-green-400" />
            <Chip label="Losing"     active={ledgerDir === "loss"} onClick={() => setLedgerDir("loss")}
              color="border-red-500/40 bg-red-500/10 text-red-400" />
          </FilterBar>

          <Panel label="PnL Ledger" className="overflow-x-auto">
            {ledger === undefined ? (
              <div className="flex justify-center py-8"><RefreshCw className="animate-spin w-5 h-5 text-white/30" /></div>
            ) : ledger.length === 0 ? (
              <p className="text-white/40 text-sm text-center py-8">No ledger entries match the current filters.</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-white/40 text-xs border-b border-white/8">
                    <th className="text-left py-2 pr-4">Time</th>
                    <th className="text-right py-2 pr-4">Realized PnL</th>
                    <th className="text-right py-2 pr-4">Cumulative PnL</th>
                    <th className="text-right py-2 pr-4">Fees+Gas</th>
                    <th className="text-right py-2 pr-4">Peak Equity</th>
                    <th className="text-right py-2">Drawdown</th>
                  </tr>
                </thead>
                <tbody>
                  {ledger.map((l) => (
                    <tr key={l._id} className="border-b border-white/5 hover:bg-white/3">
                      <td className="py-2 pr-4 text-white/50 whitespace-nowrap">{ts(l.timestamp_ms)}</td>
                      <td className={cn(
                        "py-2 pr-4 text-right font-mono",
                        l.realized_pnl_usd >= 0 ? "text-green-400" : "text-red-400",
                      )}>
                        {l.realized_pnl_usd >= 0 ? "+" : ""}{usd(l.realized_pnl_usd)}
                      </td>
                      <td className={cn(
                        "py-2 pr-4 text-right font-mono font-semibold",
                        l.cumulative_pnl_usd >= 0 ? "text-green-400" : "text-red-400",
                      )}>
                        {l.cumulative_pnl_usd >= 0 ? "+" : ""}{usd(l.cumulative_pnl_usd)}
                      </td>
                      <td className="py-2 pr-4 text-right font-mono text-white/50">
                        {usd(l.cumulative_fees_usd + l.cumulative_gas_usd)}
                      </td>
                      <td className="py-2 pr-4 text-right font-mono text-white/70">
                        {usd(l.peak_equity_usd)}
                      </td>
                      <td className={cn(
                        "py-2 text-right font-mono",
                        l.current_drawdown_pct > 0.05 ? "text-red-400" : "text-white/60",
                      )}>
                        {(l.current_drawdown_pct * 100).toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>
        </>
      )}
    </div>
  );
}
