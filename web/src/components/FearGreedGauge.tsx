import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Panel } from "./Panel";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// Arc gauge geometry
const CX = 100, CY = 92, OR = 76, IR = 56;
const W = 200, H = 100;

function polar(r: number, score: number): [number, number] {
  const a = Math.PI * (1 - score / 100);
  return [CX + r * Math.cos(a), CY - r * Math.sin(a)];
}

function thickArc(s1: number, s2: number): string {
  const [ox1, oy1] = polar(OR, s1);
  const [ox2, oy2] = polar(OR, s2);
  const [ix1, iy1] = polar(IR, s1);
  const [ix2, iy2] = polar(IR, s2);
  const f = (n: number) => n.toFixed(1);
  return (
    `M ${f(ox1)} ${f(oy1)} ` +
    `A ${OR} ${OR} 0 0 1 ${f(ox2)} ${f(oy2)} ` +
    `L ${f(ix2)} ${f(iy2)} ` +
    `A ${IR} ${IR} 0 0 0 ${f(ix1)} ${f(iy1)} Z`
  );
}

type Zone = { label: string; textCls: string; fillVar: string };

function getZone(s: number): Zone {
  if (s <= 25) return { label: "EXTREME FEAR",  textCls: "text-red",      fillVar: "var(--red)" };
  if (s <= 45) return { label: "FEAR",           textCls: "text-yellow",   fillVar: "var(--yellow)" };
  if (s <= 55) return { label: "NEUTRAL",        textCls: "text-muted-fg", fillVar: "var(--border-hi)" };
  if (s <= 75) return { label: "GREED",          textCls: "text-yellow",   fillVar: "var(--yellow)" };
  return               { label: "EXTREME GREED", textCls: "text-red",      fillVar: "var(--red)" };
}

function getStrategySignal(score: number) {
  if (score < 0.2) return { label: "BUY SIGNAL",  cls: "text-green" };
  if (score > 0.6) return { label: "TRIM SIGNAL", cls: "text-yellow" };
  return                   { label: "WATCHING",    cls: "text-muted-fg" };
}

// Background zone segments
const BG_ZONES: [number, number, string][] = [
  [0,  25,  "color-mix(in oklab, var(--red)      18%, transparent)"],
  [25, 45,  "color-mix(in oklab, var(--yellow)   16%, transparent)"],
  [45, 55,  "color-mix(in oklab, var(--border-hi) 25%, transparent)"],
  [55, 75,  "color-mix(in oklab, var(--yellow)   16%, transparent)"],
  [75, 100, "color-mix(in oklab, var(--red)      18%, transparent)"],
];

function ArcGauge({ score100, zone }: { score100: number; zone: Zone }) {
  const [nx, ny] = polar(IR + (OR - IR) * 0.5, score100);
  const [needleX, needleY] = polar(OR - 4, score100);
  const f = (n: number) => n.toFixed(1);

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      style={{ overflow: "visible" }}
      aria-label={`Fear & Greed Index: ${score100} — ${zone.label}`}
    >
      {/* Background track */}
      <path
        d={thickArc(0, 100)}
        fill="color-mix(in oklab, var(--border) 40%, transparent)"
      />

      {/* Zone tints */}
      {BG_ZONES.map(([s1, s2, fill]) => (
        <path key={s1} d={thickArc(s1, s2)} fill={fill} />
      ))}

      {/* Active fill: 0 → score100 */}
      {score100 > 0 && (
        <path
          d={thickArc(0, score100)}
          fill={`color-mix(in oklab, ${zone.fillVar} 65%, transparent)`}
          style={{
            filter: `drop-shadow(0 0 5px color-mix(in oklab, ${zone.fillVar} 55%, transparent))`,
          }}
        />
      )}

      {/* Dot at needle tip */}
      <circle
        cx={f(nx)}
        cy={f(ny)}
        r="4.5"
        fill={zone.fillVar}
        style={{ filter: `drop-shadow(0 0 6px ${zone.fillVar})` }}
      />

      {/* Needle */}
      <line
        x1={CX} y1={CY}
        x2={f(needleX)} y2={f(needleY)}
        stroke="var(--text)"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.7"
      />
      <circle cx={CX} cy={CY} r="3" fill="var(--border-hi)" />

      {/* Score number */}
      <text
        x={CX} y={CY - 14}
        textAnchor="middle"
        style={{
          fontFamily: "Chakra Petch, sans-serif",
          fontSize: 20,
          fontWeight: 700,
          fill: zone.fillVar,
          filter: `drop-shadow(0 0 8px color-mix(in oklab, ${zone.fillVar} 60%, transparent))`,
        }}
      >
        {score100}
      </text>

      {/* Axis labels */}
      <text x={f(polar(OR + 6, 2)[0])} y={CY + 2} textAnchor="end"
        style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 7, fill: "var(--muted)", opacity: 0.7 }}>
        FEAR
      </text>
      <text x={f(polar(OR + 6, 98)[0])} y={CY + 2} textAnchor="start"
        style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 7, fill: "var(--muted)", opacity: 0.7 }}>
        GREED
      </text>
    </svg>
  );
}

