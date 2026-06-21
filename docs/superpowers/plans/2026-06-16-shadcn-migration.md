# Alien-Trade Cockpit — shadcn/Tailwind Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Big-bang migration of the Alien-Trade cockpit (`web/`) from hand-rolled CSS to Tailwind CSS v4 + shadcn/ui, with new features: mobile bottom nav, page transitions, error boundaries, 3-step pairing wizard, symbol switcher, and Sonner toasts.

**Architecture:** Keep existing CSS custom properties (`--bg`, `--surface`, `--cyan`, etc.) as the design token source of truth. Add Tailwind v4 `@theme inline` block referencing them so utilities like `bg-surface`, `text-cyan` work dynamically with the dark/light toggle. shadcn components use CSS vars mapped to our tokens. All Convex mutations remain wrapped with `withToken()`.

**Tech Stack:** React 18, Vite 5, TypeScript, Tailwind CSS v4 (`@tailwindcss/vite`), shadcn/ui (New York style), framer-motion, recharts, Convex, `qrcode`, `react-error-boundary`, `lucide-react`, `clsx`, `tailwind-merge`

**Working directory for all commands:** `/root/claude/projects/alien-trade/web`

---

### Task 1: Install dependencies + configure Vite + tsconfig + shadcn scaffolding

**Files:**
- Modify: `package.json` (via bun add)
- Modify: `vite.config.ts`
- Modify: `tsconfig.json`
- Create: `components.json`
- Create: `src/lib/utils.ts`

- [ ] **Step 1: Install all new packages**

```bash
cd /root/claude/projects/alien-trade/web
bun add -D tailwindcss @tailwindcss/vite
bun add lucide-react clsx tailwind-merge react-error-boundary qrcode
bun add -D @types/qrcode
```

- [ ] **Step 2: Update `vite.config.ts`** — add Tailwind plugin + `@` path alias

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [
    tailwindcss(),
    react(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "Alien-Trade",
        short_name: "Alien-Trade",
        description: "Autonomous BSC trading agent — PnL, drawdown, kill switch",
        theme_color: "#0b0f17",
        background_color: "#0b0f17",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
        ],
      },
    }),
  ],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: { host: true, port: 5173 },
});
```

- [ ] **Step 3: Update `tsconfig.json`** — add path alias

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src", "../convex/_generated"]
}
```

- [ ] **Step 4: Create `components.json`** — shadcn config (Tailwind v4, New York style)

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/globals.css",
    "baseColor": "zinc",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

- [ ] **Step 5: Create `src/lib/utils.ts`**

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 6: Verify build passes**

```bash
bun run build 2>&1 | tail -20
```

Expected: build succeeds (no Tailwind output yet — that's fine, just verifying deps resolve).

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "chore(web): install tailwind v4, shadcn scaffolding, path alias"
```

---

### Task 2: Write `src/globals.css` — design token bridge

**Files:**
- Create: `src/globals.css` (replaces `src/index.css`)
- Modify: `src/main.tsx` (update import)

- [ ] **Step 1: Create `src/globals.css`**

```css
@import "tailwindcss";

/* ── Tailwind v4: inline theme — references CSS vars at runtime so dark/light toggle works ── */
@theme inline {
  --color-bg:        var(--bg);
  --color-surface:   var(--surface);
  --color-elevated:  var(--elevated);
  --color-border:    var(--border);
  --color-border-hi: var(--border-hi);
  --color-green:     var(--green);
  --color-red:       var(--red);
  --color-cyan:      var(--cyan);
  --color-yellow:    var(--yellow);
  --color-purple:    var(--purple);
  --color-text:      var(--text);
  --color-muted-fg:  var(--muted);

  /* shadcn semantic tokens */
  --color-background:          var(--background);
  --color-foreground:          var(--foreground);
  --color-card:                var(--card);
  --color-card-foreground:     var(--card-foreground);
  --color-popover:             var(--surface);
  --color-popover-foreground:  var(--text);
  --color-primary:             var(--primary);
  --color-primary-foreground:  var(--primary-foreground);
  --color-secondary:           var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted:               var(--muted-surface);
  --color-muted-foreground:    var(--muted);
  --color-accent:              var(--elevated);
  --color-accent-foreground:   var(--text);
  --color-destructive:         var(--red);
  --color-destructive-foreground: #fff;
  --color-input:               var(--border);
  --color-ring:                var(--cyan);

  --font-grotesk: "Space Grotesk", sans-serif;
  --font-mono:    "IBM Plex Mono", monospace;

  --radius-sm:  0.5rem;
  --radius-md:  0.625rem;
  --radius-lg:  0.75rem;
  --radius-xl:  1rem;
  --radius-2xl: 1.25rem;
  --radius-full: 9999px;
}

/* ── Design tokens ── */
@layer base {
  :root {
    --bg:           #000000;
    --surface:      #080d14;
    --elevated:     #0d1520;
    --border:       #172030;
    --border-hi:    #243650;
    --green:        #00ff9d;
    --red:          #ff3060;
    --cyan:         #00d4ff;
    --yellow:       #ffd60a;
    --purple:       #a855f7;
    --text:         #e8f0f8;
    --muted:        #5878a0;
    --muted-surface: #0d1520;
    color-scheme: dark;

    /* shadcn required vars */
    --background:           var(--bg);
    --foreground:           var(--text);
    --card:                 var(--surface);
    --card-foreground:      var(--text);
    --primary:              var(--cyan);
    --primary-foreground:   #040d14;
    --secondary:            var(--elevated);
    --secondary-foreground: var(--text);
    --radius:               0.625rem;
  }

  [data-theme="light"] {
    --bg:           #f0f4f8;
    --surface:      #ffffff;
    --elevated:     #e8edf4;
    --border:       #d0dae8;
    --border-hi:    #a8bcd4;
    --green:        #00a86b;
    --red:          #e02050;
    --cyan:         #0098c8;
    --yellow:       #c89800;
    --purple:       #8030d0;
    --text:         #0a1828;
    --muted:        #5878a0;
    --muted-surface: #e8edf4;
    color-scheme: light;
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    padding: 0;
    overflow: hidden;
    background: var(--bg);
    color: var(--text);
    font-family: "Inter", ui-sans-serif, system-ui, sans-serif;
    font-variant-numeric: tabular-nums;
  }
}

/* ── Preserved hand-rolled rules (not expressible as Tailwind utilities) ── */

/* Kill switch — conic-gradient countdown is set via inline style in KillSwitch.tsx */
.kill-switch,
.kill-switch-hero {
  user-select: none;
  -webkit-user-select: none;
  touch-action: none;
}
.kill-switch__inner { pointer-events: none; }

/* Agent ticker scroll animation */
@keyframes ticker-scroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}
.ticker-track {
  display: flex;
  gap: 64px;
  white-space: nowrap;
  animation: ticker-scroll 80s linear infinite;
}

