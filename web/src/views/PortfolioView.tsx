import { useState } from "react";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { RealizedPnlChart } from "../components/RealizedPnlChart";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { usd, pct, elapsed, ts } from "../lib/formatters";

type Period = "1d" | "7d" | "30d" | "max";
type BottomTab = "positions" | "trades";

export function PortfolioView() {
  const [period, setPeriod] = useState<Period>("max");
  const [bottomTab, setBottomTab] = useState<BottomTab>("trades");

  const wallet    = useQuery(api.walletState.get);
  const ledger    = useQuery(api.ledger.latest);
  const scorecard = useQuery(api.scorecard.get);
  const positions = useQuery(api.positions.open) ?? [];
  const trades    = useQuery(api.trades.recent, { limit: 50 }) ?? [];

  const pnlVal     = ledger?.cumulative_pnl_usd ?? 0;
  const pnlPos     = pnlVal > 0;   // strictly positive — zero is neutral
  const pnlNeg     = pnlVal < 0;
  const totalVal   = wallet?.total_usd ?? 0;
  const allocUsdt  = totalVal > 0 ? (wallet?.usdt ?? 0) / totalVal : 0;
  const allocEth   = totalVal > 0 ? (totalVal - (wallet?.usdt ?? 0) - (wallet?.bnb_usd ?? 0)) / totalVal : 0;
  const allocBnb   = totalVal > 0 ? (wallet?.bnb_usd ?? 0) / totalVal : 0;

  return (
    <div className="max-w-[920px] mx-auto space-y-3.5">

      {/* ── Page header ── */}
      <div className="mb-0.5 flex items-end justify-between">
        <div>
          <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
            <span className="relative flex h-2 w-2 shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green opacity-60" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green" style={{ boxShadow: "0 0 6px var(--green)" }} />
            </span>
            TWAK Self-Custody · Live
          </div>
          <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Portfolio</h1>
        </div>
        {wallet && (
          <span className="font-mono text-[10px] text-muted-fg">
            synced {elapsed(wallet.updated_ms)} ago
          </span>
        )}
      </div>

      {/* ── Hero stats: 3-column ── */}
      <div className="grid grid-cols-3 gap-3 max-sm:grid-cols-1">

        {/* Total Value */}
        <section className="panel panel-interactive relative overflow-hidden">
          <div className="absolute inset-0 pointer-events-none tone-wash-neutral rounded-xl" />
          <div className="relative px-3.5 pt-3.5 pb-3.5">
            <p className="font-mono text-[9.5px] text-muted-fg tracking-[0.2em] uppercase mb-2.5 flex items-center gap-1.5">
              <span className="h-[2px] w-2.5 bg-green/50 rounded-full inline-block" />
              Total Value
            </p>
            {wallet === undefined ? (
              <Skeleton className="h-10 w-32 bg-elevated mt-1" />
            ) : wallet === null ? (
              <p className="font-mono text-[12px] text-muted-fg py-2">// awaiting first cycle</p>
            ) : (
              <>
                <div className="font-display text-[30px] font-bold text-text tabular-nums leading-none">
                  {usd(wallet.total_usd)}
                </div>
                <p className="font-mono text-[10px] text-muted-fg mt-2">
                  updated {elapsed(wallet.updated_ms)} ago · auto-synced
                </p>
              </>
            )}
          </div>
        </section>

        {/* Cumulative PnL */}
        <section className="panel panel-interactive relative overflow-hidden">
          {pnlPos && <div className="absolute inset-0 pointer-events-none rounded-xl tone-wash-positive opacity-70" />}
          {pnlNeg && <div className="absolute inset-0 pointer-events-none rounded-xl tone-wash-negative opacity-70" />}
          <div className="relative px-3.5 pt-3.5 pb-3.5">
            <p className="font-mono text-[9.5px] text-muted-fg tracking-[0.2em] uppercase mb-2.5 flex items-center gap-1.5">
              <span className={cn(
                "h-[2px] w-2.5 rounded-full inline-block",
                pnlPos ? "bg-green/50" : pnlNeg ? "bg-red/50" : "bg-muted-fg/40",
              )} />
              Cumulative PnL
            </p>
            {ledger === undefined ? (
              <Skeleton className="h-10 w-32 bg-elevated mt-1" />
            ) : (
              <>
                <div className={cn(
                  "font-display text-[30px] font-bold tabular-nums leading-none",
                  pnlPos ? "text-green glow-green" : pnlNeg ? "text-red glow-red" : "text-muted-fg",
                )}>
                  {pnlPos ? "+" : ""}
                  {usd(pnlVal)}
                </div>
                <div className="font-mono text-[10px] text-muted-fg mt-2 flex gap-2">
                  <span>↓ {pct(ledger?.current_drawdown_pct)} DD</span>
                  <span className="opacity-40">·</span>
                  <span>{scorecard?.n_trades ?? 0} trades</span>
                </div>
              </>
            )}
          </div>
        </section>

        {/* Risk metrics */}
        <section className="panel panel-interactive relative overflow-hidden">
          <div className="absolute inset-0 pointer-events-none tone-wash-neutral rounded-xl" />
          <div className="relative px-3.5 pt-3.5 pb-3.5">
            <p className="font-mono text-[9.5px] text-muted-fg tracking-[0.2em] uppercase mb-2.5 flex items-center gap-1.5">
              <span className="h-[2px] w-2.5 bg-cyan/50 rounded-full inline-block" />
              Risk Metrics
            </p>
            {scorecard === undefined ? (
              <div className="space-y-2 mt-1">
                {[0, 1, 2].map(i => <Skeleton key={i} className="h-4 w-full bg-elevated" />)}
              </div>
            ) : !scorecard || scorecard.n_trades === 0 ? (
              <p className="font-mono text-[11px] text-muted-fg py-2 leading-relaxed">
                // metrics populate<br />// after first trade
              </p>
            ) : (
              <div className="space-y-1.5">
                <InlineMetric label="Win Rate"      value={pct(scorecard.win_rate)}                   color={scorecard.win_rate >= 0.5 ? "green" : "red"} />
                <InlineMetric label="Profit Factor" value={scorecard.profit_factor.toFixed(2) + "×"}  color={scorecard.profit_factor >= 1 ? "green" : "red"} />
                <InlineMetric label="Sortino"       value={scorecard.sortino.toFixed(2)}              color="cyan" />
              </div>
            )}
          </div>
        </section>
      </div>

      {/* ── PnL Chart with period filter ── */}
      <Panel
        label="Realized PnL per Trade"
        tick="green"
        action={
          <div className="flex gap-0.5">
            {(["1d", "7d", "30d", "max"] as Period[]).map(p => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={cn(
                  "font-mono text-[9px] uppercase tracking-widest px-2 py-1 rounded transition-all duration-150",
                  period === p
                    ? "bg-green/15 text-green border border-green/25"
                    : "text-muted-fg hover:text-text border border-transparent",
                )}
              >
                {p}
              </button>
            ))}
          </div>
        }
      >
        <RealizedPnlChart period={period} />
      </Panel>

      {/* ── Performance breakdown + Holdings ── */}
      <div className="grid grid-cols-2 gap-3 max-md:grid-cols-1">

        {/* Performance breakdown */}
        <Panel label="Performance" tick="cyan">
          {scorecard === undefined ? (
            <div className="space-y-2.5">
              {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-5 w-full bg-elevated" />)}
            </div>
          ) : !scorecard || scorecard.n_trades === 0 ? (
            <p className="font-mono text-[11px] text-muted-fg py-4 text-center">
              // performance stats appear after the first closed trade
            </p>
          ) : (
            <div className="space-y-2">
              <PerfRow label="Expectancy / trade"  value={`${scorecard.expectancy_usd >= 0 ? "+" : ""}${usd(scorecard.expectancy_usd)}`}  positive={scorecard.expectancy_usd > 0} neutral={scorecard.expectancy_usd === 0} />
              <PerfRow label="Profit factor"        value={`${scorecard.profit_factor.toFixed(2)}×`}                                        positive={scorecard.profit_factor > 1}  neutral={scorecard.profit_factor === 0} />
              <PerfRow label="Worst trade"          value={usd(scorecard.worst_trade_usd)}                                                   positive={scorecard.worst_trade_usd > 0} neutral={scorecard.worst_trade_usd === 0} />
              <PerfRow label="Total fees + gas"     value={usd(scorecard.total_cost_usd)}                                                    neutral />
              <div className="pt-2 border-t border-border/60">
                <WinBar winRate={scorecard.win_rate} nTrades={scorecard.n_trades} />
              </div>
            </div>
          )}
        </Panel>

        {/* Holdings with allocation bars */}
        <Panel label="Holdings" tick="cyan">
          {wallet === undefined ? (
            <div className="space-y-3">
              {[0, 1, 2].map(i => <Skeleton key={i} className="h-10 w-full bg-elevated" />)}
            </div>
          ) : wallet === null ? (
            <p className="font-mono text-[11px] text-muted-fg py-2">// awaiting balance snapshot</p>
          ) : (
            <div>
              <AllocRow token="USDT" role="dry powder"    balance={wallet.usdt.toFixed(2)}    usdValue={wallet.usdt}                                       alloc={allocUsdt} color="green" warn={wallet.usdt < 1}    warnMsg="balance nearly depleted" />
              <AllocRow token="ETH"  role="open position" balance={wallet.eth.toFixed(6)}     usdValue={totalVal - (wallet.usdt) - (wallet.bnb_usd)}       alloc={allocEth}  color="cyan"  dim={wallet.eth === 0} />
              <AllocRow token="BNB"  role="gas reserve"   balance={wallet.bnb.toFixed(4)}     usdValue={wallet.bnb_usd}                                    alloc={allocBnb}  color="yellow" warn={wallet.bnb < 0.003} warnMsg="gas low — top up!" />
              <div className="flex justify-between items-center pt-2.5 mt-1 border-t border-border/60">
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-fg">Total</span>
                <span className="font-display text-[18px] font-bold text-green glow-green tabular-nums">{usd(wallet.total_usd)}</span>
              </div>
            </div>
          )}
        </Panel>
      </div>

      {/* ── Tabbed: Positions | Trades ── */}
      <div className="panel">
        {/* Custom tab header */}
        <div className="flex items-center justify-between gap-3 px-3.5 pt-3 pb-2 border-b border-border/60">
          <div className="flex gap-1">
            {([["positions", "Active Positions"], ["trades", "Recent Trades"]] as [BottomTab, string][]).map(([id, label]) => (
              <button
                key={id}
                onClick={() => setBottomTab(id)}
                className={cn(
                  "font-mono text-[9.5px] uppercase tracking-widest px-3 py-1.5 rounded transition-all duration-150",
                  bottomTab === id
                    ? "text-text bg-elevated border border-border-hi"
                    : "text-muted-fg hover:text-text border border-transparent",
                )}
              >
                {label}
                {id === "positions" && positions.length > 0 && (
                  <span className="ml-1.5 font-mono text-[8px] text-cyan border border-cyan/30 bg-cyan/10 px-1.5 py-0.5 rounded-full">
                    {positions.length}
                  </span>
                )}
              </button>
            ))}
          </div>
          <span className="font-mono text-[10px] text-muted-fg">
            {bottomTab === "positions" ? `${positions.length} active` : `${trades.length} shown`}
          </span>
        </div>

        <div className="px-3.5 pb-3.5 pt-2">
          {bottomTab === "positions" ? (
            positions.length === 0 ? (
              <p className="font-mono text-[12px] text-muted-fg py-6 text-center">
                <span className="opacity-50">// </span>no open positions
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-[13px]">
                  <thead>
                    <tr className="border-b border-border">
                      {["Symbol", "Qty", "Entry", "Current", "Value", "Unrealised PnL"].map(h => (
                        <th key={h} className={cn("font-mono text-[10px] text-muted-fg pb-2.5 uppercase tracking-widest", h === "Symbol" ? "text-left" : "text-right")}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map(p => {
                      const pos = p.unrealized_pnl_usd >= 0;
                      return (
                        <tr key={p._id} className="border-b border-border/40 hover:bg-elevated/40 transition-colors">
                          <td className="py-2.5 font-mono text-cyan font-bold">{p.symbol}</td>
                          <td className="py-2.5 font-mono text-text text-right tabular-nums">{p.quantity.toFixed(6)}</td>
                          <td className="py-2.5 font-mono text-muted-fg text-right tabular-nums">{usd(p.avg_entry_price)}</td>
                          <td className="py-2.5 font-mono text-text text-right tabular-nums">{usd(p.current_price)}</td>
                          <td className="py-2.5 font-mono text-text text-right tabular-nums">{usd(p.current_value_usd)}</td>
                          <td className={cn("py-2.5 font-mono font-bold text-right tabular-nums", pos ? "text-green" : "text-red")}>
                            {pos ? "+" : ""}{usd(p.unrealized_pnl_usd)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )
          ) : (
            trades.length === 0 ? (
              <p className="font-mono text-[12px] text-muted-fg py-6 text-center">
                <span className="opacity-50">// </span>no trades recorded yet
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-[13px]">
                  <thead>
                    <tr className="border-b border-border">
                      {["Time", "Symbol", "Side", "Size", "Fill Price", "Fee + Gas"].map(h => (
                        <th key={h} className={cn("font-mono text-[10px] text-muted-fg pb-2.5 uppercase tracking-widest", ["Time", "Symbol", "Side"].includes(h) ? "text-left" : "text-right")}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map(t => (
                      <tr key={t._id} className="border-b border-border/40 hover:bg-elevated/40 transition-colors">
                        <td className="py-2 font-mono text-[11px] text-muted-fg whitespace-nowrap">{ts(t.timestamp_ms)}</td>
                        <td className="py-2 font-mono font-bold text-cyan">{t.symbol}</td>
                        <td className="py-2">
                          <span className={cn(
                            "font-mono text-[9.5px] font-bold uppercase px-2 py-0.5 rounded-sm tracking-wide",
                            t.side === "buy"
                              ? "text-green bg-green/10 border border-green/25"
                              : "text-red bg-red/10 border border-red/25",
                          )}>
                            {t.side}
                          </span>
                        </td>
                        <td className="py-2 font-mono text-text text-right tabular-nums">{usd(t.size_usd)}</td>
                        <td className="py-2 font-mono text-text text-right tabular-nums">{usd(t.fill_price)}</td>
                        <td className="py-2 font-mono text-muted-fg text-right tabular-nums">{usd(t.fee_usd + t.gas_usd)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────────

function InlineMetric({ label, value, color }: { label: string; value: string; color: "green" | "red" | "cyan" }) {
  const colorClass = color === "green" ? "text-green" : color === "red" ? "text-red" : "text-cyan";
  return (
    <div className="flex justify-between items-center">
      <span className="font-mono text-[10px] text-muted-fg">{label}</span>
      <span className={cn("font-mono text-[12px] font-bold tabular-nums", colorClass)}>{value}</span>
    </div>
  );
}

function PerfRow({ label, value, positive, neutral }: { label: string; value: string; positive?: boolean; neutral?: boolean }) {
  const colorClass = neutral ? "text-muted-fg" : positive ? "text-green" : "text-red";
  return (
    <div className="flex justify-between items-center">
      <span className="font-mono text-[10px] text-muted-fg">{label}</span>
      <span className={cn("font-mono text-[11px] font-bold tabular-nums", colorClass)}>
        {value}
      </span>
    </div>
  );
}

function WinBar({ winRate, nTrades }: { winRate: number; nTrades: number }) {
  const wins   = Math.round(winRate * nTrades);
  const losses = nTrades - wins;
  const pct    = Math.round(winRate * 100);
  return (
    <div>
      <div className="flex justify-between font-mono text-[10px] text-muted-fg mb-1.5">
        <span>Win / Loss distribution</span>
        <span className="text-text">{wins}W · {losses}L</span>
      </div>
      <div className="h-1.5 rounded-full bg-elevated overflow-hidden flex gap-px">
        <div
          className="h-full rounded-l-full transition-all duration-700"
          style={{ width: `${pct}%`, background: "var(--green)", boxShadow: "0 0 5px var(--green)" }}
        />
        {losses > 0 && (
          <div className="h-full flex-1 rounded-r-full" style={{ background: "var(--red)", opacity: 0.5 }} />
        )}
      </div>
      <p className="font-mono text-[9.5px] text-muted-fg mt-1">{pct}% win rate</p>
    </div>
  );
}

function AllocRow({
  token, role, balance, usdValue, alloc, color, warn, warnMsg, dim,
}: {
  token: string;
  role: string;
  balance: string;
  usdValue: number;
  alloc: number;
  color: "green" | "cyan" | "yellow";
  warn?: boolean;
  warnMsg?: string;
  dim?: boolean;
}) {
  const colorVar  = color === "green" ? "var(--green)" : color === "cyan" ? "var(--cyan)" : "var(--yellow)";
  const textClass = color === "green" ? "text-green" : color === "cyan" ? "text-cyan" : "text-yellow";
  const pctWidth  = Math.max(alloc * 100, alloc > 0 ? 1.5 : 0);

  return (
    <div className={cn("py-2 border-b border-border/40 last:border-0", dim && "opacity-35")}>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className={cn("font-mono font-bold text-[13px]", textClass)}>{token}</span>
          <span className="font-mono text-[10px] text-muted-fg">{role}</span>
        </div>
        <div className="text-right">
          <div className={cn("font-mono font-bold text-[13px] tabular-nums", warn ? "text-red" : "text-text")}>{usd(usdValue)}</div>
          <div className="font-mono text-[9.5px] text-muted-fg tabular-nums">{balance}</div>
        </div>
      </div>
      <div className="h-[3px] rounded-full bg-elevated overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pctWidth}%`, background: colorVar, boxShadow: `0 0 5px ${colorVar}` }}
        />
      </div>
      {warn && warnMsg && (
        <p className="font-mono text-[9px] text-red mt-0.5">⚠ {warnMsg}</p>
      )}
    </div>
  );
}
