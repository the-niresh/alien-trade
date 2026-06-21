# UI Enhancement Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship 5 targeted cockpit improvements: thread delete, wider Co-Pilot chat, trading chart view, step-by-step tutorial tour, and logo integration.

**Architecture:** All changes are UI-only except one new Convex mutation (`copilot.deleteThread`). The chart uses the existing `priceTicks.forSymbol` + `trades.recent` Convex queries. The tour uses `driver.js` driving `data-tour` attributes already on DOM elements.

**Tech Stack:** React + TypeScript + Convex + `lightweight-charts` v4 + `driver.js` v1 + Tailwind v4 + Framer Motion

## Global Constraints

- Package manager: `bun` — never `npm` or `npx`
- Working directory: `/root/claude/projects/alien-trade/web` for all web commands
- Convex mutations that touch user data must call `assertControlToken(args.control_token)`
- `withToken()` wraps all mutation calls from the client (`import { withToken } from "@/lib/control"`)
- Build check: `bun run build` must pass with zero TypeScript errors after every task
- All CSS colours must use existing design tokens (`var(--green)`, `var(--red)`, `var(--cyan)`, `var(--purple)`, `var(--yellow)`)
- No `npm` / `npx` — use `bun add` for package installs
- Run all commands from `/root/claude/projects/alien-trade/web` unless stated otherwise

---

### Task 1: Thread Delete

**Files:**
- Modify: `convex/copilot.ts` — add `deleteThread` mutation
- Modify: `web/src/components/CoPilotDrawer.tsx` — add `×` button per thread row

**Interfaces:**
- Produces: `api.copilot.deleteThread` mutation `(control_token?, id: Id<"copilot_threads">) → null`

- [ ] **Step 1: Add `deleteThread` mutation to `convex/copilot.ts`**

Open `convex/copilot.ts`. After the `createThread` mutation, add:

```typescript
export const deleteThread = mutation({
  args: {
    control_token: v.optional(v.string()),
    id: v.id("copilot_threads"),
  },
  returns: v.null(),
  handler: async (ctx, args) => {
    assertControlToken(args.control_token);
    // Delete all messages belonging to this thread first
    const msgs = await ctx.db
      .query("copilot_messages")
      .withIndex("by_thread", (q) => q.eq("thread_id", args.id))
      .collect();
    for (const msg of msgs) {
      await ctx.db.delete(msg._id);
    }
    await ctx.db.delete(args.id);
    return null;
  },
});
```

- [ ] **Step 2: Wire delete into `CoPilotDrawer.tsx`**

Open `web/src/components/CoPilotDrawer.tsx`.

Add `deleteThread` mutation next to the existing mutations (around line 62):
```typescript
const deleteThreadMutation = useMutation(api.copilot.deleteThread);
```

Add a handler before `newThread`:
```typescript
const handleDeleteThread = async (id: Id<"copilot_threads">) => {
  if (activeThreadId === id) setActiveThreadId(null);
  await deleteThreadMutation(withToken({ id }));
};
```

Replace the thread list `<button>` block (lines 121–130) with this version that wraps the title in a `group` and shows a delete button on hover:

```tsx
{(threads as ThreadDoc[]).map((t) => (
  <div
    key={t._id}
    className={cn(
      "group relative w-full flex items-center transition-colors",
      activeThreadId === t._id ? "text-purple bg-purple/10" : "text-muted-fg hover:text-text hover:bg-elevated/50",
    )}
  >
    <button
      onClick={() => setActiveThreadId(t._id as Id<"copilot_threads">)}
      className="flex-1 text-left px-3 py-2 font-mono text-[11px] truncate cursor-pointer"
    >
      {t.title}
    </button>
    <button
      onClick={(e) => {
        e.stopPropagation();
        handleDeleteThread(t._id as Id<"copilot_threads">);
      }}
      className="opacity-0 group-hover:opacity-100 flex-shrink-0 w-6 h-6 flex items-center justify-center text-muted-fg hover:text-red transition-all cursor-pointer mr-1"
      aria-label="Delete thread"
    >
      <X className="w-3 h-3" />
    </button>
  </div>
))}
```

- [ ] **Step 3: Build check**

