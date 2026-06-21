import { useState, useEffect } from "react";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { TradingChart } from "../components/TradingChart";
import { cn } from "@/lib/utils";

const SYMBOLS = ["ETH", "CAKE", "UNI", "LINK", "AAVE", "FLOKI", "SHIB", "AVAX", "FET"] as const;
type Sym = (typeof SYMBOLS)[number];

const BINANCE_PAIR: Record<Sym, string> = {
  ETH:   "ETHUSDT",
  CAKE:  "CAKEUSDT",
  UNI:   "UNIUSDT",
  LINK:  "LINKUSDT",
  AAVE:  "AAVEUSDT",
  FLOKI: "FLOKIUSDT",
  SHIB:  "SHIBUSDT",
  AVAX:  "AVAXUSDT",
  FET:   "FETUSDT",
};

type PriceTick = { timestamp_ms: number; price: number };

async function fetchBinanceHistory(symbol: Sym, limit = 200): Promise<PriceTick[]> {
  const pair = BINANCE_PAIR[symbol];
  const url = `https://api.binance.com/api/v3/klines?symbol=${pair}&interval=1h&limit=${limit}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Binance ${res.status}`);
  const data = await res.json() as [number, string, string, string, string, ...unknown[]][];
  return data.map(([openTime, , , , close]) => ({
    timestamp_ms: openTime,
    price: parseFloat(close as string),
  }));
}

function formatPrice(price: number): string {
  if (price >= 1000)  return price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (price >= 1)     return price.toFixed(4);
  if (price >= 0.001) return price.toFixed(6);
  return price.toFixed(8);
}

type Props = {
  symbol?: string;
  onSymbolChange?: (s: string) => void;
};

export function MarketsView({ symbol: propSymbol, onSymbolChange }: Props = {}) {
  const [symbol, setSymbol] = useState<Sym>((propSymbol as Sym) ?? "ETH");

  useEffect(() => {
    if (propSymbol && SYMBOLS.includes(propSymbol as Sym) && propSymbol !== symbol) {
      setSymbol(propSymbol as Sym);
    }
  }, [propSymbol]);
  const [fallbackTicks, setFallbackTicks] = useState<PriceTick[]>([]);
  const [fallbackLoading, setFallbackLoading] = useState(false);
  const [fallbackError, setFallbackError] = useState("");
  const [source, setSource] = useState<"convex" | "binance">("convex");

  const convexTicks = useQuery(api.priceTicks.forSymbol, { symbol, limit: 200 }) ?? [];
  const trades      = useQuery(api.trades.recent, { limit: 100 }) ?? [];
  const filteredTrades = trades.filter((t) => t.symbol === symbol);

  useEffect(() => {
    if (convexTicks.length >= 2) {
      setSource("convex");
      setFallbackTicks([]);
      return;
    }
    setFallbackLoading(true);
    setFallbackError("");
    fetchBinanceHistory(symbol)
      .then((ticks) => { setFallbackTicks(ticks); setSource("binance"); })
      .catch((e) => setFallbackError(String(e)))
      .finally(() => setFallbackLoading(false));
  }, [symbol, convexTicks.length]);

  const ticks = convexTicks.length >= 2 ? convexTicks : fallbackTicks;

  // Compute current price + 24h change from ticks (sorted ascending)
  const sorted = [...ticks].sort((a, b) => a.timestamp_ms - b.timestamp_ms);
  const currentPrice = sorted.length > 0 ? sorted[sorted.length - 1].price : null;
  const price24hAgo  = sorted.length > 1 ? sorted[0].price : null;
  const change24h    = currentPrice && price24hAgo
    ? ((currentPrice - price24hAgo) / price24hAgo) * 100
    : null;
  const priceUp = change24h !== null ? change24h >= 0 : true;

  return (
    <div className="max-w-[1180px] mx-auto space-y-4">
      {/* Header row: title + live price */}
      <div className="flex items-end justify-between">
        <div>
          <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
            <span className="h-[2px] w-4 bg-cyan rounded-full inline-block" style={{ boxShadow: "0 0 6px var(--cyan)" }} />
            Markets
          </div>
          <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Markets</h1>
        </div>

        {/* Current price + change — prominent display */}
        {currentPrice !== null && (
          <div className="text-right">
            <div className={cn(
              "font-display text-[28px] font-bold tabular-nums leading-none",
              priceUp ? "text-green glow-green" : "text-red",
            )}>
              ${formatPrice(currentPrice)}
            </div>
            {change24h !== null && (
              <div className={cn(
                "font-mono text-[12px] mt-1",
                priceUp ? "text-green/80" : "text-red/80",
              )}>
                {priceUp ? "▲" : "▼"} {Math.abs(change24h).toFixed(2)}%
                <span className="text-muted-fg ml-1.5">
                  {source === "binance" ? "200h range" : "period range"}
                </span>
              </div>
            )}
          </div>
        )}
        {fallbackLoading && (
          <div className="font-display text-[28px] font-bold text-muted-fg animate-pulse">
            —
          </div>
        )}
      </div>

      {/* Symbol pills */}
      <div className="flex gap-2 flex-wrap">
        {SYMBOLS.map((s) => (
          <button key={s} onClick={() => { setSymbol(s); onSymbolChange?.(s); }}
            className={cn(
              "font-mono text-[11px] px-3 py-1.5 rounded-lg border transition-colors cursor-pointer",
              symbol === s
                ? "bg-cyan/10 border-cyan/30 text-cyan"
                : "border-border text-muted-fg hover:border-border-hi hover:text-text",
            )}>
            {s}
          </button>
        ))}
      </div>

      <Panel
        label={`${symbol} / USDT`}
        tick="cyan"
        action={
          <span className="font-mono text-[10px] text-muted-fg flex items-center gap-2">
            {source === "binance" && !fallbackLoading && (
              <span className="text-yellow/70">Binance 1h · last 200 candles</span>
            )}
            {fallbackLoading && <span className="animate-pulse">Loading…</span>}
            {!fallbackLoading && ticks.length > 0 && (
              <span>{ticks.length} ticks · {filteredTrades.length} trades</span>
            )}
          </span>
        }
      >
        {fallbackError ? (
          <div className="flex items-center justify-center font-mono text-[12px] text-red" style={{ height: 480 }}>
            Failed to load price data: {fallbackError}
          </div>
        ) : (
          <TradingChart ticks={ticks} trades={filteredTrades} height={480} />
        )}
      </Panel>
    </div>
  );
}
