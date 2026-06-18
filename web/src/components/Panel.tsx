import type { CSSProperties, ReactNode } from "react";
import { cn } from "@/lib/utils";

type Props = {
  label?: ReactNode;
  /** right-aligned content in the header row (badges, buttons) */
  action?: ReactNode;
  /** override the label tick colour (defaults to alien green) */
  tick?: "green" | "cyan" | "red" | "yellow" | "purple";
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
};

const TICK: Record<NonNullable<Props["tick"]>, string> = {
  green:  "var(--green)",
  cyan:   "var(--cyan)",
  red:    "var(--red)",
  yellow: "var(--yellow)",
  purple: "var(--purple)",
};

export function Panel({ label, action, tick = "green", children, className, bodyClassName }: Props) {
  return (
    <section className={cn("panel", className)}>
      {(label || action) && (
        <header className="flex items-center justify-between gap-3 px-3.5 pt-3 pb-2">
          {label ? (
            <span
              className="panel-label"
              style={{ "--tick": TICK[tick] } as CSSProperties}
            >
              {label}
            </span>
          ) : <span />}
          {action}
        </header>
      )}
      <div className={cn("px-3.5 pb-3", !label && !action && "pt-3.5", bodyClassName)}>
        {children}
      </div>
    </section>
  );
}