```bash
cd /root/claude/projects/alien-trade && bunx convex dev --once 2>&1 | tail -5
cd web && bun run build 2>&1 | tail -10
```

Expected: no TypeScript errors, build succeeds.

- [ ] **Step 4: Commit**

```bash
cd /root/claude/projects/alien-trade
git add convex/copilot.ts web/src/components/CoPilotDrawer.tsx
git commit -m "feat(copilot): thread delete button + deleteThread mutation"
```

---

### Task 2: Wider Co-Pilot Chat Area

**Files:**
- Modify: `web/src/components/CoPilotDrawer.tsx` — width + mobile sidebar toggle

**Interfaces:**
- No new interfaces — layout-only changes

- [ ] **Step 1: Widen the drawer and add mobile sidebar toggle state**

In `CoPilotDrawer.tsx`, add `sidebarOpen` state to the existing state declarations:
```typescript
const [sidebarOpen, setSidebarOpen] = useState(false);
```

- [ ] **Step 2: Update drawer width**

Find the `SheetContent` opening tag. Change:
```tsx
className="w-[560px] max-sm:w-full p-0 flex flex-col gap-0 border-l-0 shadow-none bg-transparent overflow-hidden"
```
to:
```tsx
className="w-[720px] max-sm:w-full p-0 flex flex-col gap-0 border-l-0 shadow-none bg-transparent overflow-hidden"
```

- [ ] **Step 3: Update thread sidebar width and add mobile hide**

Find the thread sidebar `<div>` (the one with `w-[160px]`). Change:
```tsx
<div className="w-[160px] border-r border-border/40 flex flex-col flex-shrink-0 overflow-hidden">
```
to:
```tsx
<div className={cn(
  "w-[140px] border-r border-border/40 flex flex-col flex-shrink-0 overflow-hidden transition-all",
  "max-sm:absolute max-sm:inset-y-0 max-sm:left-0 max-sm:z-20 max-sm:w-[200px] max-sm:bg-[#050508]",
  !sidebarOpen && "max-sm:hidden",
)}>
```

- [ ] **Step 4: Add mobile sidebar toggle to chat header**

Find the chat header `<div>` (the one with "Co-Pilot" label, around line 137). Add a hamburger toggle button visible only on mobile, just before the brand dot:

```tsx
<div className="flex items-center justify-between px-4 py-3 border-b border-border/40">
  <div className="flex items-center gap-2">
    {/* Mobile sidebar toggle */}
    <button
      onClick={() => setSidebarOpen((v) => !v)}
      className="sm:hidden w-6 h-6 flex items-center justify-center text-muted-fg hover:text-text transition-colors cursor-pointer mr-1"
      aria-label="Toggle threads"
    >
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>
    <div className="w-2 h-2 rounded-full bg-purple" style={{ boxShadow: "0 0 8px var(--purple)" }} />
    <span className="font-display text-[14px] font-bold text-text">Co-Pilot</span>
  </div>
  <button onClick={onClose}
    className="w-7 h-7 rounded flex items-center justify-center text-muted-fg hover:text-text hover:bg-elevated transition-colors cursor-pointer">
    <X className="w-4 h-4" />
  </button>
</div>
```

- [ ] **Step 5: Build check and commit**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | tail -10
```

Expected: clean build.

```bash
cd /root/claude/projects/alien-trade
git add web/src/components/CoPilotDrawer.tsx
git commit -m "feat(copilot): wider drawer (720px), narrower sidebar (140px), mobile toggle"
```

---

### Task 3: Trading Chart View

**Files:**
- Create: `web/src/components/TradingChart.tsx` — wraps `lightweight-charts`
- Create: `web/src/views/ChartView.tsx` — the new view
- Modify: `web/src/components/SideNav.tsx` — add `"chart"` to View union + nav item
- Modify: `web/src/components/BottomNav.tsx` — add chart tab
- Modify: `web/src/App.tsx` — add `case "chart"` to `renderView()`

**Interfaces:**
- `TradingChart` props: `{ ticks: PriceTick[]; trades?: TradeMarker[]; height?: number }`
- `PriceTick`: `{ timestamp_ms: number; price: number }`
- `TradeMarker`: `{ timestamp_ms: number; side: "buy" | "sell" }`

- [ ] **Step 1: Install `lightweight-charts`**

```bash
cd /root/claude/projects/alien-trade/web && bun add lightweight-charts
```

Expected output: package added to `package.json`.

- [ ] **Step 2: Create `TradingChart.tsx`**

Create `web/src/components/TradingChart.tsx`:

```tsx
import { useEffect, useRef } from "react";
import { createChart, ColorType, LineStyle } from "lightweight-charts";

