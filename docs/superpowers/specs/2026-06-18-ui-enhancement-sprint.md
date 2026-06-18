# Alien-Trade UI Enhancement Sprint — Design Spec
**Date:** 2026-06-18  
**Branch:** AT-2-awake-sprint-productization

---

## Overview

Five targeted improvements to the Alien-Trade cockpit PWA:

1. Thread delete in Co-Pilot drawer
2. Wider Co-Pilot chat area
3. Trading candlestick chart view
4. Step-by-step onboarding tutorial
5. Logo integration via CSS `mix-blend-mode: screen`

---

## Feature 1: Thread Delete Button

**Problem:** The Co-Pilot thread sidebar has no way to remove threads once created.

**Solution:** Add an `×` delete button that appears on hover for each thread row (not for "Default"). Clicking calls a new Convex mutation `copilot.deleteThread`. If the deleted thread is currently active, fall back to `null` (Default view).

**Files touched:**
- `convex/copilot.ts` — add `deleteThread` mutation (takes `thread_id`, deletes thread doc + all its messages)
- `web/src/components/CoPilotDrawer.tsx` — render `×` button on hover per thread row, call `deleteThread`

**Behaviour:**
- Deleting Default is not allowed (button not rendered on that row)
- Optimistic removal: thread disappears immediately, Convex syncs in background
- No confirmation dialog — quick destructive action acceptable here given low stakes

---

## Feature 2: Wider Co-Pilot Chat Area

**Problem:** The sheet drawer is 560px wide; 160px is consumed by the thread sidebar, leaving only 400px of chat width.

**Solution:**
- Increase `SheetContent` width from `w-[560px]` → `w-[720px]`
- Shrink thread sidebar from `w-[160px]` → `w-[140px]`  
- Net chat area grows from ~400px → ~580px
- Mobile (`max-sm`): thread sidebar hidden by default; a `☰` icon button in the chat header toggles it open as a slide-over

**Files touched:**
- `web/src/components/CoPilotDrawer.tsx` — update widths + mobile sidebar toggle

---

## Feature 3: Trading Candlestick Chart View

**Problem:** No visual price chart exists in the cockpit.

**Solution:** Add a new `"chart"` view using `lightweight-charts` (TradingView OSS, Apache 2.0).

**Library:** `lightweight-charts` — installed via `bun add lightweight-charts`

**New files:**
- `web/src/views/ChartView.tsx` — the new view
- `web/src/components/TradingChart.tsx` — wraps `lightweight-charts` in a React component

**ChartView layout:**
- Symbol selector at top (pill buttons: ETH · CAKE · UNI · LINK · AAVE)
- `TradingChart` component below, full-width, height ~480px
- Fallback message when < 2 price ticks exist: `"Waiting for price data…"`

**TradingChart component:**
- Creates a `createChart()` instance in a `useEffect`, attaches to a `<div ref>`
- Reads `priceTicks.forSymbol` from Convex (already exists)
- Converts ticks to OHLC bars (since ticks are scalar prices, synthesise O=H=L=C=price for now — real OHLC can be added when the agent writes OHLCV bars)
- Trade markers: queries `ledger.recent` (or `trades` table), overlays green ▲ (buy) / red ▼ (sell) markers at trade timestamps
- Cleans up chart instance on unmount

**SideNav addition:**
- `LineChart` icon (lucide) added between Pipeline and Positions
- View type `"chart"` added to the `View` union in `SideNav.tsx`
- `BottomNav.tsx` updated to include Chart

**App.tsx:**
- `case "chart": return <ChartView />` added to `renderView()`

---

## Feature 4: Step-by-Step Onboarding Tutorial

**Problem:** New users don't know how to navigate or operate the cockpit.

**Solution:** A guided tour triggered by a button. Uses **`driver.js`** (lightweight, framework-agnostic, ~5KB gzipped).

**Library:** `driver.js` — installed via `bun add driver.js`

**Tour steps:**

| Step | Element selector | Title | Description |
|------|-----------------|-------|-------------|
| 1 | `[data-tour="brand"]` | Welcome to Alien-Trade | Your autonomous BSC trading cockpit. This tour takes 30 seconds. |
| 2 | `[data-tour="kill-switch"]` | Kill Switch | Halt all trading instantly. Red = halted, Green = active. |
| 3 | `[data-tour="nav-overview"]` | Overview | Live PnL, drawdown, signal scores, and agent heartbeat. |
| 4 | `[data-tour="nav-chart"]` | Chart | Candlestick price chart with your trade entries and exits. |
| 5 | `[data-tour="nav-portfolio"]` | Portfolio | Your TWAK self-custody wallet holdings in real time. |
| 6 | `[data-tour="nav-controls"]` | Controls | Set risk limits, position size cap, and equity floor. |
| 7 | `[data-tour="nav-copilot"]` | Co-Pilot | Ask the agent anything in natural language. |
| 8 | `[data-tour="nav-tour"]` | You're all set | The agent is watching the market 24/7. Come back here anytime. |

**`data-tour` attributes** added to the corresponding DOM elements in:
- `LiveHeader.tsx` — brand mark, kill switch
- `SideNav.tsx` — each nav item + copilot button + tour button
- `BottomNav.tsx` — mobile equivalents (same attributes)

**Tour button:**
- `GraduationCap` icon, positioned above the Co-Pilot button in `SideNav.tsx`
- Tooltip: "Start tour"
- On mobile: added to `BottomNav` or accessible via a `?` chip in Overview

**New file:** `web/src/lib/tour.ts`
- `startTour()` function — creates and drives the driver.js instance
- `hasTourBeenSeen()` / `markTourSeen()` — `localStorage` helpers
- Tour auto-launches on first login (after pairing), never again unless user clicks the button

**driver.js theming:** Override the default white popover to match the app's dark theme via the `popoverClass` option and a small CSS block in `globals.css`.

---

## Feature 5: Logo Integration

**Asset:** `docs/logo.png` (2048×2048 RGBA, opaque dark-teal background)

**Approach:** CSS `mix-blend-mode: screen` — on a dark background the near-black pixels become invisible, showing only the bright alien + glow. No image processing needed.

**Steps:**
1. Copy `docs/logo.png` → `web/public/logo.png`
2. Update `web/index.html` favicon to `/logo.png`

**Usage in UI:**

| Location | Size | Treatment |
|----------|------|-----------|
| `LiveHeader.tsx` — replaces pulsing dot | 28px circle, `object-cover`, `mix-blend-mode: screen` | Left of "ALIEN·TRADE" text |
| `App.tsx` `PairingScreen` welcome step | 72px circle, same blend | Above "ALIEN·TRADE" heading |
| `LandingView.tsx` hero section | 96px circle, same blend | Hero logo |

**CSS class added to `globals.css`:**
```css
.logo-blend {
  mix-blend-mode: screen;
  border-radius: 50%;
}
```

---

## Non-Goals

- No backend changes except the `deleteThread` mutation
- No rembg / image processing (using CSS blend mode instead)
- No changes to the strategy or agent code
- No new Convex tables — chart uses existing `priceTicks`

---

## Acceptance Criteria

- [ ] Threads can be deleted; active thread falls back to Default
- [ ] Co-Pilot chat area is visibly wider; mobile sidebar toggles correctly
- [ ] Chart view renders candlestick data for all 5 symbols; trade markers appear
- [ ] Tour launches on first login; re-launchable via Tour button; Skip works at any step
- [ ] Logo appears in header, pairing wizard, and landing page without visible dark box
- [ ] `bun run build` passes with no type errors
