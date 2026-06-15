# Alien-Trade Cockpit — shadcn/Tailwind Migration Design

**Date:** 2026-06-16
**Branch:** AT-2-awake-sprint-productization
**Status:** Approved — ready for implementation planning

---

## Context

The Alien-Trade cockpit (`web/`) is a React 18 + Vite + Convex PWA. It currently uses a hand-rolled CSS design system in `index.css` (CSS custom properties + class names). The goal is a big-bang migration to Tailwind CSS v4 + shadcn/ui so the cockpit is production-grade, open-source–ready, and a foundation for commercial SaaS.

**Non-goals:** React Router, React Native, changing Convex schema, changing any Python/agent code.

---

## Approach: Big-Bang Migration

All components migrate in one sprint. No half-states shipped to production. The app must build and look correct at every commit — the migration is executed in a strict dependency order so each step leaves the app working.

**Latency impact: zero.** Tailwind v4 JIT generates only used classes at build time. CSS bundle will be smaller than the current hand-rolled `index.css`. No runtime styling overhead.

---

## 1. Token Strategy

### Source of truth: preserve existing custom properties

The existing CSS custom properties (`--bg`, `--surface`, `--elevated`, `--border`, `--border-hi`, `--cyan`, `--green`, `--red`, `--yellow`, `--purple`, `--text`, `--muted`) are the design system. They are **not replaced** — they are re-declared in `globals.css` and extended into Tailwind.

### `src/globals.css` replaces `src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Alien-Trade design tokens — unchanged */
    --bg:        #000000;
    --surface:   #080d14;
    --elevated:  #0d1520;
    --border:    #172030;
    --border-hi: #243650;
    --green:     #00ff9d;
    --red:       #ff3060;
    --cyan:      #00d4ff;
    --yellow:    #ffd60a;
    --purple:    #a855f7;
    --text:      #e8f0f8;
    --muted:     #5878a0;
    color-scheme: dark;

    /* shadcn required vars — mapped to our tokens.
       NOTE: --border is shared (same name, same meaning in both systems — no alias needed).
       NOTE: shadcn's --muted = surface background; our --muted = text color.
             Resolved by mapping shadcn's --muted to --elevated and
             shadcn's --muted-foreground to our muted text value.
             JSX must use text-muted-foreground utility, not color:var(--muted). */
    --background:         var(--bg);
    --foreground:         var(--text);
    --card:               var(--surface);
    --card-foreground:    var(--text);
    --popover:            var(--surface);
    --popover-foreground: var(--text);
    --primary:            var(--cyan);
    --primary-foreground: #040d14;
    --secondary:          var(--elevated);
    --secondary-foreground: var(--text);
    --muted:              var(--elevated);
    --muted-foreground:   #5878a0;
    --accent:             var(--elevated);
    --accent-foreground:  var(--text);
    --destructive:        var(--red);
    --destructive-foreground: #fff;
    --input:              var(--border);
    --ring:               var(--cyan);
    --radius:           0.625rem;
  }

  [data-theme="light"] {
    --bg:        #f0f4f8;
    --surface:   #ffffff;
    --elevated:  #e8edf4;
    --border:    #d0dae8;
    --border-hi: #a8bcd4;
    --green:     #00a86b;
    --red:       #e02050;
    --cyan:      #0098c8;
    --yellow:    #c89800;
    --purple:    #8030d0;
    --text:      #0a1828;
    --muted:     #5878a0;
    color-scheme: light;
  }
}

/* Hand-rolled rules that MUST stay — not expressible as Tailwind utilities */

/* Kill switch conic-gradient countdown — set via inline style in KillSwitch.tsx */
.kill-switch, .kill-switch-hero {
  user-select: none;
  -webkit-user-select: none;
  touch-action: none;
}

/* Agent ticker scroll animation */
@keyframes ticker-scroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}