/* Log console — monospace font, specific line layout */
.logconsole {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  line-height: 1.5;
  background: #02060c;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Touch targets */
@media (pointer: coarse) {
  button { min-height: 44px; }
}
```

- [ ] **Step 2: Update `src/main.tsx`** — swap import

Find the line `import "./index.css"` and change it to:
```ts
import "./globals.css"
```

Also keep the fontsource imports:
```ts
import "@fontsource/space-grotesk/400.css";
import "@fontsource/space-grotesk/700.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/600.css";
import "@fontsource/ibm-plex-mono/400.css";
```

- [ ] **Step 3: Delete `src/index.css`** — only after verifying globals.css is imported

```bash
rm src/index.css
```

- [ ] **Step 4: Verify build**

```bash
bun run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(web): add globals.css — tailwind v4 design token bridge"
```

---

### Task 3: Install all shadcn components

**Files:**
- Create: `src/components/ui/` (many files generated by shadcn)

- [ ] **Step 1: Add all needed shadcn components**

```bash
cd /root/claude/projects/alien-trade/web
bunx shadcn@latest add alert-dialog sheet button input slider tooltip skeleton sonner badge card dialog select --overwrite
```

If prompted, accept defaults. This generates files in `src/components/ui/`.

- [ ] **Step 2: Verify components exist**

```bash
ls src/components/ui/
```

Expected: `alert-dialog.tsx  badge.tsx  button.tsx  card.tsx  dialog.tsx  input.tsx  select.tsx  sheet.tsx  skeleton.tsx  slider.tsx  sonner.tsx  tooltip.tsx` (and possibly `label.tsx`, `separator.tsx` as auto-deps).

- [ ] **Step 3: Verify build still passes**

```bash
bun run build 2>&1 | tail -20
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat(web): add shadcn components (alert-dialog, sheet, button, input, slider, tooltip, skeleton, sonner, badge, card, dialog, select)"
```

---

### Task 4: Fix priceTicks type hack in PositionCard

**Files:**
- Modify: `web/src/components/PositionCard.tsx`

- [ ] **Step 1: Regenerate Convex types**

```bash
cd /root/claude/projects/alien-trade
bunx convex dev --once 2>&1 | tail -10
```

Expected: generates `convex/_generated/` — `api.priceTicks.forSymbol` should now be typed.

- [ ] **Step 2: Update the query in `src/components/PositionCard.tsx`**

Replace line:
```ts
const rawTicks = useQuery((api as any).priceTicks?.forSymbol, { symbol: position.symbol, limit: 24 }) ?? [];
```

With:
```ts
const rawTicks = useQuery(api.priceTicks.forSymbol, { symbol: position.symbol, limit: 24 }) ?? [];
```

- [ ] **Step 3: Verify typecheck passes**

```bash
bun run typecheck 2>&1 | grep -i "error" | head -10
```

Expected: no errors on PositionCard.tsx line.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "fix(web): remove (api as any) hack in PositionCard — use typed priceTicks.forSymbol"
```

---

### Task 5: Migrate AppShell.tsx

**Files:**
- Modify: `src/components/AppShell.tsx`

- [ ] **Step 1: Rewrite `AppShell.tsx` with Tailwind**

```tsx
import { ReactNode } from "react";
import { SideNav, View } from "./SideNav";
import { LiveHeader } from "./LiveHeader";
import { AgentTicker } from "./AgentTicker";
import { BottomNav } from "./BottomNav";

type Props = {
  children: ReactNode;
  activeView: View;
  onViewChange: (v: View) => void;
  onCopilot: () => void;
  halted: boolean;
  mode?: string;
  onKillToggle: () => void;
};

export function AppShell({ children, activeView, onViewChange, onCopilot, halted, mode, onKillToggle }: Props) {
  return (
    <div className="flex flex-col h-screen">
      <LiveHeader halted={halted} mode={mode} onKillToggle={onKillToggle} />
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar — hidden on mobile */}
        <div className="hidden sm:flex">
          <SideNav active={activeView} onSelect={onViewChange} onCopilot={onCopilot} />
        </div>
        <main className="flex-1 overflow-y-auto px-6 py-5 pb-12">
          {children}
        </main>
      </div>
      <AgentTicker />
      {/* Bottom nav — mobile only */}
      <div className="flex sm:hidden">
        <BottomNav active={activeView} onSelect={onViewChange} onCopilot={onCopilot} />
      </div>
    </div>
  );
}
```

Note: `BottomNav` is created in Task 18 — add the import but the component can be a stub for now.

- [ ] **Step 2: Commit**

```bash
git add src/components/AppShell.tsx && git commit -m "refactor(web): AppShell — tailwind layout utilities"
```

---

### Task 6: Migrate SideNav.tsx with Tooltip

**Files:**
- Modify: `src/components/SideNav.tsx`

- [ ] **Step 1: Rewrite `SideNav.tsx`**

```tsx
import { useState } from "react";
import { toggleTheme, getTheme } from "../lib/theme";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { LayoutDashboard, List, Users, Settings, FileText, Bot, Sun, Moon } from "lucide-react";
import type { View } from "./SideNav";

export type { View };

const NAV_ITEMS: { view: View; icon: React.ComponentType<{ className?: string }>; label: string }[] = [
  { view: "overview",  icon: LayoutDashboard, label: "Overview" },
  { view: "positions", icon: List,            label: "Positions" },
  { view: "agents",    icon: Users,           label: "Agents" },
  { view: "controls",  icon: Settings,        label: "Controls" },
  { view: "logs",      icon: FileText,        label: "Logs" },
];

type Props = { active: View; onSelect: (v: View) => void; onCopilot: () => void };

export function SideNav({ active, onSelect, onCopilot }: Props) {
  const [theme, setTheme] = useState(getTheme);

  const handleThemeToggle = () => {
    const next = toggleTheme();
    setTheme(next);
  };

  return (
    <TooltipProvider delayDuration={300}>
      <nav className="w-[52px] bg-surface border-r border-border flex flex-col items-center py-3 gap-1 flex-shrink-0">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <Tooltip key={item.view}>
              <TooltipTrigger asChild>
                <button
                  onClick={() => onSelect(item.view)}
                  className={cn(
                    "w-10 h-10 rounded-[10px] flex items-center justify-center transition-colors",
                    active === item.view
                      ? "bg-elevated text-cyan"
                      : "text-muted-fg hover:bg-elevated hover:text-text"
                  )}
                  aria-label={item.label}
                >
                  <Icon className="w-[18px] h-[18px]" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">{item.label}</TooltipContent>
            </Tooltip>
          );
        })}

        <div className="flex-1" />

        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={onCopilot}
              className="w-10 h-10 rounded-[10px] flex items-center justify-center text-purple hover:bg-elevated transition-colors"
              aria-label="Co-Pilot"
            >
              <Bot className="w-[18px] h-[18px]" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="right">Co-Pilot</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={handleThemeToggle}
              className="w-10 h-10 rounded-[10px] flex items-center justify-center text-muted-fg hover:bg-elevated hover:text-text transition-colors"
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              {theme === "dark"
                ? <Sun className="w-4 h-4" />
                : <Moon className="w-4 h-4" />}
            </button>
          </TooltipTrigger>
          <TooltipContent side="right">
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </TooltipContent>
        </Tooltip>
      </nav>
    </TooltipProvider>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
bun run build 2>&1 | grep -i error | head -5
```

- [ ] **Step 3: Commit**

```bash
git add src/components/SideNav.tsx && git commit -m "refactor(web): SideNav — tailwind + shadcn Tooltip"
```

---

### Task 7: Migrate LiveHeader.tsx + RegimeBadge.tsx

**Files:**
- Modify: `src/components/LiveHeader.tsx`
- Modify: `src/components/RegimeBadge.tsx`

- [ ] **Step 1: Rewrite `RegimeBadge.tsx`**

```tsx
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type Props = { regime?: string | null };

const CFG: Record<string, { colorClass: string; icon: string }> = {
  bull:     { colorClass: "border-green/30 bg-green/10 text-green", icon: "↑" },
  trend:    { colorClass: "border-green/30 bg-green/10 text-green", icon: "↑" },
  bear:     { colorClass: "border-red/30 bg-red/10 text-red", icon: "↓" },
  crash:    { colorClass: "border-red/50 bg-red/20 text-red", icon: "⚠" },
  chop:     { colorClass: "border-yellow/30 bg-yellow/10 text-yellow", icon: "↔" },
  high_vol: { colorClass: "border-yellow/30 bg-yellow/10 text-yellow", icon: "⚡" },
};
const DEFAULT = { colorClass: "border-border bg-elevated text-muted-fg", icon: "?" };

export function RegimeBadge({ regime }: Props) {
  const key = (regime ?? "").toLowerCase().replace(/ /g, "_");
  const c = CFG[key] ?? DEFAULT;
  return (
    <Badge variant="outline" className={cn("text-[11px] font-bold tracking-wide px-2.5 py-0.5", c.colorClass)}>
      {c.icon} {(regime ?? "UNKNOWN").toUpperCase()}
    </Badge>
  );
}
```

- [ ] **Step 2: Rewrite `LiveHeader.tsx`**

```tsx
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { KillSwitch } from "./KillSwitch";
import { RegimeBadge } from "./RegimeBadge";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { usd } from "../lib/formatters";

type Props = { halted: boolean; mode?: string; onKillToggle: () => void };

const MODE_CLASS: Record<string, string> = {
  paper:   "bg-yellow/10 text-yellow border-yellow/20",
  mainnet: "bg-red/10 text-red border-red/20",
  testnet: "bg-cyan/10 text-cyan border-cyan/20",
};

export function LiveHeader({ halted, mode, onKillToggle }: Props) {
  const ledger    = useQuery(api.ledger.latest);
  const decisions = useQuery(api.decisions.recent, { limit: 1 });

  const pnl    = ledger?.cumulative_pnl_usd;
  const regime = decisions?.[0]?.regime ?? null;
  const pnlPos = (pnl ?? 0) >= 0;

  return (
    <header className="h-14 bg-surface border-b border-border flex items-center px-4 gap-3.5 flex-shrink-0">
      <span className="font-grotesk text-[15px] font-bold tracking-[2px] text-cyan">
        ALIEN-TRADE
      </span>

      <div className="w-px h-7 bg-border flex-shrink-0" />

      {regime && <RegimeBadge regime={regime} />}

      {mode && (
        <Badge
          variant="outline"
          className={cn("text-[11px] font-bold tracking-widest rounded-md px-2.5", MODE_CLASS[mode])}
        >
          {mode === "mainnet" ? "LIVE" : mode.toUpperCase()}
        </Badge>
      )}

      {pnl != null && (
        <>
          <div className="w-px h-7 bg-border flex-shrink-0" />
          <span className={cn("font-grotesk text-[22px] font-bold", pnlPos ? "text-green" : "text-red")}>
            {usd(pnl)}
          </span>
        </>
      )}

      <div className="flex-1" />

      {halted && (
        <Badge className="bg-red/10 text-red border border-red/30 text-[12px] font-bold tracking-wide rounded-md">
          HALTED
        </Badge>
      )}

      <KillSwitch halted={halted} onToggle={onKillToggle} />
    </header>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add src/components/LiveHeader.tsx src/components/RegimeBadge.tsx && git commit -m "refactor(web): LiveHeader + RegimeBadge — tailwind + shadcn Badge"
```

---

### Task 8: Migrate AgentTicker.tsx

**Files:**
- Modify: `src/components/AgentTicker.tsx`

- [ ] **Step 1: Rewrite `AgentTicker.tsx`**

```tsx
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { AGENT_DEFS } from "./AgentCard";

export function AgentTicker() {
  const events = useQuery(api.agentEvents.recent, { limit: 20 }) ?? [];
  if (events.length === 0) return null;

  const items = events.map((e) => {
    const def = AGENT_DEFS.find((a) => a.name === e.agent);
    return { id: e._id, agent: e.agent, color: def?.color ?? "var(--muted)", headline: String(e.headline) };
  });
  const doubled = [...items, ...items];

  return (
    <div className="h-[30px] bg-surface border-t border-border flex items-center overflow-hidden flex-shrink-0 px-3">
      <div className="ticker-track flex gap-16 whitespace-nowrap">
        {doubled.map((item, i) => (
          <span key={`${item.id}-${i}`} className="text-[11px] text-muted-fg">
            <span className="font-bold mr-1.5" style={{ color: item.color }}>{item.agent}</span>
            {item.headline}
          </span>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/AgentTicker.tsx && git commit -m "refactor(web): AgentTicker — tailwind utilities"
```

---

### Task 9: Migrate StatCard.tsx

**Files:**
- Modify: `src/components/StatCard.tsx`

- [ ] **Step 1: Rewrite `StatCard.tsx`**

```tsx
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type Tone = "positive" | "negative" | "neutral" | "warn";

const TONE_CLASS: Record<Tone, string> = {
  positive: "text-green",
  negative: "text-red",
  neutral:  "text-text",
  warn:     "text-yellow",
};

type Props = {
  label: string;
  value: string;
  tone?: Tone;
  sub?: string;
  animKey?: string | number;
};

export function StatCard({ label, value, tone = "neutral", sub, animKey }: Props) {
  return (
    <div className="bg-surface border border-border rounded-[14px] p-4">
      <div className="text-[11px] uppercase tracking-[0.6px] text-muted-fg mb-2">{label}</div>
      <motion.div
        className={cn("font-grotesk text-[26px] font-bold leading-none", TONE_CLASS[tone])}
        key={animKey ?? value}
        initial={{ scale: 1.06 }}
        animate={{ scale: 1 }}
        transition={{ duration: 0.25 }}
      >
        {value}
      </motion.div>
      {sub && <div className="text-[12px] text-muted-fg mt-1.5">{sub}</div>}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/StatCard.tsx && git commit -m "refactor(web): StatCard — tailwind utilities"
```

---

### Task 10: Migrate KillSwitch.tsx (layout only — hold mechanic preserved)

**Files:**
- Modify: `src/components/KillSwitch.tsx`

- [ ] **Step 1: Rewrite `KillSwitch.tsx`** — replace CSS class layout with Tailwind, keep conic-gradient + interval hold logic exactly

```tsx
import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type Props = {
  halted: boolean;
  onToggle: () => void;
  hero?: boolean;
};

const HOLD_MS = 1500;
const TICK_MS = 50;

export function KillSwitch({ halted, onToggle, hero = false }: Props) {
  const [progress, setProgress] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startHold = () => {
    if (timerRef.current) return;
    let elapsed = 0;
    timerRef.current = setInterval(() => {
      elapsed += TICK_MS;
      const p = Math.min(elapsed / HOLD_MS, 1);
      setProgress(p);
      if (p >= 1) { stopHold(); onToggle(); }
    }, TICK_MS);
  };

  const stopHold = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setProgress(0);
  };

  const deg   = progress * 360;
  const color = halted ? "var(--green)" : "var(--red)";
  const size  = hero ? "w-[120px] h-[120px]" : "w-11 h-11";
  const inner = halted ? "bg-[#01120a] text-green" : "bg-[#12040a] text-red";
  const textSz = hero ? "text-sm font-black tracking-wider" : "text-[8px] font-black tracking-wide";

  return (
    <motion.button
      className={cn("kill-switch rounded-full border-none cursor-pointer p-[3px] flex items-center justify-center flex-shrink-0", size, halted ? "kill-switch--resume" : "kill-switch--halt")}
      style={{ background: `conic-gradient(${color} ${deg}deg, var(--border) ${deg}deg)` }}
      onMouseDown={startHold}
      onMouseUp={stopHold}
      onMouseLeave={stopHold}
      onTouchStart={(e) => { e.preventDefault(); startHold(); }}
      onTouchEnd={stopHold}
      animate={!halted && progress === 0
        ? { boxShadow: ["0 0 0px #ff306000", "0 0 14px #ff306050", "0 0 0px #ff306000"] }
        : {}}
      transition={{ duration: 2, repeat: Infinity }}
      title={halted ? "Hold to resume trading" : "Hold to halt trading"}
    >
      <span className={cn("kill-switch__inner w-full h-full rounded-full flex items-center justify-center", inner, textSz)}>
        {progress > 0 ? `${Math.round(progress * 100)}%` : halted ? "RESUME" : "KILL"}
      </span>
    </motion.button>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/KillSwitch.tsx && git commit -m "refactor(web): KillSwitch — tailwind layout, hold mechanic unchanged"
```

---

### Task 11: Migrate LogsView.tsx

**Files:**
- Modify: `src/views/LogsView.tsx`

- [ ] **Step 1: Rewrite `LogsView.tsx`**

```tsx
import { useQuery, useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { motion } from "framer-motion";
import { ts, usd } from "../lib/formatters";
import { AGENT_DEFS } from "../components/AgentCard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const KIND_CLASS: Record<string, string> = {
  observation: "bg-green/10 text-green border-green/20",
  analysis:    "bg-cyan/10 text-cyan border-cyan/20",
  verdict:     "bg-yellow/10 text-yellow border-yellow/20",
  action:      "bg-purple/10 text-purple border-purple/20",
  handoff:     "bg-green/5 text-green/70 border-green/10",
  control:     "bg-red/10 text-red border-red/20",
};

const VERDICT_CLASS: Record<string, string> = {
  allow:   "bg-green/10 text-green border-green/20",
  block:   "bg-red/10 text-red border-red/20",
  reduce:  "bg-yellow/10 text-yellow border-yellow/20",
  observe: "bg-green/10 text-green border-green/20",
};

export function LogsView() {
  const decisions      = useQuery(api.decisions.recent, { limit: 20 });
  const auditLog       = useQuery(api.audit.recent, { limit: 60 });
  const events         = useQuery(api.agentEvents.recent, { limit: 40 });
  const wins           = useQuery(api.reflections.wins, { limit: 5 });
  const recordFeedback = useMutation(api.feedback.record);

  return (
    <div className="space-y-4">
      <h1 className="font-grotesk text-xl font-bold">Logs</h1>

      {/* Decision History */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-3">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Decision History</p>
        </CardHeader>
        <CardContent className="p-0">
          {decisions === undefined ? (
            <div className="px-6 pb-4 space-y-2">
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-8 w-full bg-elevated" />)}
            </div>
          ) : (
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr>
                  {["Time", "Symbol", "Regime", "Verdict", "Size", "Rate"].map((h) => (
                    <th key={h} className="text-left px-4 py-2.5 border-b border-border text-muted-fg font-semibold text-[11px] uppercase tracking-[0.4px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {decisions.map((d) => (
                  <tr key={d._id} className="border-b border-border last:border-0">
                    <td className="px-4 py-2.5 text-muted-fg">{ts(d.timestamp_ms)}</td>
                    <td className="px-4 py-2.5 text-cyan font-bold">{d.symbol}</td>
                    <td className="px-4 py-2.5">{d.regime}</td>
                    <td className="px-4 py-2.5">
                      <Badge variant="outline" className={cn("text-[11px] font-bold", VERDICT_CLASS[d.risk_verdict] ?? "")}>
                        {d.risk_verdict}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5">{usd(d.final_size_usd)}</td>
                    <td className="px-4 py-2.5">
                      {d.setup_key ? (
                        <span className="inline-flex gap-1">
                          <button
                            className="bg-elevated border border-border rounded-md px-2 py-1 text-[13px] hover:bg-border transition-colors"
                            onClick={() => recordFeedback({ cycle_id: d.cycle_id, setup_key: d.setup_key!, symbol: d.symbol, label: "good" })}
                          >👍</button>
                          <button
                            className="bg-elevated border border-border rounded-md px-2 py-1 text-[13px] hover:bg-border transition-colors"
                            onClick={() => recordFeedback({ cycle_id: d.cycle_id, setup_key: d.setup_key!, symbol: d.symbol, label: "bad" })}
                          >👎</button>
                        </span>
                      ) : <span className="text-muted-fg">—</span>}
                    </td>
                  </tr>
                ))}
                {decisions.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-4 text-muted-fg">No decisions yet.</td></tr>
                )}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* Winning Trades */}
      {(wins ?? []).length > 0 && (
        <Card className="bg-surface border-border">
          <CardHeader className="pb-3">
            <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Winning Trades</p>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {(wins ?? []).map((w) => (
              <motion.div
                key={w._id}
                className="bg-green/5 border border-green/20 rounded-xl px-3.5 py-3"
                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
              >
                <div className="flex justify-between items-center mb-1">
                  <Badge className="bg-green/10 text-green border-green/20 text-[11px] font-bold">WIN</Badge>
                  <span className="text-green font-bold">+{usd(w.outcome_pnl_usd)}</span>
                </div>
                <div className="text-[12px] text-muted-fg">{w.regime} · {ts(w.timestamp_ms)}</div>
                {w.lesson && (
                  <div className="text-[12px] text-muted-fg italic mt-1">"{w.lesson}"</div>
                )}
              </motion.div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Agent Activity Channel */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-3">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Agent Activity Channel</p>
        </CardHeader>
        <CardContent>
          {events === undefined ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14 w-full bg-elevated rounded-xl" />)}
            </div>
          ) : events.length === 0 ? (
            <p className="text-muted-fg text-[13px]">No activity yet.</p>
          ) : (
            <div className="flex flex-col gap-1.5 max-h-[500px] overflow-y-auto pr-1">
              {events.map((e) => {
                const def = AGENT_DEFS.find((a) => a.name === e.agent);
                return (
                  <div key={e._id} className="bg-bg border border-border rounded-[10px] px-3 py-2.5">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-bold text-[12px]" style={{ color: def?.color ?? "var(--cyan)" }}>{e.agent}</span>
                      <Badge variant="outline" className={cn("text-[10px] font-bold", KIND_CLASS[e.kind] ?? "")}>
                        {e.kind}
                      </Badge>
                      <span className="text-[11px] text-muted-fg ml-auto">{ts(e.ts_ms)}</span>
                      {e.cycle_id && <span className="text-[10px] text-border-hi font-mono">{String(e.cycle_id).slice(-8)}</span>}
                    </div>
                    <div className="text-[13px] text-text leading-relaxed">{e.headline}</div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Live Log Console */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-3">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Live Log Console</p>
        </CardHeader>
        <CardContent>
          {auditLog === undefined ? (
            <Skeleton className="h-32 w-full bg-elevated rounded-lg" />
          ) : auditLog.length === 0 ? (
            <p className="text-muted-fg text-[13px]">No log entries yet.</p>
          ) : (
            <div className="logconsole max-h-80 overflow-y-auto border border-border rounded-lg p-2.5">
              {auditLog.map((a) => (
                <div key={a._id} className={cn("flex gap-2 py-px whitespace-nowrap", a.severity === "warn" ? "text-yellow" : a.severity === "error" ? "text-red" : "")}>
                  <span className="text-[#364a60] flex-shrink-0">{ts(a.timestamp_ms)}</span>
                  <span className={cn("flex-shrink-0 min-w-[96px]", a.severity === "error" ? "text-red" : "text-cyan")}>{a.event_type}</span>
                  {a.cycle_id && <span className="text-[#364a60] flex-shrink-0">{String(a.cycle_id).slice(-8)}</span>}
                  <span className={cn("overflow-hidden text-ellipsis", a.severity === "warn" ? "text-yellow" : a.severity === "error" ? "text-red" : "text-[#7090aa]")}>{a.payload}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/views/LogsView.tsx && git commit -m "refactor(web): LogsView — tailwind + shadcn Card, Badge, Skeleton"
```

---

### Task 12: Migrate AgentsView.tsx + AgentCard.tsx

**Files:**
- Modify: `src/views/AgentsView.tsx`
- Modify: `src/components/AgentCard.tsx`

- [ ] **Step 1: Rewrite `AgentCard.tsx`**

```tsx
import { motion } from "framer-motion";
import { ts } from "../lib/formatters";
import { Skeleton } from "@/components/ui/skeleton";

export type AgentDef = {
  name: string;
  label: string;
  color: string;
  bg: string;
  role: string;
};

export const AGENT_DEFS: AgentDef[] = [
  { name: "CoPilot",    label: "CP", color: "var(--cyan)",   bg: "#00d4ff18", role: "Answers your questions about the market, regime and trades." },
  { name: "Historian",  label: "HI", color: "var(--yellow)", bg: "#ffd60a18", role: "Queries the Second Brain for institutional memory before each trade." },
  { name: "Researcher", label: "RE", color: "var(--purple)", bg: "#a855f718", role: "Auto-researches market anomalies and builds the research digest." },
  { name: "Reflector",  label: "RF", color: "var(--red)",    bg: "#ff306018", role: "Writes structured reflections after every trade for Hermes learning." },
];

type LastEvent = { ts_ms: number; kind: string; headline: string };
type Props = { def: AgentDef; lastEvent?: LastEvent; onClick: () => void };

export function AgentCard({ def, lastEvent, onClick }: Props) {
  const now = Date.now();
  const ageSec = lastEvent ? (now - lastEvent.ts_ms) / 1000 : Infinity;
  const isActive = ageSec < 60;
  const isRecent = ageSec < 300;
  const dotColor = isActive ? "var(--green)" : isRecent ? "var(--yellow)" : "var(--border-hi)";

  return (
    <div
      className="bg-surface border border-border rounded-2xl p-5 cursor-pointer transition-colors hover:bg-elevated"
      onClick={onClick}
    >
      <div className="flex items-center gap-3 mb-3">
        <motion.div
          className="w-[42px] h-[42px] rounded-full flex items-center justify-center text-[13px] font-black flex-shrink-0"
          style={{ color: def.color, background: def.bg, border: `1.5px solid ${def.color}40` }}
          animate={isActive
            ? { boxShadow: [`0 0 8px ${def.color}40`, `0 0 20px ${def.color}80`, `0 0 8px ${def.color}40`] }
            : { scale: [1, 1.03, 1] }}
          transition={{ duration: isActive ? 1.5 : 4, repeat: Infinity, ease: "easeInOut" }}
        >
          {def.label}
        </motion.div>
        <div className="flex-1">
          <div className="font-grotesk text-[16px] font-bold" style={{ color: def.color }}>{def.name}</div>
          <div className="text-[12px] text-muted-fg">{def.role}</div>
        </div>
        <motion.div
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ background: dotColor }}
          animate={isActive ? { opacity: [1, 0.4, 1] } : {}}
          transition={{ duration: 1, repeat: Infinity }}
        />
      </div>
      {lastEvent ? (
        <>
          <div className="text-[13px] text-text/80 leading-relaxed line-clamp-2">{lastEvent.headline}</div>
          <div className="text-[11px] text-muted-fg mt-2">{ts(lastEvent.ts_ms)} · {lastEvent.kind}</div>
        </>
      ) : (
        <div className="text-[13px] text-muted-fg italic">No activity yet</div>
      )}
    </div>
  );
}

export function AgentCardSkeleton() {
  return (
    <div className="bg-surface border border-border rounded-2xl p-5">
      <div className="flex items-center gap-3 mb-3">
        <Skeleton className="w-[42px] h-[42px] rounded-full bg-elevated" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-24 bg-elevated" />
          <Skeleton className="h-3 w-40 bg-elevated" />
        </div>
      </div>
      <Skeleton className="h-8 w-full bg-elevated" />
    </div>
  );
}
```

- [ ] **Step 2: Rewrite `AgentsView.tsx`**

```tsx
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { AgentCard, AgentCardSkeleton, AGENT_DEFS } from "../components/AgentCard";

type Props = { onAgentClick: (name: string) => void };

export function AgentsView({ onAgentClick }: Props) {
  const roster = useQuery(api.agentEvents.latestPerAgent);
  const rosterMap = new Map(
    (roster ?? []).map((e: { agent: string; ts_ms: number; kind: string; headline: string }) =>
      [e.agent, { ts_ms: e.ts_ms, kind: e.kind, headline: e.headline }]
    )
  );

  return (
    <div>
      <div className="mb-5">
        <h1 className="font-grotesk text-xl font-bold mb-1.5">Agent Team</h1>
        <p className="text-[13px] text-muted-fg">Click any agent to ask the co-pilot about them.</p>
      </div>
      <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        {roster === undefined
          ? AGENT_DEFS.map((d) => <AgentCardSkeleton key={d.name} />)
          : AGENT_DEFS.map((def) => (
              <AgentCard key={def.name} def={def}
                lastEvent={rosterMap.get(def.name)}
                onClick={() => onAgentClick(def.name)} />
            ))
        }
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add src/components/AgentCard.tsx src/views/AgentsView.tsx && git commit -m "refactor(web): AgentCard + AgentsView — tailwind + Skeleton loading state"
```

---

### Task 13: Migrate PositionsView.tsx + PositionCard.tsx

**Files:**
- Modify: `src/components/PositionCard.tsx`
- Modify: `src/views/PositionsView.tsx`

- [ ] **Step 1: Rewrite `PositionCard.tsx`**

```tsx
import { motion } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Sparkline } from "./Sparkline";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
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
  const pnlPct   = position.avg_entry_price > 0
    ? (position.current_price - position.avg_entry_price) / position.avg_entry_price
    : 0;
  const sign = positive ? "+" : "";

  return (
    <motion.div
      className={cn(
        "bg-surface rounded-2xl p-4 border transition-[border-color,box-shadow] duration-300",
        positive
          ? "border-green/20 shadow-[0_0_20px_rgba(0,255,157,0.03)]"
          : "border-red/20 shadow-[0_0_20px_rgba(255,48,96,0.03)]"
      )}
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
    >
      <div className="flex justify-between items-center mb-2">
        <span className="font-grotesk text-[17px] font-bold">{position.symbol}</span>
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-cyan/10 text-cyan tracking-widest">LONG</span>
      </div>

      {ticks.length > 0
        ? <Sparkline data={ticks} positive={positive} />
        : <Skeleton className="h-14 w-full bg-elevated rounded-lg my-2" />
      }

      <div className="flex items-center gap-2 my-2.5">
        <div className="flex-1">
          <div className="text-[10px] text-muted-fg mb-0.5">Entry</div>
          <div className="font-grotesk text-[13px] font-semibold">{usd(position.avg_entry_price)}</div>
        </div>
        <span className="text-muted-fg text-sm">→</span>
        <div className="flex-1">
          <div className="text-[10px] text-muted-fg mb-0.5">Current</div>
          <div className="font-grotesk text-[13px] font-semibold">{usd(position.current_price)}</div>
        </div>
      </div>

      <div className="flex justify-between items-center mt-2">
        <span className="text-[12px] text-muted-fg">
          {position.quantity.toFixed(4)} · {elapsed(position.updated_ms)}
        </span>
        <span className={cn("font-grotesk text-[15px] font-bold", positive ? "text-green" : "text-red")}>
          {sign}{usd(position.unrealized_pnl_usd)} ({sign}{pct(Math.abs(pnlPct))})
        </span>
      </div>
    </motion.div>
  );
}
```

- [ ] **Step 2: Rewrite `PositionsView.tsx`**

```tsx
import { AnimatePresence } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { PositionCard } from "../components/PositionCard";
import { Skeleton } from "@/components/ui/skeleton";

export function PositionsView() {
  const positions = useQuery(api.positions.open);

  if (positions === undefined) {
    return (
      <div>
        <div className="flex items-center gap-3 mb-5">
          <h1 className="font-grotesk text-xl font-bold">Positions</h1>
          <Skeleton className="h-5 w-16 bg-elevated" />
        </div>
        <div className="grid grid-cols-3 gap-4 max-[1200px]:grid-cols-2 max-sm:grid-cols-1">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full bg-surface border border-border rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (positions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-8 text-center gap-3">
        <div className="text-[52px]">👽</div>
        <h2 className="font-grotesk text-[18px] font-bold">Watching the market</h2>
        <p className="text-[14px] text-muted-fg max-w-xs">
          No open positions — the agent is flat and waiting for a high-conviction setup.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <h1 className="font-grotesk text-xl font-bold">Positions</h1>
        <span className="text-[13px] text-muted-fg">{positions.length} open</span>
      </div>
      <div className="grid grid-cols-3 gap-4 max-[1200px]:grid-cols-2 max-sm:grid-cols-1">
        <AnimatePresence>
          {positions.map((p) => <PositionCard key={p._id} position={p} />)}
        </AnimatePresence>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add src/components/PositionCard.tsx src/views/PositionsView.tsx && git commit -m "refactor(web): PositionCard + PositionsView — tailwind + Skeleton"
```

---

### Task 14: Migrate OverviewView.tsx

**Files:**
- Modify: `src/views/OverviewView.tsx`

- [ ] **Step 1: Rewrite `OverviewView.tsx`**

```tsx
import { AnimatePresence, motion } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { StatCard } from "../components/StatCard";
import { EquityChart } from "../components/EquityChart";
import { AgentCard, AgentCardSkeleton, AGENT_DEFS } from "../components/AgentCard";
import { PositionCard } from "../components/PositionCard";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import ThesisLedger from "../components/ThesisLedger";
import { usd, pct, ts } from "../lib/formatters";

type Props = { onAgentClick: (name: string) => void };

export function OverviewView({ onAgentClick }: Props) {
  const ledger    = useQuery(api.ledger.latest);
  const risk      = useQuery(api.riskState.get);
  const decisions = useQuery(api.decisions.recent, { limit: 3 });
  const roster    = useQuery(api.agentEvents.latestPerAgent);
  const positions = useQuery(api.positions.open) ?? [];
  const events    = useQuery(api.agentEvents.recent, { limit: 30 });

  const pnl = ledger?.cumulative_pnl_usd;
  const dd  = risk?.current_drawdown_pct;

  const floorHalt = (events ?? []).find(
    (e) => e.agent === "RiskGuard" && e.kind === "control" &&
      typeof e.headline === "string" && e.headline.includes("floor hit"),
  );
  const floorWarn = !floorHalt && (events ?? []).find(
    (e) => e.agent === "RiskGuard" && e.kind === "control" &&
      typeof e.headline === "string" && e.headline.includes("approaching floor"),
  );

  const rosterMap = new Map(
    (roster ?? []).map((e: { agent: string; ts_ms: number; kind: string; headline: string }) =>
      [e.agent, { ts_ms: e.ts_ms, kind: e.kind, headline: e.headline }]
    )
  );

  return (
    <div className="space-y-5">
      {/* Alert banners */}
      <AnimatePresence>
        {floorHalt && (
          <motion.div
            className="rounded-xl px-4 py-3 font-semibold text-[13px] bg-red/10 text-red border border-red/25"
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
          >
            Trading HALTED — equity floor hit. Fund wallet or raise floor, then Resume.
          </motion.div>
        )}
        {floorWarn && (
          <motion.div
            className="rounded-xl px-4 py-3 font-semibold text-[13px] bg-yellow/10 text-yellow border border-yellow/20"
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
          >
            Portfolio approaching equity floor. Consider adding capital.
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-3 max-[900px]:grid-cols-2">
        {ledger === undefined
          ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full bg-surface border border-border rounded-[14px]" />)
          : <>
              <StatCard label="Cumulative PnL" value={usd(pnl)}
                tone={(pnl ?? 0) >= 0 ? "positive" : "negative"} animKey={pnl ?? 0} />
              <StatCard label="Max Drawdown" value={pct(dd)}
                tone={(dd ?? 0) > 0.05 ? "negative" : (dd ?? 0) > 0 ? "warn" : "positive"} />
              <StatCard label="Open Exposure" value={usd(risk?.open_exposure_usd)} />
              <StatCard label="Win Rate" value={risk?.win_rate != null ? pct(risk.win_rate) : "—"} />
            </>
        }
      </div>

      {/* Equity chart */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-2">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Equity Curve</p>
        </CardHeader>
        <CardContent>
          <EquityChart />
        </CardContent>
      </Card>

      {/* Open positions */}
      {positions.length > 0 && (
        <Card className="bg-surface border-border">
          <CardHeader className="pb-2">
            <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Open Positions</p>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3 max-[1200px]:grid-cols-2 max-sm:grid-cols-1">
              <AnimatePresence>
                {positions.map((p) => <PositionCard key={p._id} position={p} />)}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent decisions */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-2">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Recent Decisions</p>
        </CardHeader>
        <CardContent>
          {decisions === undefined
            ? <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12 w-full bg-elevated" />)}</div>
            : decisions.length === 0
              ? <p className="text-[13px] text-muted-fg">No decisions yet.</p>
              : <div className="space-y-2">
                  {decisions.map((d) => (
                    <div key={d._id} className="flex items-center justify-between text-[13px] py-1.5 border-b border-border last:border-0">
                      <span className="text-muted-fg text-[11px]">{ts(d.timestamp_ms)}</span>
                      <span className="text-cyan font-bold">{d.symbol}</span>
                      <span className="text-muted-fg">{d.regime}</span>
                      <span className={d.risk_verdict === "allow" ? "text-green font-bold" : "text-red font-bold"}>{d.risk_verdict}</span>
                    </div>
                  ))}
                </div>
          }
        </CardContent>
      </Card>

      {/* Agent roster */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-2">
          <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Agent Team</p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
            {roster === undefined
              ? AGENT_DEFS.map((d) => <AgentCardSkeleton key={d.name} />)
              : AGENT_DEFS.map((def) => (
                  <AgentCard key={def.name} def={def}
                    lastEvent={rosterMap.get(def.name)}
                    onClick={() => onAgentClick(def.name)} />
                ))
            }
          </div>
        </CardContent>
      </Card>

      <ThesisLedger />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/views/OverviewView.tsx && git commit -m "refactor(web): OverviewView — tailwind + shadcn Card, Skeleton"
```

---

### Task 15: Migrate ControlsView.tsx (AlertDialog, Slider, Card, Button)

**Files:**
- Modify: `src/views/ControlsView.tsx`

- [ ] **Step 1: Rewrite `ControlsView.tsx`**

```tsx
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useQuery, useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { KillSwitch } from "../components/KillSwitch";
import { withToken } from "../lib/control";
import { usd, pct } from "../lib/formatters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";

const STRATEGIES = [
  { name: "momentum",   label: "Momentum",   blurb: "Rides confirmed uptrends." },
  { name: "contrarian", label: "Contrarian", blurb: "Buys fear, trims greed. Best in down/choppy markets." },
  { name: "balanced",   label: "Balanced",   blurb: "Momentum + derivatives + fear." },
  { name: "defensive",  label: "Defensive",  blurb: "Rare high-conviction longs. Minimises drawdown." },
];

export function ControlsView() {
  const config  = useQuery(api.config.get);
  const control = useQuery(api.agentControl.get);
  const [floorInput, setFloorInput] = useState("");
  const [showSliders, setShowSliders] = useState(false);

  const _setHalted      = useMutation(api.config.setHalted);
  const _setTradingMode = useMutation(api.config.setTradingMode);
  const _updateLimits   = useMutation(api.config.updateLimits);
  const _setControl     = useMutation(api.agentControl.set);
  const _setStrategy    = useMutation(api.config.setStrategy);
  const _setAutopilot   = useMutation(api.config.setAutopilot);
  const setHalted      = (a: Parameters<typeof _setHalted>[0])      => _setHalted(withToken(a));
  const setTradingMode = (a: Parameters<typeof _setTradingMode>[0]) => _setTradingMode(withToken(a));
  const updateLimits   = (a: Parameters<typeof _updateLimits>[0])   => _updateLimits(withToken(a));
  const setControl     = (a: Parameters<typeof _setControl>[0])     => _setControl(withToken(a));
  const setStrategy    = (a: Parameters<typeof _setStrategy>[0])    => _setStrategy(withToken(a));
  const setAutopilot   = (a: Parameters<typeof _setAutopilot>[0])   => _setAutopilot(withToken(a));

  const halted = config?.halted ?? false;
  const paused = control?.agents_paused ?? false;
  const mode   = config?.trading_mode;
  const floor  = config?.equity_floor ?? 0;
  const active = config?.strategy_name ?? "balanced";
  const ap     = config?.autopilot;

  const onKillToggle = () => {
    setHalted({ halted: !halted });
    setControl({ trading_halted: !halted, updated_by: "user" });
  };
  const onSetFloor = () => {
    const v = parseFloat(floorInput);
    if (!isNaN(v) && v >= 0) { updateLimits({ equity_floor: v }); setFloorInput(""); }
  };

  return (
    <div className="max-w-[680px] mx-auto space-y-4">
      <h1 className="font-grotesk text-xl font-bold mb-6">Controls</h1>

      {/* Kill switch */}
      <Card className="bg-surface border-border text-center">
        <CardHeader><p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Emergency Stop</p></CardHeader>
        <CardContent className="flex flex-col items-center gap-3">
          <KillSwitch halted={halted} onToggle={onKillToggle} hero />
          <p className="text-[13px] text-muted-fg">
            {halted ? "Agent is HALTED. Hold to resume trading." : "Hold for 1.5s to halt all trading."}
          </p>
          <div className="flex gap-2 justify-center">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="sm" className="border-border text-muted-fg hover:text-text">
                  {paused ? "Resume Agents" : "Pause Agents"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent className="bg-surface border-border">
                <AlertDialogHeader>
                  <AlertDialogTitle className="text-text">
                    {paused ? "Resume advisory agents?" : "Pause advisory agents?"}
                  </AlertDialogTitle>
                  <AlertDialogDescription className="text-muted-fg">
                    {paused ? "Agents will resume processing signals." : "Trading continues but advisory agents will pause."}
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel className="border-border text-muted-fg">Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    className="bg-cyan text-[#040d14] font-bold hover:bg-cyan/80"
                    onClick={() => setControl({ agents_paused: !paused, updated_by: "user" })}
                  >
                    Confirm
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="sm" className="border-red/30 text-red bg-red/5 hover:bg-red/10">
                  Stop Response
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent className="bg-surface border-border">
                <AlertDialogHeader>
                  <AlertDialogTitle className="text-text">Stop current agent response?</AlertDialogTitle>
                  <AlertDialogDescription className="text-muted-fg">
                    This will cancel the in-flight agent action. Cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel className="border-border text-muted-fg">Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    className="bg-red text-white font-bold hover:bg-red/80"
                    onClick={() => setControl({ stop_response_id: String(Date.now()), updated_by: "user" })}
                  >
                    Stop Response
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </CardContent>
      </Card>

      {/* Trading mode */}
      <Card className="bg-surface border-border">
        <CardHeader><p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Trading Mode</p></CardHeader>
        <CardContent>
          {config === undefined ? <Skeleton className="h-10 w-full bg-elevated" /> : (
            <div className="flex bg-bg border border-border rounded-[10px] p-1 gap-1">
              {(["testnet", "paper", "mainnet"] as const).map((m) => {
                const isActive = mode === m;
                const activeClass = m === "testnet" ? "bg-cyan/10 text-cyan"
                  : m === "paper" ? "bg-yellow/10 text-yellow"
                  : "bg-red/10 text-red";
                return (
                  <AlertDialog key={m}>
                    <AlertDialogTrigger asChild>
                      <button
                        className={cn(
                          "flex-1 py-2 px-3 rounded-lg text-[12px] font-bold uppercase tracking-[0.4px] transition-colors",
                          isActive ? activeClass : "text-muted-fg hover:text-text"
                        )}
                        disabled={isActive || config === undefined}
                        onClick={m !== "mainnet" ? (e) => {
                          e.preventDefault();
                          setTradingMode({ trading_mode: m });
                        } : undefined}
                      >
                        {m === "mainnet" ? "LIVE" : m}
                      </button>
                    </AlertDialogTrigger>
                    {m === "mainnet" && (
                      <AlertDialogContent className="bg-surface border-border">
                        <AlertDialogHeader>
                          <AlertDialogTitle className="text-text">Switch to LIVE mainnet?</AlertDialogTitle>
                          <AlertDialogDescription className="text-muted-fg">
                            This will trade real funds via TWAK-signed transactions. Make sure your wallet is funded.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel className="border-border text-muted-fg">Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            className="bg-red text-white font-bold hover:bg-red/80"
                            onClick={() => setTradingMode({ trading_mode: "mainnet" })}
                          >
                            Go LIVE
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    )}
                  </AlertDialog>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Strategy */}
      <Card className="bg-surface border-border">
        <CardHeader><p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Strategy</p></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-2">
            {STRATEGIES.map((s) => (
              <button key={s.name}
                className={cn(
                  "bg-elevated border-[1.5px] border-border rounded-xl p-3.5 cursor-pointer text-left transition-colors hover:border-border-hi",
                  active === s.name && "border-cyan bg-cyan/5"
                )}
                onClick={() => setStrategy({ strategy_name: s.name })}
              >
                <div className="font-bold text-[14px] text-text mb-1">{s.label}</div>
                <div className="text-[12px] text-muted-fg leading-snug">{s.blurb}</div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Equity floor */}
      <Card className="bg-surface border-border">
        <CardHeader><p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Equity Floor</p></CardHeader>
        <CardContent className="space-y-3">
          <p className="text-[13px] text-muted-fg">
            {floor > 0
              ? <><strong className="text-text">Floor: {usd(floor)}</strong> — agent halts if equity drops below this.</>
              : "Disabled — agent trades until manually halted."}
          </p>
          <div className="flex gap-2">
            <Input
              type="number" min="0" placeholder="e.g. 50"
              value={floorInput} onChange={(e) => setFloorInput(e.target.value)}
              className="w-32 bg-bg border-border text-text font-mono text-[13px] focus-visible:ring-cyan"
            />
            <Button size="sm" className="bg-cyan text-[#040d14] font-bold hover:bg-cyan/80"
              onClick={onSetFloor} disabled={!floorInput}>Set</Button>
            {floor > 0 && (
              <Button size="sm" variant="outline" className="border-border text-muted-fg hover:text-text"
                onClick={() => updateLimits({ equity_floor: 0 })}>Remove</Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Autopilot */}
      <Card className="bg-surface border-border">
        <CardHeader>
          <div className="flex justify-between items-center">
            <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Autopilot</p>
            <Button size="sm"
              className={ap?.enabled ? "bg-cyan text-[#040d14] font-bold hover:bg-cyan/80" : "border border-border text-muted-fg bg-elevated hover:text-text"}
              onClick={() => setAutopilot({ autopilot: { ...(ap ?? {}), enabled: !(ap?.enabled ?? false) } as Parameters<typeof setAutopilot>[0]["autopilot"] })}
            >
              {ap?.enabled ? "ON" : "OFF"}
            </Button>
          </div>
        </CardHeader>
        {ap?.enabled && (
          <CardContent className="space-y-2.5">
            {[
              { label: "Take profit %",        key: "profit_target_pct" },
              { label: "Trailing give-back %", key: "trailing_giveback_pct" },
              { label: "Daily target %",       key: "daily_profit_target_pct" },
            ].map(({ label, key }) => (
              <div key={key} className="flex justify-between items-center gap-2">
                <span className="text-[13px] text-muted-fg">{label}</span>
                <Input
                  type="number" min="0" placeholder="—" className="w-20 bg-bg border-border text-text font-mono text-[13px] focus-visible:ring-cyan"
                  defaultValue={(ap as unknown as Record<string, number | undefined>)[key] != null
                    ? (((ap as unknown as Record<string, number | undefined>)[key] as number) * 100).toFixed(1) : ""}
                  onBlur={(e) => {
                    const v = parseFloat(e.target.value);
                    setAutopilot({ autopilot: { ...ap, [key]: isNaN(v) ? undefined : v / 100 } as Parameters<typeof setAutopilot>[0]["autopilot"] });
                  }}
                />
              </div>
            ))}
          </CardContent>
        )}
      </Card>

      {/* Risk caps */}
      <Card className="bg-surface border-border">
        <CardHeader>
          <div className="flex justify-between items-center">
            <p className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">Risk Caps</p>
            <Button size="sm" variant="outline" className="border-border text-muted-fg hover:text-text"
              onClick={() => setShowSliders(!showSliders)}>
              {showSliders ? "Hide" : "Edit"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <AnimatePresence>
            {showSliders && config && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }} className="overflow-hidden space-y-4 mb-4">
                {[
                  { label: "Max position",     key: "max_position_usd",     min: 100,  max: 10000, step: 100, fmt: usd, accentClass: "accent-cyan" },
                  { label: "Daily loss limit", key: "daily_loss_limit_usd", min: 50,   max: 2000,  step: 50,  fmt: usd, accentClass: "accent-cyan" },
                ].map(({ label, key, min, max, step, fmt }) => (
                  <div key={key}>
                    <div className="flex justify-between text-[12px] mb-2">
                      <span className="text-muted-fg">{label}</span>
                      <span className="font-semibold">{fmt((config as unknown as Record<string, number>)[key])}</span>
                    </div>
                    <Slider
                      min={min} max={max} step={step}
                      defaultValue={[(config as unknown as Record<string, number>)[key]]}
                      className="[&_[data-slot=slider-thumb]]:bg-cyan [&_[data-slot=slider-range]]:bg-cyan"
                      onValueCommit={([v]) => updateLimits({ [key]: v })}
                    />
                  </div>
                ))}
                <div>
                  <div className="flex justify-between text-[12px] mb-2">
                    <span className="text-muted-fg">Max drawdown</span>
                    <span className="font-semibold">{pct(config.max_drawdown_pct)}</span>
                  </div>
                  <Slider
                    min={1} max={50} step={1}
                    defaultValue={[Math.round(config.max_drawdown_pct * 100)]}
                    className="[&_[data-slot=slider-thumb]]:bg-red [&_[data-slot=slider-range]]:bg-red"
                    onValueCommit={([v]) => updateLimits({ max_drawdown_pct: v / 100 })}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          {!showSliders && config && (
            <div className="space-y-1">
              <p className="text-[13px] text-muted-fg">Max position: <strong className="text-text">{usd(config.max_position_usd)}</strong></p>
              <p className="text-[13px] text-muted-fg">Daily loss limit: <strong className="text-text">{usd(config.daily_loss_limit_usd)}</strong></p>
              <p className="text-[13px] text-muted-fg">Max drawdown: <strong className="text-text">{pct(config.max_drawdown_pct)}</strong></p>
            </div>
          )}
          {!config && <Skeleton className="h-20 w-full bg-elevated" />}
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/views/ControlsView.tsx && git commit -m "refactor(web): ControlsView — shadcn AlertDialog, Slider, Button, Input, Card"
```

---

### Task 16: Migrate CoPilotDrawer.tsx → shadcn Sheet

**Files:**
- Modify: `src/components/CoPilotDrawer.tsx`

- [ ] **Step 1: Rewrite `CoPilotDrawer.tsx`**

```tsx
import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAction, useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const CHIPS = [
  "What's the current regime?",
  "What was the last trade?",
  "What's my risk state?",
  "Why is the agent flat?",
];

type Props = { isOpen: boolean; onClose: () => void; prefill?: string };

export function CoPilotDrawer({ isOpen, onClose, prefill = "" }: Props) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastPrefill, setLastPrefill] = useState("");
  const msgs = useQuery(api.copilot.messages, { limit: 40 }) ?? [];
  const addMessage = useMutation(api.copilot.addMessage);
  const ask = useAction(api.copilot.ask);
  const bottomRef = useRef<HTMLDivElement>(null);

  if (prefill && prefill !== lastPrefill) {
    setQuestion(prefill);
    setLastPrefill(prefill);
  }

  const send = async (q = question) => {
    const text = q.trim();
    if (!text || loading) return;
    setQuestion("");
    setLoading(true);
    try {
      await addMessage({ role: "user", content: text, sources_json: "[]" });
      const res = await ask({ question: text });
      await addMessage({ role: "assistant", content: res.answer, sources_json: JSON.stringify(res.sources) });
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  };

  return (
    <Sheet open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent
        side="right"
        className="w-[420px] max-sm:w-full bg-surface border-l border-border p-0 flex flex-col"
      >
        <SheetHeader className="px-5 py-4 border-b border-border">
          <SheetTitle className="font-grotesk text-[16px] font-bold text-purple">Co-Pilot</SheetTitle>
        </SheetHeader>

        {/* Chips */}
        <div className="flex gap-1.5 px-5 pt-3 pb-0 flex-wrap">
          {CHIPS.map((c) => (
            <button key={c}
              className="bg-elevated border border-border rounded-full px-3 py-1 text-[12px] text-muted-fg hover:text-text hover:border-border-hi transition-colors"
              onClick={() => send(c)}
            >
              {c}
            </button>
          ))}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-2.5">
          {msgs.length === 0 && (
            <p className="text-muted-fg text-[13px] italic py-2">Ask anything — regime, last trade, risk state…</p>
          )}
          <AnimatePresence initial={false}>
            {msgs.map((m) => (
              <motion.div key={m._id}
                className={`px-3.5 py-2.5 rounded-xl text-[13px] leading-relaxed max-w-[92%] ${
                  m.role === "user"
                    ? "bg-cyan/5 border border-cyan/15 self-end"
                    : "bg-elevated border border-border self-start"
                }`}
                initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
              >
                <div className={`text-[10px] font-bold mb-1 ${m.role === "user" ? "text-cyan" : "text-purple"}`}>
                  {m.role === "user" ? "You" : "CoPilot"}
                </div>
                <div>{m.content}</div>
              </motion.div>
            ))}
          </AnimatePresence>
          {loading && (
            <motion.div className="bg-elevated border border-border rounded-xl px-3.5 py-2.5 self-start text-[13px]"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <div className="text-[10px] font-bold text-purple mb-1">CoPilot</div>
              <motion.span animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 1.2, repeat: Infinity }}>
                thinking…
              </motion.span>
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input row */}
        <div className="flex gap-2 px-5 py-3 border-t border-border">
          <Input
            placeholder="Ask the co-pilot…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            disabled={loading}
            className="flex-1 bg-bg border-border text-text text-[13px] focus-visible:ring-cyan"
          />
          <Button size="sm"
            className="bg-cyan text-[#040d14] font-bold hover:bg-cyan/80"
            onClick={() => send()}
            disabled={loading || !question.trim()}
          >
            {loading ? "…" : "Ask"}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/CoPilotDrawer.tsx && git commit -m "refactor(web): CoPilotDrawer → shadcn Sheet with accessible close"
```

---

### Task 17: Add Sonner toast provider + 3 trigger sites

**Files:**
- Modify: `src/App.tsx`

- [ ] **Step 1: Update `App.tsx`** — add Sonner provider and toast trigger on kill switch toggle

Add imports at the top:
```ts
import { Toaster, toast } from "sonner";
```

Add `<Toaster position="bottom-right" theme="dark" richColors />` just before the closing `</>` in the return.

Replace the `onKillToggle` function in App.tsx:
```ts
const onKillToggle = () => {
  const willHalt = !halted;
  setHalted({ halted: willHalt });
  setControl({ trading_halted: willHalt, updated_by: "user" });
  if (willHalt) {
    toast.error("Trading halted", {
      description: "Hold the kill switch again to resume.",
      duration: 6000,
    });
  } else {
    toast.success("Trading resumed", { duration: 3000 });
  }
};
```

For equity floor and trade toasts: these fire from Convex events. Add a `useEffect` in `App.tsx` that watches the events query:
```ts
const events = useQuery(api.agentEvents.recent, { limit: 5 });
const [lastFloorHalt, setLastFloorHalt] = useState<string | null>(null);

useEffect(() => {
  const floorHalt = (events ?? []).find(
    (e) => e.agent === "RiskGuard" && e.kind === "control" &&
      typeof e.headline === "string" && e.headline.includes("floor hit"),
  );
  if (floorHalt && floorHalt._id !== lastFloorHalt) {
    setLastFloorHalt(floorHalt._id);
    toast.error("Equity floor hit", {
      description: "Agent has been halted. Fund wallet or raise floor.",
      duration: Infinity,
    });
  }
}, [events, lastFloorHalt]);
```

- [ ] **Step 2: Commit**

```bash
git add src/App.tsx && git commit -m "feat(web): add Sonner toast provider — kill switch + equity floor toasts"
```

---

### Task 18: Create BottomNav component

**Files:**
- Create: `src/components/BottomNav.tsx`

- [ ] **Step 1: Create `src/components/BottomNav.tsx`**

```tsx
import { LayoutDashboard, List, Users, Settings, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import type { View } from "./SideNav";

const TABS: { view: View; icon: React.ComponentType<{ className?: string }>; label: string }[] = [
  { view: "overview",  icon: LayoutDashboard, label: "Overview" },
  { view: "positions", icon: List,            label: "Positions" },
  { view: "agents",    icon: Users,           label: "Agents" },
  { view: "controls",  icon: Settings,        label: "Controls" },
  { view: "logs",      icon: FileText,        label: "Logs" },
];

type Props = {
  active: View;
  onSelect: (v: View) => void;
  onCopilot: () => void;
};

export function BottomNav({ active, onSelect }: Props) {
  return (
    <nav className="h-11 bg-surface border-t border-border flex items-stretch w-full flex-shrink-0">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = active === tab.view;
        return (
          <button
            key={tab.view}
            onClick={() => onSelect(tab.view)}
            className={cn(
              "flex-1 flex flex-col items-center justify-center gap-0.5 transition-colors",
              isActive ? "text-cyan" : "text-muted-fg"
            )}
            aria-label={tab.label}
          >
            <Icon className="w-[18px] h-[18px]" />
            <span className={cn("text-[9px] font-bold", isActive ? "text-cyan" : "text-muted-fg")}>
              {tab.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/BottomNav.tsx && git commit -m "feat(web): BottomNav — mobile bottom tab bar with icons + labels"
```

---

### Task 19: Add page transitions + error boundaries

**Files:**
- Modify: `src/App.tsx`
- Create: `src/components/ViewError.tsx`

- [ ] **Step 1: Create `src/components/ViewError.tsx`**

```tsx
import { Button } from "@/components/ui/button";

type Props = { error: Error; resetErrorBoundary: () => void };

export function ViewError({ error, resetErrorBoundary }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-8 text-center gap-4">
      <div className="text-4xl">⚠️</div>
      <h2 className="font-grotesk text-lg font-bold text-red">View crashed</h2>
      <p className="text-[13px] text-muted-fg max-w-xs font-mono">{error.message}</p>
      <Button size="sm" variant="outline" className="border-border text-muted-fg hover:text-text"
        onClick={resetErrorBoundary}>
        Reload view
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Update `src/App.tsx`** — add AnimatePresence on view switch + ErrorBoundary per view

Add imports:
```ts
import { AnimatePresence, motion } from "framer-motion";
import { ErrorBoundary } from "react-error-boundary";
import { ViewError } from "./components/ViewError";
```

Replace `renderView()` call in the return with:
```tsx
<AnimatePresence mode="wait">
  <motion.div
    key={view}
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -8 }}
    transition={{ duration: 0.15 }}
    className="h-full"
  >
    <ErrorBoundary FallbackComponent={ViewError} resetKeys={[view]}>
      {renderView()}
    </ErrorBoundary>
  </motion.div>
