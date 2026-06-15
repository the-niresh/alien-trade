import { motion } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Sparkline } from "./Sparkline";
import { usd, pct, elapsed } from "../lib/formatters";

type Position = {
  _id: string;
  symbol: string;
  quantity: number;
  avg_entry_price: number;
  current_price: number;
  current_value_usd: number;
  unrealized_pnl_usd: number;
  updated_ms: number;
};

export function PositionCard({ position }: { position: Position }) {
  const rawTicks = useQuery(api.priceTicks.forSymbol, { symbol: position.symbol, limit: 24 }) ?? [];
  const ticks = [...rawTicks].reverse().map((t) => ({ t: t.timestamp_ms, p: t.price }));

  const positive = position.unrealized_pnl_usd >= 0;
  const pnlPct = position.avg_entry_price > 0
    ? (position.current_price - position.avg_entry_price) / position.avg_entry_price
    : 0;
  const sign = positive ? "+" : "";

  return (
    <motion.div
      className={`position-card ${positive ? "position-card--win" : "position-card--loss"}`}
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
    >
      <div className="position-card__header">
        <span className="position-card__symbol">{position.symbol}</span>
        <span className="position-card__side">LONG</span>
      </div>

      <Sparkline ticks={ticks} positive={positive} />

      <div className="position-card__prices">
        <div className="price-col">
          <div className="price-label">Entry</div>
          <div className="price-value">{usd(position.avg_entry_price)}</div>
        </div>
        <div className="price-arrow">→</div>
        <div className="price-col" style={{ textAlign: "right" }}>
          <div className="price-label">Now</div>
          <motion.div
            className="price-value"
            key={position.current_price}
            animate={{ scale: [1.07, 1] }}
            transition={{ duration: 0.28 }}
          >
            {usd(position.current_price)}
          </motion.div>
        </div>
      </div>

      <div className="position-card__stats">
        <span className="position-card__size">{usd(position.current_value_usd)}</span>
        <motion.span
          className={`position-card__pnl ${positive ? "pnl--pos" : "pnl--neg"}`}
          key={position.unrealized_pnl_usd}
          animate={{ scale: [1.08, 1] }}
          transition={{ duration: 0.28 }}
        >
          {sign}{usd(position.unrealized_pnl_usd)} ({sign}{pct(pnlPct)})
        </motion.span>
      </div>

      <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 8 }}>
        Updated {elapsed(position.updated_ms)} ago
      </div>
    </motion.div>
  );
}