/* Log console font override */
.logconsole {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  line-height: 1.5;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
  }
}
```

### `tailwind.config.ts`

Extends Tailwind's color palette with our custom property aliases so utility classes like `bg-surface`, `text-cyan`, `border-border` work directly in JSX.

```ts
// Key extension — maps Tailwind utilities to our CSS vars
theme: {
  extend: {
    colors: {
      bg:       "var(--bg)",
      surface:  "var(--surface)",
      elevated: "var(--elevated)",
      border:   "var(--border)",
      "border-hi": "var(--border-hi)",
      green:    "var(--green)",
      red:      "var(--red)",
      cyan:     "var(--cyan)",
      yellow:   "var(--yellow)",
      purple:   "var(--purple)",
      text:     "var(--text)",
      muted:    "var(--muted)",
    },
    fontFamily: {
      grotesk: ["Space Grotesk", "sans-serif"],
      mono:    ["IBM Plex Mono", "monospace"],
    },
  }
}
```

---

## 2. Component Migration Map

### shadcn components to install

```
bunx shadcn@latest add alert-dialog sheet button input slider tooltip skeleton sonner badge card dialog select
```

### Full migration table

| Current pattern | Replaced by | Constraints |
|---|---|---|
| `window.confirm()` in ControlsView (2×) | `<AlertDialog>` | Must wrap async Convex mutations correctly |
| `CoPilotDrawer` custom CSS drawer | `<Sheet side="right">` | Keep framer-motion spring on open/close |
| `.btn`, `.btn--*` classes | `<Button variant="...">` | Variants: `default`(cyan), `destructive`(red), `outline`, `ghost`, `secondary` |
| `.num-input` | `<Input>` | Styled via shadcn token map |
| `<input type="range">` in ControlsView | `<Slider>` | 3 sliders: max position, daily loss, max drawdown |
| `.nav-icon` buttons without tooltips | `<Tooltip>` wrapping each SideNav icon | Desktop sidebar only; not on mobile bottom bar |
| `undefined` Convex query states | `<Skeleton>` | Every `useQuery` that can return `undefined` |
| Kill switch toggle / equity floor / trade events | `<Sonner>` toast | Provider in `App.tsx`; 3 toast triggers |
| `.tag`, `.tag-*` classes | `<Badge>` | Color overrides via `className` |
| `RegimeBadge` custom spans | `<Badge variant="outline">` | Per-regime color via `className` override |
| `.strategy-card` buttons | `<Card>` + `<CardContent>` | Active state: `ring-1 ring-cyan` |
| `.panel` divs | `<Card>` | |
| Pairing screen bare `<input>` | `<Dialog>` 3-step wizard | With `qrcode` npm package |
| ThesisLedger `#34d399`, `#f87171` hardcoded | `text-green`, `text-red` Tailwind classes | |
| `(api as any).priceTicks` | `api.priceTicks.forSymbol` | Run `bunx convex dev --once` first |
| Mobile: SideNav at <640px | Bottom tab bar (icons + labels, 44px) | Conditional render in AppShell |
| View switches (no animation) | `<AnimatePresence>` fade+Y in App.tsx | 150ms, `y: 8` → `0` |
| No error boundaries | `<ErrorBoundary>` per view | Use `react-error-boundary` package |
| LiveHeader symbol (hardcoded) | `<Select>` pulling symbols from Convex | New Convex query: `api.positions.symbols` |

### Do NOT migrate

- `KillSwitch.tsx` — conic-gradient hold mechanic stays as custom CSS + framer-motion. Wrapping in `<Button>` would lose the hold UX.
- `EquityChart.tsx`, `Sparkline.tsx` — recharts stays.
- framer-motion on `PositionCard`, alert banners, `CoPilotDrawer` slide — all kept.
- `AgentTicker` keyframe — stays in globals.css.
- All Convex mutations — unchanged. `withToken()` wrapper stays on every mutation.
- No React Router added.

---

## 3. New Features

### Mobile bottom nav (icons + labels)

- Renders below 640px, replaces the 52px sidebar
- 5 tabs: Overview · Positions · Agents · Controls · Logs
- Each tab: icon (SVG, 18px) + label (9px, font-bold)
- Active tab: `text-cyan bg-elevated` pill background
- Inactive: `text-muted`
- Height: 44px (meets touch target minimum)
- Implementation: conditional render in `AppShell.tsx` via CSS `hidden sm:flex` / `flex sm:hidden`

### Pairing screen — 3-step Dialog wizard

**Step 1 — Welcome**
- ALIEN-TRADE logo (cyan, Space Grotesk)
- Tagline: "Autonomous trading cockpit"
- "Connect your agent →" button