export function FearGreedGauge() {
  const sentiment = useQuery(api.social.getSentiment, { symbol: "ETH" });

  if (sentiment === undefined) {
    return (
      <Panel label="Fear & Greed" tick="yellow">
        <div className="space-y-3">
          <Skeleton className="h-8 w-40 bg-elevated rounded" />
          <Skeleton className="h-3 w-full bg-elevated rounded" />
          <Skeleton className="h-4 w-48 bg-elevated rounded" />
        </div>
      </Panel>
    );
  }

  if (!sentiment) {
    return (
      <Panel label="Fear & Greed" tick="yellow">
        <div className="flex flex-col items-center justify-center gap-3 py-2">
          {/* Full radar — fills the panel like a real instrument */}
          <svg width="120" height="120" viewBox="0 0 120 120" aria-label="Scanning for sentiment data">
            <defs>
              <radialGradient id="fgRadarGrad2" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="var(--yellow)" stopOpacity="0.55" />
                <stop offset="100%" stopColor="var(--yellow)" stopOpacity="0" />
              </radialGradient>
            </defs>
            {/* Outer ring */}
            <circle cx="60" cy="60" r="54" fill="none" stroke="var(--border-hi)" strokeWidth="1" />
            {/* Mid ring */}
            <circle cx="60" cy="60" r="36" fill="none" stroke="var(--border-hi)" strokeWidth="1" opacity="0.5" />
            {/* Inner ring */}
            <circle cx="60" cy="60" r="18" fill="none" stroke="var(--border-hi)" strokeWidth="1" opacity="0.3" />
            {/* Cross hairs */}
            <line x1="60" y1="6" x2="60" y2="114" stroke="var(--border-hi)" strokeWidth="0.5" opacity="0.25" />
            <line x1="6" y1="60" x2="114" y2="60" stroke="var(--border-hi)" strokeWidth="0.5" opacity="0.25" />
            {/* Sweep */}
            <g style={{ animation: "radar-sweep 3.2s linear infinite", transformOrigin: "60px 60px" }}>
              <path d="M 60 60 L 60 6 A 54 54 0 0 1 113 60 Z" fill="url(#fgRadarGrad2)" />
            </g>
            {/* Center blip */}
            <circle cx="60" cy="60" r="3.5" fill="var(--yellow)"
              style={{ filter: "drop-shadow(0 0 6px var(--yellow))", animation: "radar-blip 1.6s ease-in-out infinite" }} />
            {/* Tick marks */}
            {[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map((deg) => {
              const r = Math.PI * deg / 180;
              const x1 = 60 + 50 * Math.cos(r), y1 = 60 + 50 * Math.sin(r);
              const x2 = 60 + 54 * Math.cos(r), y2 = 60 + 54 * Math.sin(r);
              return <line key={deg} x1={x1.toFixed(1)} y1={y1.toFixed(1)} x2={x2.toFixed(1)} y2={y2.toFixed(1)} stroke="var(--yellow)" strokeWidth="1" opacity="0.3" />;
            })}
          </svg>
          <div className="text-center space-y-1">
            <p className="font-mono text-[11px] font-bold tracking-[0.18em] uppercase text-yellow/70">Scanning Sentiment</p>
            <p className="font-mono text-[9.5px] text-muted-fg/50">feeds on next cycle trigger</p>
          </div>
        </div>
      </Panel>
    );
  }

  // score is [-1, 1] → convert to 0-100
  const score100 = Math.round((sentiment.score + 1) * 50);
  const zone     = getZone(score100);
  const signal   = getStrategySignal(sentiment.score);

  return (
    <Panel
      label="Fear & Greed"
      tick="yellow"
      action={
        <span className="font-mono text-[10px] text-muted-fg">
          ETH · {sentiment.n_posts} posts
        </span>
      }
    >
      <div className="flex flex-col gap-2">
        {/* Arc gauge */}
        <ArcGauge score100={score100} zone={zone} />

        {/* Zone label */}
        <p className={cn("font-mono text-[11px] font-bold tracking-[0.12em] uppercase text-center -mt-1", zone.textCls)}>
          {zone.label}
        </p>

        {/* Strategy signal */}
        <div className="flex items-center gap-2 border-t border-border/40 pt-2">
          <span className="font-mono text-[11px] text-muted-fg">Agent strategy:</span>
          <span className={cn("font-mono text-[11px] font-bold tracking-[0.1em]", signal.cls)}>
            {signal.label}
          </span>
        </div>
      </div>
    </Panel>
  );
}
