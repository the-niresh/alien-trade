import { useState } from "react";
import { MoreHorizontal, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { View } from "./SideNav";
import { PRIMARY_VIEWS, MORE_VIEWS } from "../lib/nav";

// 4 primary tabs shown in the bottom bar (first 4 from PRIMARY_VIEWS)
const BOTTOM_TABS = PRIMARY_VIEWS.slice(0, 4);
// remaining primary views that go into the More sheet
const OVERFLOW_PRIMARY = PRIMARY_VIEWS.slice(4);

type Props = {
  active: View;
  onSelect: (v: View) => void;
  onCopilot: () => void;
};

export function BottomNav({ active, onSelect }: Props) {
  const [moreOpen, setMoreOpen] = useState(false);

  // Whether the active view is one of the overflow views (not in the 4 bottom tabs)
  const allMoreViews = [...OVERFLOW_PRIMARY, ...MORE_VIEWS];
  const isMoreActive = allMoreViews.some((item) => item.view === active);

  function handleSelect(view: View) {
    onSelect(view);
    setMoreOpen(false);
  }

  return (
    <>
      <nav
        className="h-14 border-t border-border/60 flex items-stretch w-full flex-shrink-0 z-10"
        style={{
          background: "color-mix(in oklab, var(--surface) 88%, transparent)",
          backdropFilter: "blur(16px) saturate(1.2)",
          WebkitBackdropFilter: "blur(16px) saturate(1.2)",
        }}
      >
        {BOTTOM_TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = active === tab.view;
          return (
            <button
              key={tab.view}
              onClick={() => onSelect(tab.view)}
              className={cn(
                "relative flex-1 flex flex-col items-center justify-center gap-[3px] transition-all duration-200 cursor-pointer min-h-[44px]",
                isActive ? "text-green" : "text-muted-fg hover:text-text/70",
              )}
              aria-label={tab.label}
              aria-current={isActive ? "page" : undefined}
            >
              {/* Active indicator — full-width top bar with glow */}
              {isActive && (
                <span
                  className="absolute top-0 left-2 right-2 h-[2.5px] rounded-full bg-green"
                  style={{ boxShadow: "0 0 10px var(--green), 0 0 20px color-mix(in oklab, var(--green) 40%, transparent)" }}
                />
              )}

              {/* Active background wash */}
              {isActive && (
                <span className="absolute inset-x-1 inset-y-1 rounded-xl bg-green/6" />
              )}

              <Icon className={cn("relative z-10 transition-transform duration-200", isActive ? "w-[19px] h-[19px]" : "w-[18px] h-[18px]", isActive && "drop-shadow-[0_0_6px_var(--green)]")} />
              <span className={cn(
                "relative z-10 font-mono font-bold tracking-[0.08em] transition-all duration-200",
                isActive ? "text-[10px] text-green" : "text-[9px] text-muted-fg",
              )}>
                {tab.label}
              </span>
            </button>
          );
        })}

        {/* More button */}
        <button
          onClick={() => setMoreOpen(true)}
          className={cn(
            "relative flex-1 flex flex-col items-center justify-center gap-[3px] transition-all duration-200 cursor-pointer min-h-[44px]",
            isMoreActive ? "text-green" : "text-muted-fg hover:text-text/70",
          )}
          aria-label="More views"
          aria-expanded={moreOpen}
        >
          {isMoreActive && (
            <span
              className="absolute top-0 left-2 right-2 h-[2.5px] rounded-full bg-green"
              style={{ boxShadow: "0 0 10px var(--green), 0 0 20px color-mix(in oklab, var(--green) 40%, transparent)" }}
            />
          )}
          {isMoreActive && (
            <span className="absolute inset-x-1 inset-y-1 rounded-xl bg-green/6" />
          )}
          <MoreHorizontal className={cn("relative z-10 transition-transform duration-200", isMoreActive ? "w-[19px] h-[19px] drop-shadow-[0_0_6px_var(--green)]" : "w-[18px] h-[18px]")} />
          <span className={cn(
            "relative z-10 font-mono font-bold tracking-[0.08em] transition-all duration-200",
            isMoreActive ? "text-[10px] text-green" : "text-[9px] text-muted-fg",
          )}>
            More
          </span>
        </button>
      </nav>

      {/* More sheet */}
      <Sheet open={moreOpen} onOpenChange={setMoreOpen}>
        <SheetContent
          side="bottom"
          className="rounded-t-2xl border-border/60 pb-safe"
          style={{
            background: "color-mix(in oklab, var(--surface) 96%, transparent)",
            backdropFilter: "blur(24px) saturate(1.3)",
            WebkitBackdropFilter: "blur(24px) saturate(1.3)",
          }}
        >
          <SheetHeader className="mb-4">
            <div className="flex items-center justify-between">
              <SheetTitle className="text-sm font-mono font-bold tracking-widest uppercase text-muted-fg">
                All Views
              </SheetTitle>
              <button
                onClick={() => setMoreOpen(false)}
                className="w-7 h-7 rounded-full flex items-center justify-center text-muted-fg hover:bg-elevated hover:text-text transition-colors"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </SheetHeader>

          {/* Overflow primary views */}
          {OVERFLOW_PRIMARY.length > 0 && (
            <div className="mb-4">
              <p className="text-[10px] font-mono tracking-widest uppercase text-muted-fg/60 mb-2 px-1">Main</p>
              <div className="grid grid-cols-4 gap-2">
                {OVERFLOW_PRIMARY.map((item) => {
                  const Icon = item.icon;
                  const isActive = active === item.view;
                  return (
                    <button
                      key={item.view}
                      onClick={() => handleSelect(item.view)}
                      className={cn(
                        "flex flex-col items-center gap-1.5 py-3 px-2 rounded-xl transition-all duration-200 cursor-pointer",
                        isActive
                          ? "bg-green/10 text-green border border-green/25"
                          : "bg-elevated/60 text-muted-fg hover:bg-elevated hover:text-text border border-transparent",
                      )}
                      aria-label={item.label}
                      aria-current={isActive ? "page" : undefined}
                    >
                      <Icon className={cn("w-5 h-5", isActive && "drop-shadow-[0_0_6px_var(--green)]")} />
                      <span className="text-[10px] font-mono font-bold tracking-[0.06em]">{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* More views grid */}
          <div>
            <p className="text-[10px] font-mono tracking-widest uppercase text-muted-fg/60 mb-2 px-1">Tools</p>
            <div className="grid grid-cols-4 gap-2">
              {MORE_VIEWS.map((item) => {
                const Icon = item.icon;
                const isActive = active === item.view;
                return (
                  <button
                    key={item.view}
                    onClick={() => handleSelect(item.view)}
                    className={cn(
                      "flex flex-col items-center gap-1.5 py-3 px-2 rounded-xl transition-all duration-200 cursor-pointer",
                      isActive
                        ? "bg-green/10 text-green border border-green/25"
                        : "bg-elevated/60 text-muted-fg hover:bg-elevated hover:text-text border border-transparent",
                    )}
                    aria-label={item.label}
                    aria-current={isActive ? "page" : undefined}
                  >
                    <Icon className={cn("w-5 h-5", isActive && "drop-shadow-[0_0_6px_var(--green)]")} />
                    <span className="text-[10px] font-mono font-bold tracking-[0.06em]">{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