</AnimatePresence>
```

- [ ] **Step 3: Commit**

```bash
git add src/App.tsx src/components/ViewError.tsx && git commit -m "feat(web): page transitions (AnimatePresence) + per-view ErrorBoundary"
```

---

### Task 20: Pairing screen → 3-step Dialog wizard with QR code

**Files:**
- Modify: `src/App.tsx` (replace PairingScreen component)

- [ ] **Step 1: Replace the `PairingScreen` component in `src/App.tsx`**

Replace the entire `PairingScreen` function with:

```tsx
import { useEffect, useRef } from "react";
import QRCode from "qrcode";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type PairingStep = "welcome" | "pair" | "done";

function PairingScreen({ onPaired }: { onPaired: (t: string) => void }) {
  const [step, setStep] = useState<PairingStep>("welcome");
  const [val, setVal] = useState("");
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (step === "pair" && canvasRef.current) {
      QRCode.toCanvas(canvasRef.current, window.location.href, {
        width: 160,
        color: { dark: "#000000", light: "#ffffff" },
        errorCorrectionLevel: "M",
      });
    }
  }, [step]);

  const submit = () => {
    const t = val.trim();
    if (!t) return;
    setStep("done");
    setTimeout(() => onPaired(t), 1200);
  };

  return (
    <div className="grid place-items-center h-screen overflow-auto bg-bg">
      <Dialog open modal>
        <DialogContent
          className="bg-surface border-border max-w-sm w-[90%] rounded-2xl p-0 overflow-hidden"
          onInteractOutside={(e) => e.preventDefault()}
        >
          {/* Step indicators */}
          <div className="flex gap-1.5 px-6 pt-5">
            {(["welcome", "pair", "done"] as PairingStep[]).map((s, i) => (
              <div key={s} className={`h-1 flex-1 rounded-full transition-colors ${
                s === step ? "bg-cyan" :
                ["welcome", "pair", "done"].indexOf(step) > i ? "bg-cyan/40" : "bg-border"
              }`} />
            ))}
          </div>

          {step === "welcome" && (
            <div className="px-6 py-5 text-center">
              <DialogHeader>
                <div className="font-grotesk text-[28px] font-bold text-cyan tracking-[2px] mb-1">
                  ALIEN-TRADE
                </div>
                <DialogTitle className="text-[16px] font-semibold text-text">
                  Autonomous trading cockpit
                </DialogTitle>
                <DialogDescription className="text-muted-fg text-[13px] mt-2 leading-relaxed">
                  Pair this cockpit to your running agent to see live PnL, control the kill switch, and chat with the co-pilot.
                </DialogDescription>
              </DialogHeader>
              <Button
                className="mt-6 w-full bg-cyan text-[#040d14] font-bold hover:bg-cyan/80"
                onClick={() => setStep("pair")}
              >
                Connect your agent →
              </Button>
            </div>
          )}

          {step === "pair" && (
            <div className="px-6 py-5">
              <DialogHeader>
                <DialogTitle className="text-[14px] font-bold text-muted-fg uppercase tracking-widest">
                  Step 2 of 3 — Pair device
                </DialogTitle>
              </DialogHeader>
              <div className="flex flex-col items-center mt-4 mb-4 gap-2">
                <canvas ref={canvasRef} className="rounded-lg" />
                <p className="text-[11px] text-muted-fg">Scan to open on mobile</p>
              </div>
              <div className="flex items-center gap-2 my-3">
                <div className="flex-1 h-px bg-border" />
                <span className="text-[11px] text-muted-fg">or paste token</span>
                <div className="flex-1 h-px bg-border" />
              </div>
              <Input
                type="password"
                value={val}
                placeholder="control token"
                onChange={(e) => setVal(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submit()}
                className="w-full bg-bg border-border text-text font-mono text-[13px] focus-visible:ring-cyan mb-3"
              />
              <Button
                className="w-full bg-cyan text-[#040d14] font-bold hover:bg-cyan/80"
                onClick={submit}
                disabled={!val.trim()}
              >
                Pair cockpit →
              </Button>
            </div>
          )}

          {step === "done" && (
            <div className="px-6 py-8 text-center">
              <motion.div
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: "spring", stiffness: 400, damping: 20 }}
                className="text-5xl mb-4"
              >
                ✓
              </motion.div>
              <DialogTitle className="font-grotesk text-lg font-bold text-green mb-2">Cockpit paired</DialogTitle>
              <DialogDescription className="text-muted-fg text-[13px]">
                You're in. Loading your agent…
              </DialogDescription>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

Add `motion` to the existing `framer-motion` import at the top of App.tsx.

- [ ] **Step 2: Commit**

```bash
git add src/App.tsx && git commit -m "feat(web): pairing screen — 3-step Dialog wizard with QR code"
```

---

### Task 21: Symbol switcher in LiveHeader

**Files:**
- Create: `convex/symbolList.ts` (new Convex query)
- Modify: `src/components/LiveHeader.tsx`
- Modify: `src/App.tsx` (pass selectedSymbol state down)

- [ ] **Step 1: Create `convex/symbolList.ts`**

```ts
import { query } from "./_generated/server";

export const list = query({
  args: {},
  handler: async (ctx) => {
    const positions = await ctx.db
      .query("positions")
      .filter((q) => q.eq(q.field("status"), "open"))
      .collect();
    const symbols = [...new Set(positions.map((p) => p.symbol))].sort();
    return symbols;
  },
});
```

- [ ] **Step 2: Regenerate Convex types**

```bash
cd /root/claude/projects/alien-trade
bunx convex dev --once 2>&1 | tail -5
```

- [ ] **Step 3: Update `LiveHeader.tsx`** — add symbol Select

Add prop to `Props`:
```ts
type Props = {
  halted: boolean;
  mode?: string;
  onKillToggle: () => void;
  selectedSymbol: string;
  onSymbolChange: (s: string) => void;
};
```

Add inside `LiveHeader` after the spacer div:
```tsx
import { useQuery } from "convex/react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

// Inside component:
const symbols = useQuery(api.symbolList.list) ?? [];

// Add after <div className="flex-1" />:
{symbols.length > 0 && (
  <Select value={selectedSymbol} onValueChange={onSymbolChange}>
    <SelectTrigger className="w-28 h-7 text-[12px] bg-elevated border-border text-text focus:ring-cyan">
      <SelectValue placeholder="ALL" />
    </SelectTrigger>
    <SelectContent className="bg-surface border-border text-text">
      <SelectItem value="ALL" className="text-[12px]">ALL</SelectItem>
      {symbols.map((s) => (
        <SelectItem key={s} value={s} className="text-[12px] text-cyan font-bold">{s}</SelectItem>
      ))}
    </SelectContent>
  </Select>
)}
```

- [ ] **Step 4: Wire selectedSymbol state in `App.tsx`**

Add state:
```ts
const [selectedSymbol, setSelectedSymbol] = useState("ALL");
```

Pass to AppShell props → LiveHeader:
```tsx
<LiveHeader
  halted={halted} mode={mode} onKillToggle={onKillToggle}
  selectedSymbol={selectedSymbol} onSymbolChange={setSelectedSymbol}
/>
```

- [ ] **Step 5: Commit**

```bash
git add convex/symbolList.ts src/components/LiveHeader.tsx src/App.tsx && git commit -m "feat(web): symbol switcher in LiveHeader — new Convex symbolList query + shadcn Select"
```

---

### Task 22: ThesisLedger hardcoded hex cleanup

**Files:**
- Modify: `src/components/ThesisLedger.tsx`

- [ ] **Step 1: Replace hardcoded hex colors in `ThesisLedger.tsx`**

Replace the `STATUS_STYLE` map:
```ts
const STATUS_STYLE: Record<string, { colorClass: string; label: string }> = {
  validated: { colorClass: "bg-green/10 text-green", label: "VALIDATED" },
  FALSIFIED: { colorClass: "bg-red/10 text-red",     label: "FALSIFIED" },
  untested:  { colorClass: "bg-elevated text-muted-fg", label: "untested" },
};
```

Replace the `StatusBadge` component:
```tsx
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.untested;
  return (
    <Badge variant="outline" className={cn("text-[11px] font-bold", s.colorClass)}>
      {s.label}
    </Badge>
  );
}
```

Replace the outer container `.panel` → Card:
```tsx
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

// Replace the top-level div with:
<Card className="bg-surface border-border mb-3">
  <CardHeader className="pb-3">
    <h2 className="text-[11px] uppercase tracking-[0.6px] text-muted-fg font-bold">
      Thesis ledger <span className="opacity-50 font-normal normal-case tracking-normal">· science in public</span>
    </h2>
  </CardHeader>
  <CardContent>
    {theses === undefined ? (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-14 w-full bg-elevated rounded-xl" />)}
      </div>
    ) : theses.length === 0 ? (
      <p className="text-muted-fg text-[13px]">No theses tested yet — the loop logs every trial here.</p>
    ) : (
      <div className="flex flex-col gap-2">
        {theses.map((t: any) => (
          <div key={t.thesis_id ?? t._id} className="bg-elevated border border-border rounded-xl px-3 py-2.5">
            <div className="flex justify-between gap-2 mb-1.5">
              <span className="text-[13px] font-semibold">{t.claim}</span>
              <StatusBadge status={t.status} />
            </div>
            <div className="flex gap-4 text-[12px] text-text/80">
              <span>obj <b>{fmt(t.oos_objective)}</b></span>
              <span>DSR <b>{fmt(t.deflated_sharpe, 2)}</b></span>
              {t.regime ? <span>regime <b>{t.regime}</b></span> : null}
            </div>
            {t.source && <div className="text-[11px] text-muted-fg mt-1">↳ {t.source}</div>}
          </div>
        ))}
      </div>
    )}
  </CardContent>
</Card>
```

- [ ] **Step 2: Commit**

```bash
git add src/components/ThesisLedger.tsx && git commit -m "refactor(web): ThesisLedger — replace hardcoded hex colors with CSS vars + shadcn Badge, Card"
```

---

### Task 23: Final verification

- [ ] **Step 1: Run typecheck**

```bash
cd /root/claude/projects/alien-trade/web
bun run typecheck 2>&1
```

Expected: zero errors. Fix any type errors before proceeding.

- [ ] **Step 2: Run build**

```bash
bun run build 2>&1 | tail -20
```

Expected: build succeeds, no warnings about missing modules.

- [ ] **Step 3: Start dev server and smoke test**

```bash
bun run dev &
```

Open http://localhost:5173 (or http://76.13.243.12:5173 from your browser) and verify:

- [ ] Dark background (#000000) visible ✓
- [ ] Sidebar shows lucide icons with tooltips on hover ✓
- [ ] LiveHeader shows logo, mode badge, equity, kill switch ✓
- [ ] KillSwitch hold-to-confirm still works (hold for 1.5s, conic gradient fills) ✓
- [ ] Overview page loads with stat cards and Skeleton while loading ✓
- [ ] Controls page: AlertDialog appears on "Pause Agents" and "Stop Response" ✓
- [ ] Controls page: "Switch to LIVE" shows AlertDialog (not window.confirm) ✓
- [ ] Controls page: Sliders work for risk caps ✓
- [ ] Co-pilot drawer opens as Sheet from right ✓
- [ ] Mobile (< 640px): sidebar hidden, bottom nav visible with labels ✓
- [ ] Pairing screen: 3-step wizard with QR code renders ✓
- [ ] Dark/light toggle works — all Tailwind utilities update with theme ✓
- [ ] Agent ticker scrolls at bottom ✓

- [ ] **Step 4: Restart production service**

```bash
cd /root/claude/projects/alien-trade/web
bun run build
systemctl restart alien-cockpit
```

- [ ] **Step 5: Final commit**

```bash
git add -A && git commit -m "chore(web): final verification — shadcn migration complete"
```