**Step 2 — Pair device**
- QR code encodes `window.location.href` (the cockpit URL itself) via `qrcode` npm package, rendered to `<canvas>`. This lets mobile users navigate to the cockpit URL on their phone, then enter the control token manually. No env var required — it works for any deployment URL.
- "or paste token" divider
- `<Input type="password">` for control token
- "Pair cockpit →" button (disabled until input non-empty)

**Step 3 — Confirmed**
- Checkmark animation (framer-motion scale-in)
- "Cockpit paired. You're in." message
- Auto-dismisses after 1.5s, transitions to main app

Dialog is not dismissable via overlay click — must complete pairing to proceed.

### Sonner toast triggers

| Event | Toast type | Content |
|---|---|---|
| Kill switch toggled to HALTED | `toast.error()` | "Trading halted" + "Resume" action button |
| Kill switch toggled to RESUME | `toast.success()` | "Trading resumed" |
| Equity floor hit (detected via agentEvents) | `toast.error({ duration: Infinity })` | "Equity floor hit — agent halted" |
| Trade executed (new position in Convex) | `toast.success()` | "{symbol} {side} executed" |

Toast provider: `<Toaster position="bottom-right" theme="dark" />` in `App.tsx`.

### Symbol switcher in LiveHeader

- `<Select>` component showing distinct symbols from open positions
- Defaults to "ALL" (current behaviour — show all)
- Selecting a symbol filters PositionsView and focuses EquityChart
- Source: new `api.positions.symbols` query (returns `string[]` of distinct symbols from open positions)

### Error boundaries

- `react-error-boundary` package
- Each view wrapped: `<ErrorBoundary FallbackComponent={ViewError}>`
- `ViewError` fallback: card with error message + "Reload view" button that calls `resetErrorBoundary()`

---

## 4. Execution Order

Steps must be executed in this order. Each step leaves the app in a working state.

1. **Foundation** — Install Tailwind v4, shadcn, react-error-boundary, qrcode. Write `globals.css`. Configure `tailwind.config.ts`. Verify `bun run build` passes with zero visual change.
2. **Fix type hack** — Run `bunx convex dev --once` to regenerate types. Replace `(api as any).priceTicks` with `api.priceTicks.forSymbol` in `PositionCard.tsx`.
3. **Migrate layout classes** — Convert `AppShell`, `SideNav`, `LiveHeader`, `AgentTicker` to Tailwind utilities. Delete those CSS classes from `globals.css`.
4. **Migrate primitive components** — `StatCard`, `RegimeBadge`, `Sparkline`, `KillSwitch` (layout only, not the hold mechanic).
5. **Migrate views** — `LogsView` → `AgentsView` → `PositionsView` → `OverviewView` → `ControlsView`.
6. **Add shadcn interaction components** — AlertDialog (ControlsView confirms), Sheet (CoPilotDrawer), Slider (risk caps), Tooltip (SideNav), Skeleton (all loading states), Badge (tags + RegimeBadge), Card (panels + strategy cards), Button (all buttons), Input (all inputs).
7. **Add Sonner** — Provider in App.tsx + 3 toast trigger sites.
8. **Mobile bottom nav** — Conditional render in AppShell, new `BottomNav` component.
9. **Page transitions** — `AnimatePresence` on `renderView()` in App.tsx.
10. **Error boundaries** — Wrap each view.
11. **Pairing screen wizard** — 3-step Dialog with qrcode canvas.
12. **Symbol switcher** — New Convex query + `<Select>` in LiveHeader.
13. **ThesisLedger hex cleanup** — Replace hardcoded hex colors with Tailwind classes.
14. **Final verification** — `bun run typecheck`, `bun run build`, manual smoke test of kill switch hold, equity chart, co-pilot drawer, mobile layout.

---

## 5. Constraints (must be honoured throughout)

- Kill switch hold-to-confirm mechanic (conic-gradient + 1.5s interval) must survive intact
- Pure black `#000000` background preserved
- framer-motion on PositionCard price pulse preserved
- recharts for all charts — do not replace
- AgentTicker at bottom of AppShell preserved
- No React Router — view switching stays as `useState<View>`
- All Convex mutations stay wrapped with `withToken()`
- No shadcn components on the hot trading path (signals, execution)