type PriceTick   = { timestamp_ms: number; price: number };
type TradeMarker = { timestamp_ms: number; side: "buy" | "sell" };

type Props = {
  ticks: PriceTick[];
  trades?: TradeMarker[];
  height?: number;
};

export function TradingChart({ ticks, trades = [], height = 480 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || ticks.length < 2) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#5f7d96",
        fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(120,160,190,0.06)", style: LineStyle.Dotted },
        horzLines: { color: "rgba(120,160,190,0.06)", style: LineStyle.Dotted },
      },
      crosshair: {
        vertLine: { color: "rgba(52,255,174,0.3)", labelBackgroundColor: "#050508" },
        horzLine: { color: "rgba(52,255,174,0.3)", labelBackgroundColor: "#050508" },
      },
      timeScale: {
        borderColor: "rgba(120,160,190,0.12)",
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: number) => {
          const d = new Date(time * 1000);
          return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
        },
      },
      rightPriceScale: { borderColor: "rgba(120,160,190,0.12)" },
      width: containerRef.current.clientWidth,
      height,
      handleScroll: true,
      handleScale: true,
    });

    const areaSeries = chart.addAreaSeries({
      lineColor: "#34ffae",
      topColor: "rgba(52,255,174,0.20)",
      bottomColor: "rgba(52,255,174,0.01)",
      lineWidth: 2,
    });

    const sorted = [...ticks].sort((a, b) => a.timestamp_ms - b.timestamp_ms);
    // lightweight-charts needs time in seconds
    areaSeries.setData(
      sorted.map((t) => ({ time: Math.floor(t.timestamp_ms / 1000) as unknown as import("lightweight-charts").Time, value: t.price }))
    );

    if (trades.length > 0) {
      areaSeries.setMarkers(
        [...trades]
          .sort((a, b) => a.timestamp_ms - b.timestamp_ms)
          .map((tr) => ({
            time: Math.floor(tr.timestamp_ms / 1000) as unknown as import("lightweight-charts").Time,
            position: tr.side === "buy" ? ("belowBar" as const) : ("aboveBar" as const),
            color: tr.side === "buy" ? "#34ffae" : "#ff2d6e",
            shape: tr.side === "buy" ? ("arrowUp" as const) : ("arrowDown" as const),
            text: tr.side === "buy" ? "B" : "S",
            size: 1,
          }))
      );
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [ticks, trades, height]);

  if (ticks.length < 2) {
    return (
      <div className="flex items-center justify-center font-mono text-[12px] text-muted-fg" style={{ height }}>
        Waiting for price data…
      </div>
    );
  }

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}
```

- [ ] **Step 3: Create `ChartView.tsx`**

Create `web/src/views/ChartView.tsx`:

```tsx
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
```

- [ ] **Step 4: Add `"chart"` to `SideNav.tsx`**

Open `web/src/components/SideNav.tsx`.

Add `LineChart` to the lucide import:
```typescript
import { LayoutDashboard, List, Users, Settings, FileText, Bot, Sun, Moon, Bell, Wallet, Activity, BookOpen, LineChart } from "lucide-react";
```

Update the `View` union to include `"chart"`:
```typescript
export type View = "overview" | "chart" | "positions" | "agents" | "controls" | "pipeline" | "portfolio" | "logs" | "notifications" | "docs";
```

Add to `NAV_ITEMS` array, after `"pipeline"` and before `"positions"`:
```typescript
{ view: "chart",        icon: LineChart,       label: "Chart" },
```

Add `data-tour` attributes to nav buttons. Replace the NAV_ITEMS `.map()` button element's `aria-label` line to also include `data-tour`:

Replace:
```tsx
aria-label={item.label}
aria-current={isActive ? "page" : undefined}
```
with:
```tsx
aria-label={item.label}
aria-current={isActive ? "page" : undefined}
data-tour={`nav-${item.view}`}
```

- [ ] **Step 5: Update `BottomNav.tsx` to include Chart**

Open `web/src/components/BottomNav.tsx`.

Add `LineChart` to the lucide import:
```typescript
import { LayoutDashboard, List, Users, Settings, LineChart } from "lucide-react";
```

Replace the `TABS` array with (swapping "logs" for "chart" to keep 5 items):
```typescript
const TABS: { view: View; icon: React.ComponentType<{ className?: string }>; label: string }[] = [
  { view: "overview",  icon: LayoutDashboard, label: "Overview" },
  { view: "chart",     icon: LineChart,       label: "Chart" },
  { view: "positions", icon: List,            label: "Positions" },
  { view: "agents",    icon: Users,           label: "Agents" },
  { view: "controls",  icon: Settings,        label: "Controls" },
];
```

- [ ] **Step 6: Add `case "chart"` in `App.tsx`**

Open `web/src/App.tsx`.

Add the import at the top:
```typescript
import { ChartView } from "./views/ChartView";
```

In `renderView()`, add before `case "positions"`:
```typescript
case "chart":         return <ChartView />;
```

- [ ] **Step 7: Build check and commit**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | tail -15
```

