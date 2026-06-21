import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import {
  Area, CartesianGrid, ComposedChart, Line,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { ts } from "../lib/formatters";

export function EquityChart() {
  const raw = useQuery(api.ledger.history, { limit: 100 }) ?? [];
  const data = [...raw].reverse().map((r) => ({
    t:   r.timestamp_ms,
    pnl: Number(r.cumulative_pnl_usd.toFixed(2)),
    dd:  Number((r.current_drawdown_pct * 100).toFixed(2)),
  }));

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
        <span className="font-mono text-[11px] tracking-[0.16em] text-green/70 uppercase">
          <span className="animate-pulse">▮</span> awaiting telemetry
        </span>
        <p className="text-[13px] text-muted-fg">Equity curve plots after the first trade cycle.</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="2 4" stroke="var(--border)" vertical={false} />
        <XAxis dataKey="t" tickFormatter={(v) => ts(Number(v))}
          tick={{ fontSize: 10, fill: "var(--muted)" }} tickLine={false} axisLine={false} />
        <YAxis yAxisId="pnl" tick={{ fontSize: 10, fill: "var(--muted)" }}
          tickFormatter={(v) => `$${v}`} tickLine={false} axisLine={false} width={48} />
        <YAxis yAxisId="dd" orientation="right" tick={{ fontSize: 10, fill: "var(--muted)" }}
          tickFormatter={(v) => `${v}%`} tickLine={false} axisLine={false} width={36}
          domain={[0, "auto"]} reversed />
        <defs>
          <linearGradient id="eq-dd" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"  stopColor="var(--red)" stopOpacity={0.18} />
            <stop offset="100%" stopColor="var(--red)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <Tooltip
          contentStyle={{ background: "var(--surface)", border: "1px solid var(--border-hi)", borderRadius: 8, fontSize: 12, fontFamily: "var(--font-mono)" }}
          labelFormatter={(l) => ts(Number(l))}
          formatter={(val, name) => {
            const n = Number(val);
            return name === "Equity" ? [`$${n.toFixed(2)}`, name] : [`${n.toFixed(2)}%`, name];
          }}
        />
        <Area yAxisId="dd" type="monotone" dataKey="dd" name="Drawdown"
          stroke="var(--red)" fill="url(#eq-dd)" strokeWidth={1} />
        <Line yAxisId="pnl" type="monotone" dataKey="pnl" name="Equity"
          stroke="var(--green)" strokeWidth={2} dot={false}
          style={{ filter: "drop-shadow(0 0 6px color-mix(in oklab, var(--green) 45%, transparent))" }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
