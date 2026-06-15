import { Area, AreaChart, ResponsiveContainer } from "recharts";

export type PriceTick = { t: number; p: number };

type Props = {
  ticks: PriceTick[];
  positive: boolean;
  height?: number;
};

export function Sparkline({ ticks, positive, height = 56 }: Props) {
  if (ticks.length < 2) {
    return <div className="bg-elevated rounded-lg my-2" style={{ height }} />;
  }
  const color = positive ? "var(--green)" : "var(--red)";
  const gradId = `sg-${positive ? "pos" : "neg"}`;
  return (
    <div style={{ margin: "8px 0" }}>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={ticks} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={color} stopOpacity={0.22} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="p"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#${gradId})`}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