Expected: clean build. Fix any type errors before committing.

```bash
cd /root/claude/projects/alien-trade
git add web/src/components/TradingChart.tsx web/src/views/ChartView.tsx \
  web/src/components/SideNav.tsx web/src/components/BottomNav.tsx web/src/App.tsx \
  web/package.json web/bun.lock
git commit -m "feat(chart): candlestick chart view with trade markers — lightweight-charts"
```

---

### Task 4: Step-by-Step Tutorial Tour

**Files:**
- Create: `web/src/lib/tour.ts` — driver.js wrapper
- Modify: `web/src/globals.css` — dark theme override for driver.js popover
- Modify: `web/src/components/SideNav.tsx` — Tour button + `data-tour="nav-tour"` 
- Modify: `web/src/components/LiveHeader.tsx` — `data-tour` on brand + kill switch
- Modify: `web/src/App.tsx` — auto-launch tour on first pairing

**Interfaces:**
- `startTour()` — launches the tour (imported wherever needed)
- `hasTourBeenSeen(): boolean`
- `markTourSeen(): void`

- [ ] **Step 1: Install `driver.js`**

```bash
cd /root/claude/projects/alien-trade/web && bun add driver.js
```

- [ ] **Step 2: Create `web/src/lib/tour.ts`**

```typescript
import { driver } from "driver.js";
import "driver.js/dist/driver.css";

const TOUR_KEY = "alien-trade:tour-seen-v1";

export function hasTourBeenSeen(): boolean {
  return localStorage.getItem(TOUR_KEY) === "1";
}

export function markTourSeen(): void {
  localStorage.setItem(TOUR_KEY, "1");
}

export function startTour(): void {
  const driverObj = driver({
    showProgress: true,
    progressText: "{{current}} / {{total}}",
    animate: true,
    overlayOpacity: 0.65,
    popoverClass: "alien-tour-popover",
    onDestroyed: markTourSeen,
    steps: [
      {
        element: '[data-tour="brand"]',
        popover: {
          title: "Welcome to Alien-Trade",
          description: "Your autonomous BSC trading cockpit. This 30-second tour covers the key controls.",
          side: "bottom",
          align: "start",
        },
      },
      {
        element: '[data-tour="kill-switch"]',
        popover: {
          title: "Kill Switch",
          description: "Halt all trading instantly. Hold again to resume. Red = halted, Green = live.",
          side: "bottom",
          align: "end",
        },
      },
      {
        element: '[data-tour="nav-overview"]',
        popover: {
          title: "Overview",
          description: "Live PnL, drawdown, signal scores, and agent heartbeat at a glance.",
          side: "right",
        },
      },
      {
        element: '[data-tour="nav-chart"]',
        popover: {
          title: "Chart",
          description: "Price chart for each token the agent trades, with your entry and exit markers.",
          side: "right",
        },
      },
      {
        element: '[data-tour="nav-portfolio"]',
        popover: {
          title: "Portfolio",
          description: "Your TWAK self-custody wallet holdings shown in real time.",
          side: "right",
        },
      },
      {
        element: '[data-tour="nav-controls"]',
        popover: {
          title: "Controls",
          description: "Set risk limits, position size, equity floor, and strategy parameters.",
          side: "right",
        },
      },
      {
        element: '[data-tour="nav-copilot"]',
        popover: {
          title: "Co-Pilot",
          description: 'Ask the agent anything. "What\'s the current regime?" or "Why did we go flat?"',
          side: "right",
        },
      },
      {
        element: '[data-tour="nav-tour"]',
        popover: {
          title: "You're all set",
          description: "The agent is watching the market 24/7. Click this button any time to replay the tour.",
          side: "right",
        },
      },
    ],
  });

  driverObj.drive();
}
```

