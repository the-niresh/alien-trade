import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import {
  Area, AreaChart, CartesianGrid,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { ts } from "../lib/formatters";

export function RealizedPnlChart() {
  const raw = useQuery(api.ledger.history, { limit: 100 }) ?? [];
  const data = [...raw].reverse().map((r) => ({
    t:   r.timestamp_ms,
    pnl: Number(r.realized_pnl_usd.toFixed(4)),
  }));

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
        <span className="font-mono text-[11px] tracking-[0.16em] text-green/70 uppercase">
          <span className="animate-pulse">▮</span> awaiting telemetry
        </span>
        <p className="text-[13px] text-muted-fg">Per-trade PnL plots after the first trade cycle.</p>
      </div>
    );
  }

  const lastPnl = data[data.length - 1]?.pnl ?? 0;
  const positive = lastPnl >= 0;
  const color = positive ? "var(--green)" : "var(--red)";
  const gradientId = positive ? "rpnl-green" : "rpnl-red";

  return (
    <ResponsiveContainer width="100%" height={180}>
      <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="rpnl-green" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"  stopColor="var(--green)" stopOpacity={0.22} />
            <stop offset="100%" stopColor="var(--green)" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="rpnl-red" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"  stopColor="var(--red)" stopOpacity={0.22} />
            <stop offset="100%" stopColor="var(--red)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="2 4" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="t"
          tickFormatter={(v) => ts(Number(v))}
          tick={{ fontSize: 10, fill: "var(--muted)" }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "var(--muted)" }}
          tickFormatter={(v) => `$${v}`}
          tickLine={false}
          axisLine={false}
          width={52}
        />
        <Tooltip
          contentStyle={{
            background: "var(--surface)",
            border: "1px solid var(--border-hi)",
            borderRadius: 8,
            fontSize: 12,
            fontFamily: "var(--font-mono)",
          }}
          labelFormatter={(l) => ts(Number(l))}
          formatter={(val) => {
            const n = Number(val);
            return [`$${n.toFixed(4)}`, "Realized PnL"];
          }}
        />
        <Area
          type="monotone"
          dataKey="pnl"
          name="Realized PnL"
          stroke={color}
          fill={`url(#${gradientId})`}
          strokeWidth={2}
          dot={false}
          style={{ filter: `drop-shadow(0 0 4px color-mix(in oklab, ${color} 40%, transparent))` }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
