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
      <div style={{ textAlign: "center", padding: "32px 0", color: "var(--muted)", fontSize: 13 }}>
        No trade history yet — equity curve appears after the first cycle.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1a2737" vertical={false} />
        <XAxis dataKey="t" tickFormatter={(v) => ts(Number(v))}
          tick={{ fontSize: 10, fill: "var(--muted)" }} tickLine={false} axisLine={false} />
        <YAxis yAxisId="pnl" tick={{ fontSize: 10, fill: "var(--muted)" }}
          tickFormatter={(v) => `$${v}`} tickLine={false} axisLine={false} width={48} />
        <YAxis yAxisId="dd" orientation="right" tick={{ fontSize: 10, fill: "var(--muted)" }}
          tickFormatter={(v) => `${v}%`} tickLine={false} axisLine={false} width={36}
          domain={[0, "auto"]} reversed />
        <Tooltip
          contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
          labelFormatter={(l) => ts(Number(l))}
          formatter={(val, name) => {
            const n = Number(val);
            return name === "Equity" ? [`$${n.toFixed(2)}`, name] : [`${n.toFixed(2)}%`, name];
          }}
        />
        <Area yAxisId="dd" type="monotone" dataKey="dd" name="Drawdown"
          stroke="var(--red)" fill="#ff306018" strokeWidth={1} />
        <Line yAxisId="pnl" type="monotone" dataKey="pnl" name="Equity"
          stroke="var(--green)" strokeWidth={2} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
