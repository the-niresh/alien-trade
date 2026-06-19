import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface SponsorCardProps {
  sponsor: "TWAK" | "CMC" | "BNB_SDK";
  name: string;
  tagline: string;
  integrations: string[];
  stat?: { label: string; value: string | number };
  badgeColor?: string;
  children?: ReactNode;
}

const SPONSOR_COLORS: Record<SponsorCardProps["sponsor"], string> = {
  CMC:     "bg-blue/10 text-blue border-blue/25",
  TWAK:    "bg-cyan/10 text-cyan border-cyan/25",
  BNB_SDK: "bg-yellow/10 text-yellow border-yellow/25",
};

const SPONSOR_TICK: Record<SponsorCardProps["sponsor"], string> = {
  CMC:     "var(--blue, #3b82f6)",
  TWAK:    "var(--cyan)",
  BNB_SDK: "var(--yellow)",
};

export function SponsorCard({
  sponsor,
  name,
  tagline,
  integrations,
  stat,
  badgeColor,
  children,
}: SponsorCardProps) {
  const colorClass = badgeColor ?? SPONSOR_COLORS[sponsor];
  const tick = SPONSOR_TICK[sponsor];

  return (
    <div className="panel flex flex-col gap-3">
      {/* Header */}
      <div className="px-3.5 pt-3.5">
        <div className="flex items-start justify-between gap-2 mb-1.5">
          <span
            className={cn(
              "font-mono text-[10px] font-bold tracking-[0.18em] uppercase px-2 py-0.5 rounded border",
              colorClass,
            )}
          >
            {sponsor.replace("_", " ")}
          </span>
        </div>
        <h3 className="font-display font-bold text-[15px] text-text leading-snug">{name}</h3>
        <p className="font-mono text-[11px] text-muted-fg mt-0.5">{tagline}</p>
      </div>

      {/* Divider with tick */}
      <div
        className="mx-3.5 h-px"
        style={{ background: `linear-gradient(to right, ${tick}, transparent)` }}
      />

      {/* Integration bullets */}
      <ul className="px-3.5 space-y-1.5 flex-1">
        {integrations.map((item) => (
          <li key={item} className="flex items-start gap-2">
            <span
              className="mt-[5px] h-[5px] w-[5px] rounded-full flex-shrink-0"
              style={{ background: tick, boxShadow: `0 0 4px ${tick}` }}
            />
            <span className="font-mono text-[11px] text-muted-fg leading-relaxed">{item}</span>
          </li>
        ))}
      </ul>

      {children}

      {/* Live stat */}
      {stat && (
        <div className="px-3.5 pb-3.5 flex items-center justify-end">
          <div
            className={cn(
              "flex items-center gap-2 font-mono text-[11px] px-2.5 py-1 rounded-lg border",
              colorClass,
            )}
          >
            <span
              className="h-1.5 w-1.5 rounded-full animate-pulse"
              style={{ background: tick }}
            />
            <span className="text-muted-fg">{stat.label}:</span>
            <span className="font-bold">{stat.value}</span>
          </div>
        </div>
      )}
    </div>
  );
}