- [ ] **Step 3: Add dark-theme CSS override to `globals.css`**

Append to the end of `web/src/globals.css`:

```css
/* ── driver.js tour — dark theme override ───────────────────────────────── */
.alien-tour-popover {
  background: oklch(5.5% 0 0) !important;
  border: 1px solid oklch(14% 0 0) !important;
  border-radius: 12px !important;
  color: #e6f1f5 !important;
  box-shadow: 0 0 40px rgba(52,255,174,0.08), 0 8px 32px rgba(0,0,0,0.6) !important;
}
.alien-tour-popover .driver-popover-title {
  font-family: "Chakra Petch", ui-sans-serif, sans-serif !important;
  font-size: 14px !important;
  font-weight: 700 !important;
  color: #34ffae !important;
  margin-bottom: 6px !important;
}
.alien-tour-popover .driver-popover-description {
  font-family: "IBM Plex Mono", ui-monospace, monospace !important;
  font-size: 12px !important;
  color: rgba(230,241,245,0.8) !important;
  line-height: 1.65 !important;
}
.alien-tour-popover .driver-popover-progress-text {
  font-family: "IBM Plex Mono", ui-monospace, monospace !important;
  font-size: 10px !important;
  color: #5f7d96 !important;
}
.alien-tour-popover .driver-popover-navigation-btns button {
  background: oklch(8% 0 0) !important;
  border: 1px solid oklch(14% 0 0) !important;
  color: #e6f1f5 !important;
  border-radius: 6px !important;
  font-family: "IBM Plex Mono", ui-monospace, monospace !important;
  font-size: 11px !important;
  cursor: pointer !important;
  padding: 4px 12px !important;
}
.alien-tour-popover .driver-popover-navigation-btns button:hover {
  background: oklch(10% 0 0) !important;
}
.alien-tour-popover .driver-popover-next-btn {
  border-color: rgba(52,255,174,0.3) !important;
  color: #34ffae !important;
}
.alien-tour-popover .driver-popover-close-btn {
  color: #5f7d96 !important;
  background: transparent !important;
  border: none !important;
}
.alien-tour-popover .driver-popover-close-btn:hover {
  color: #e6f1f5 !important;
  background: transparent !important;
}
```

- [ ] **Step 4: Add `data-tour` attributes to `LiveHeader.tsx`**

Open `web/src/components/LiveHeader.tsx`.

On the brand mark `<div>` (the one with `font-display` "ALIEN·TRADE", around line 40), add `data-tour="brand"`:
```tsx
<div className="flex items-center gap-2 sm:gap-2.5 flex-shrink-0" data-tour="brand">
```

On the desktop kill switch wrapper `<div>` (around line 130), add `data-tour="kill-switch"`:
```tsx
<div className="hidden sm:flex" data-tour="kill-switch">
```

- [ ] **Step 5: Add Tour button to `SideNav.tsx`**

Open `web/src/components/SideNav.tsx`.

Add `GraduationCap` to the lucide import:
```typescript
import { LayoutDashboard, List, Users, Settings, FileText, Bot, Sun, Moon, Bell, Wallet, Activity, BookOpen, LineChart, GraduationCap } from "lucide-react";
```

Update Props type to accept `onTour`:
```typescript
type Props = { active: View; onSelect: (v: View) => void; onCopilot: () => void; onTour: () => void };
```

Update the function signature:
```typescript
export function SideNav({ active, onSelect, onCopilot, onTour }: Props) {
```

Add the Tour button in the bottom section, between the `<div className="flex-1" />` spacer and the Co-Pilot button:

