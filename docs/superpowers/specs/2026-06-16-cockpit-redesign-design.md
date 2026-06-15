# Alien-Trade Cockpit — Full UI Redesign Spec
**Date:** 2026-06-16  
**Status:** Approved

---

## Goal

Redesign `web/src/` from a developer tool into a premium trader cockpit. Inspired by AlgoMaster.io's design language. The guiding principle: **a trader opens this at 2am and knows in 2 seconds if they're winning, if the agent is running, and if anything is on fire.**

---

## Architecture: Option A — Sidebar + Views

A slim 48px icon sidebar (always visible), a persistent live header, and 5 named full-page views.

```
┌────┬──────────────────────────────────────────────────────┐
│ 👾 │  ALIEN-TRADE  ● LIVE  [BULL]  $9,831  +$142  [KILL] │
│    ├──────────────────────────────────────────────────────┤
│ 📊 │                                                      │
│ ◈  │              [ Active view content ]                 │
│ 🤖 │                                                      │
│ ⚙️ │                                                      │
│ 💬 │                                                      │
└────┴──────────────────────────────────────────────────────┘
│  [ Agent activity ticker — scrolling live agent thoughts ]│
└──────────────────────────────────────────────────────────┘
```

---

## Color System

```
--bg:         #050a0f   deep space background
--surface:    #0d1520   card/panel surfaces  
--elevated:   #141f30   hover / elevated state
--border:     #1e2d42   default borders
--border-hi:  #2a4060   active/hover borders

--green:      #00ff9d   profit, running, positive
--red:        #ff3060   loss, danger, kill switch
--cyan:       #00d4ff   primary accent, brand, live data
--yellow:     #ffd60a   paper mode, warnings
--purple:     #a855f7   AI agents, co-pilot
--text:       #e8f0f8   primary text
--muted:      #6080a0   labels, timestamps
```

---

## Typography

| Role | Font |
|---|---|
| Headlines & numbers | Space Grotesk (Google Fonts) |
| UI text & labels | Inter (Google Fonts) |
| Logs, addresses, mono | JetBrains Mono (Google Fonts) |

---

## Components

### `AppShell`
Root layout: sidebar + header + main content area + bottom ticker.

### `LiveHeader` (persistent, all views)
- Logo + agent name
- `RegimeBadge` — BULL / BEAR / CHOP / CRASH pill, color-coded
- Equity (large, green/red by today's PnL)
- Cumulative PnL delta
- Mode badge — PAPER (yellow) / LIVE (red)
- `KillSwitch` — always visible red button, hold 1.5s to confirm

### `SideNav` (48px, icon-only with tooltips)
Icons for: Overview · Positions · Agents · Controls · Logs · Co-pilot

### `AgentTicker` (bottom strip, persistent)
Scrolling marquee of latest agent events: `[CoPilot · analysis] Regime shifted to BULL — increasing position sizes`

---

## Views

### 1. Overview (default)
- Full-width equity curve (recharts, prominent)
- 4 stat cards: Equity · PnL · Drawdown · Exposure
- Mini positions grid (2-up, compact cards)
- Agent status strip: 4 agents, status dot + last-active time
- Last 3 decisions (compact table)

### 2. Positions (the star feature)
Grid of `PositionCard` components, 3 columns desktop / 2 tablet / 1 mobile.

**`PositionCard`:**
- Token symbol + side badge (LONG)
- Sparkline: price history since entry (from `price_ticks` Convex table)
- Entry price → current price with arrow
- Position size + unrealized P&L (large, color-coded)
- Progress bar: current P&L % toward take-profit target
- Time since entry
- Border: green glow if profitable, red glow if losing
- Pulse animation on price update

**Empty state:** Centered alien character + "Watching the market. Waiting for my moment."

### 3. Agents
4 agent cards in a 2×2 grid:
- Agent name + role description
- Status indicator (active / recent / idle) with pulse animation
- Last message preview
- Click → opens CoPilot drawer pre-filled with "What is [Agent] currently doing?"

Agent map: CoPilot (cyan) · Historian (yellow) · Researcher (purple) · Reflector (red)

### 4. Controls
- `KillSwitch` — huge, full-width, hold-to-confirm with countdown ring
- Trading mode segmented toggle (TESTNET / PAPER / LIVE) — large, prominent
- Strategy picker — 4 large cards with name + blurb, selected state highlighted
- Autopilot toggle + numeric inputs
- Risk caps sliders
- Equity floor input

### 5. Logs
- Decisions table (full, all columns)
- Agent activity channel (full height)
- Live log console
- Wins feed

### CoPilot Drawer (slide-over panel, any view)
- Triggered by sidebar Co-pilot icon
- Slides in from the right, 420px wide, overlaps content
- Chat messages + input
- Quick-ask chips: "What's the regime?" · "Last trade?" · "Risk state?"

---

## Backend Addition Required

**`price_ticks` Convex table:**
```ts
price_ticks: defineTable({
  symbol: v.string(),
  price: v.float64(),
  timestamp_ms: v.float64(),
})
```
Python agent appends on each cycle for active position symbols.
Frontend queries last 24 ticks per symbol for sparklines.

---

## File Structure

```
web/src/
  App.tsx                     AppShell + router state
  views/
    OverviewView.tsx
    PositionsView.tsx
    AgentsView.tsx
    ControlsView.tsx
    LogsView.tsx
  components/
    AppShell.tsx
    LiveHeader.tsx
    SideNav.tsx
    PositionCard.tsx           ← hero component
    Sparkline.tsx
    AgentTicker.tsx
    CoPilotDrawer.tsx
    KillSwitch.tsx             hold-to-confirm
    RegimeBadge.tsx
    StatCard.tsx
    AgentCard.tsx
    EquityChart.tsx
    DecisionsTable.tsx
    ThesisLedger.tsx           (unchanged)
  lib/
    control.ts                 (unchanged)
    formatters.ts              (extracted from App.tsx)
  index.css                    (full new design token system)
```

---

## UX Moments

1. **Hold-to-kill**: 1.5s hold on kill switch — visual countdown ring — no browser confirm()
2. **Trade card pulse**: Price tick → card number briefly scales 1.08 → settles back
3. **Regime badge**: Always in header, color shifts with regime changes
4. **Activity ticker**: Scrolling bottom strip — agent thoughts without opening logs
5. **Empty positions alien**: Character + "Waiting for my moment" — agent feels alive
6. **PnL zero-cross**: Subtle green flash animation when cumulative PnL crosses from negative to positive

---

## What Does NOT Change

- Convex queries / mutations (all existing API calls preserved)
- `ThesisLedger.tsx` (keep as-is, embed in Positions or Overview)
- `lib/control.ts` (token logic unchanged)
- All mutation logic (kill switch, mode, floor, autopilot — same calls, new buttons)

---

## Out of Scope

- Mobile bottom tab bar (PWA mobile addressed via responsive CSS only)
- Real-time price feed from external API (sparklines use Convex `price_ticks`)
- Dark/light mode toggle
- User preferences persistence
