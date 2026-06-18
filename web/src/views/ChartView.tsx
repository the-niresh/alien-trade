import { useState } from "react";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "../components/Panel";
import { TradingChart } from "../components/TradingChart";
import { cn } from "@/lib/utils";

const SYMBOLS = ["ETH", "CAKE", "UNI", "LINK", "AAVE"] as const;
type Sym = (typeof SYMBOLS)[number];

export function ChartView() {
  const [symbol, setSymbol] = useState<Sym>("ETH");

  const ticks  = useQuery(api.priceTicks.forSymbol, { symbol, limit: 200 }) ?? [];
  const trades = useQuery(api.trades.recent, { limit: 100 }) ?? [];

  const filteredTrades = trades.filter((t) => t.symbol === symbol);

  return (
    <div className="max-w-[1180px] mx-auto space-y-4">
      <div className="mb-2">
        <div className="font-mono text-[10px] text-muted-fg tracking-[0.22em] uppercase mb-1.5 flex items-center gap-2">
          <span
            className="h-[2px] w-4 bg-cyan rounded-full inline-block"
            style={{ boxShadow: "0 0 6px var(--cyan)" }}
          />
          Price Chart
        </div>
        <h1 className="font-display text-[22px] font-bold tracking-wide text-text">Chart</h1>
      </div>

      {/* Symbol pills */}
      <div className="flex gap-2 flex-wrap">
        {SYMBOLS.map((s) => (
          <button
            key={s}
            onClick={() => setSymbol(s)}
            className={cn(
              "font-mono text-[11px] px-3 py-1.5 rounded-lg border transition-colors cursor-pointer",
              symbol === s
                ? "bg-cyan/10 border-cyan/30 text-cyan"
                : "border-border text-muted-fg hover:border-border-hi hover:text-text",
            )}
          >
            {s}
          </button>
        ))}
      </div>

      <Panel
        label={`${symbol} / USDT`}
        tick="cyan"
        action={
          <span className="font-mono text-[10px] text-muted-fg">
            {ticks.length} ticks · {filteredTrades.length} trades
          </span>
        }
      >
        <TradingChart ticks={ticks} trades={filteredTrades} height={480} />
      </Panel>
    </div>
  );
}