```tsx
<Tooltip>
  <TooltipTrigger asChild>
    <button
      onClick={onTour}
      data-tour="nav-tour"
      className="w-10 h-10 rounded-[11px] flex items-center justify-center text-muted-fg hover:bg-elevated hover:text-text transition-colors cursor-pointer"
      aria-label="Start tour"
    >
      <GraduationCap className="w-[18px] h-[18px]" />
    </button>
  </TooltipTrigger>
  <TooltipContent side="right">Start tour</TooltipContent>
</Tooltip>
```

Also add `data-tour="nav-copilot"` to the Co-Pilot button:
```tsx
<button
  onClick={onCopilot}
  data-tour="nav-copilot"
  className="w-10 h-10 rounded-[11px] flex items-center justify-center text-purple hover:bg-purple/10 transition-colors cursor-pointer"
  aria-label="Co-Pilot"
>
```

- [ ] **Step 6: Wire `onTour` through `AppShell` and `App.tsx`**

Open `web/src/components/AppShell.tsx`.

Add `onTour: () => void` to the `Props` type and the destructured params. Pass it through to `SideNav`:
```tsx
type Props = {
  children: ReactNode;
  activeView: View;
  onViewChange: (v: View) => void;
  onCopilot: () => void;
  onTour: () => void;         // add this line
  halted: boolean;
  mode?: string;
  onKillToggle: () => void;
  selectedSymbol?: string;
  onSymbolChange?: (s: string) => void;
};

export function AppShell({ children, activeView, onViewChange, onCopilot, onTour, halted, mode, onKillToggle, selectedSymbol, onSymbolChange }: Props) {
```

Pass `onTour` to `SideNav`:
```tsx
<SideNav
  active={activeView}
  onSelect={onViewChange}
  onCopilot={onCopilot}
  onTour={onTour}
/>
```

Open `web/src/App.tsx`.

Add tour imports at the top (after existing imports):
```typescript
import { startTour, hasTourBeenSeen } from "./lib/tour";
```

Wire `onTour` into `AppShell`:
```tsx
<AppShell
  activeView={view}
  onViewChange={setView}
  onCopilot={() => setCopilotOpen(true)}
  onTour={startTour}
  halted={halted}
  mode={mode}
  onKillToggle={onKillToggle}
  selectedSymbol={selectedSymbol}
  onSymbolChange={setSelectedSymbol}
>
```

Add auto-launch on first pairing. In the `onPaired` callback in `PairingScreen`, after `setTokenState(t)`:
```tsx
onPaired={(t) => {
  setToken(t);
  setTokenState(t);
  if (!hasTourBeenSeen()) {
    // Small delay to let the app shell mount before driver.js tries to find elements
    setTimeout(startTour, 600);
  }
}}
```

- [ ] **Step 7: Build check and commit**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | tail -15
```

Expected: clean build.

```bash
cd /root/claude/projects/alien-trade
git add web/src/lib/tour.ts web/src/globals.css \
  web/src/components/SideNav.tsx web/src/components/AppShell.tsx \
  web/src/components/LiveHeader.tsx web/src/App.tsx \
  web/package.json web/bun.lock
git commit -m "feat(tour): step-by-step onboarding tour via driver.js, auto-launches on first login"
```

---

### Task 5: Logo Integration

**Files:**
- Copy: `docs/logo.png` → `web/public/logo.png`
- Modify: `web/index.html` — favicon
- Modify: `web/src/globals.css` — `.logo-blend` utility class
- Modify: `web/src/components/LiveHeader.tsx` — logo next to brand text
- Modify: `web/src/App.tsx` — logo in PairingScreen welcome step
- Modify: `web/src/views/LandingView.tsx` — logo in hero

- [ ] **Step 1: Copy logo to public dir and create public dir if needed**

```bash
mkdir -p /root/claude/projects/alien-trade/web/public
cp /root/claude/projects/alien-trade/docs/logo.png /root/claude/projects/alien-trade/web/public/logo.png
```

- [ ] **Step 2: Update favicon in `index.html`**

Open `web/index.html`. Add a favicon link inside `<head>`, after the `<meta>` tags:

```html
<link rel="icon" type="image/png" href="/logo.png" />
<link rel="apple-touch-icon" href="/logo.png" />
```

- [ ] **Step 3: Add `.logo-blend` utility to `globals.css`**

Append to `web/src/globals.css`:
```css
/* ── Logo — screen blend removes the dark background on dark surfaces ──── */
.logo-blend {
  mix-blend-mode: screen;
  border-radius: 50%;
  object-fit: cover;
}
```

- [ ] **Step 4: Add logo to `LiveHeader.tsx`**

Open `web/src/components/LiveHeader.tsx`.

In the brand mark `<div data-tour="brand">`, replace the pulsing dot with the logo image:

Replace:
```tsx
<span className="relative flex h-2 w-2">
  <span className={cn(
    "absolute inline-flex h-full w-full rounded-full opacity-70 animate-ping",
    halted ? "bg-red" : "bg-green",
  )} />
  <span className={cn("relative inline-flex h-2 w-2 rounded-full", halted ? "bg-red" : "bg-green")} />
</span>
```

With:
```tsx
<div className="relative flex-shrink-0">
  <img
    src="/logo.png"
    alt="Alien-Trade"
    className="logo-blend w-7 h-7"
  />
  {/* Status pulse overlaid at bottom-right of logo */}
  <span className={cn(
    "absolute bottom-0 right-0 w-2 h-2 rounded-full border border-[#050508]",
    halted ? "bg-red" : "bg-green animate-pulse",
  )} />
</div>
```

- [ ] **Step 5: Add logo to `PairingScreen` welcome step in `App.tsx`**

Open `web/src/App.tsx`.

In the `step === "welcome"` block, add the logo above the "ALIEN·TRADE" heading:

Find:
```tsx
<div className="font-display text-[28px] font-bold text-green glow-green tracking-[0.16em] mb-1">
  ALIEN<span className="text-text/40">·</span>TRADE
</div>
```

Replace with:
```tsx
<div className="flex flex-col items-center gap-3 mb-1">
  <img
    src="/logo.png"
    alt="Alien-Trade"
    className="logo-blend w-20 h-20"
  />
  <div className="font-display text-[28px] font-bold text-green glow-green tracking-[0.16em]">
    ALIEN<span className="text-text/40">·</span>TRADE
  </div>
</div>
```

- [ ] **Step 6: Add logo to `LandingView.tsx` hero**

Open `web/src/views/LandingView.tsx`.

In the hero `<div>`, add the logo above the "ALIEN·TRADE" heading. Find:
```tsx
<div className="font-display text-[48px] font-bold text-green tracking-[0.12em] mb-2"
```

Insert before it:
```tsx
<img
  src="/logo.png"
  alt="Alien-Trade"
  className="logo-blend w-28 h-28 mb-6"
/>
```

- [ ] **Step 7: Build check and commit**

```bash
cd /root/claude/projects/alien-trade/web && bun run build 2>&1 | tail -10
```

Expected: clean build.

```bash
cd /root/claude/projects/alien-trade
git add web/public/logo.png web/index.html web/src/globals.css \
  web/src/components/LiveHeader.tsx web/src/App.tsx web/src/views/LandingView.tsx
git commit -m "feat(logo): alien logo in header, pairing wizard, and landing — screen blend mode"
```

---

## Self-Review

**Spec coverage:**
- ✅ Thread delete button + deleteThread mutation (Task 1)
- ✅ Wider chat area 720px, narrower sidebar 140px, mobile toggle (Task 2)
- ✅ Trading chart with lightweight-charts, 5 symbols, trade markers (Task 3)
- ✅ Tutorial tour via driver.js, auto-launches on first login, Tour button always accessible (Task 4)
- ✅ Logo in header / pairing wizard / landing via mix-blend-mode: screen (Task 5)

**Placeholder scan:** No TBDs, all code blocks complete.

**Type consistency:**
- `PriceTick` and `TradeMarker` types defined in Task 3 and used only within `TradingChart.tsx` and `ChartView.tsx` — no cross-task type leakage.
- `onTour: () => void` added to `AppShell` Props in Task 4 and passed correctly from `App.tsx` → `AppShell` → `SideNav`.
- `View` union updated in Task 3 (`SideNav.tsx`) before `BottomNav.tsx` and `App.tsx` use it — correct order.
