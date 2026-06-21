# Cockpit Redesign Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task.

**Goal:** Replace the utilitarian cockpit with a premium trader UI — sidebar nav, trade card grid with sparklines, neon design system, hold-to-confirm kill switch.

**Architecture:** Option A (sidebar + views). No React Router — `useState<View>` in App.tsx. Convex reactive queries unchanged. New `price_ticks` table feeds sparklines.

**Tech Stack:** React 18, Vite, Convex, framer-motion, recharts, @fontsource/space-grotesk, @fontsource/inter

---

### Task 1: Fonts + CSS design tokens

**Files:**
- Modify: `web/package.json`
- Modify: `web/src/main.tsx`
- Modify: `web/index.html`
- Rewrite: `web/src/index.css`

- [ ] Install new fonts
```bash
cd /root/claude/projects/alien-trade/web
bun add @fontsource/space-grotesk @fontsource/inter
```

- [ ] Update `web/src/main.tsx` — replace IBM Plex Sans imports, keep Mono
```tsx
import "@fontsource/space-grotesk/400.css";
import "@fontsource/space-grotesk/600.css";
import "@fontsource/space-grotesk/700.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
// keep everything else unchanged
```

- [ ] Update `web/index.html` theme-color
```html
<meta name="theme-color" content="#050a0f" />
<title>Alien-Trade · Cockpit</title>
```

- [ ] Rewrite `web/src/index.css` (full replacement)
```css
:root {
  --bg:        #050a0f;
  --surface:   #0d1520;
  --elevated:  #141f30;
  --border:    #1e2d42;
  --border-hi: #2a4060;
  --green:     #00ff9d;
  --red:       #ff3060;
  --cyan:      #00d4ff;
  --yellow:    #ffd60a;
  --purple:    #a855f7;
  --text:      #e8f0f8;
  --muted:     #6080a0;
  color-scheme: dark;
  font-family: "Inter", ui-sans-serif, system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  font-variant-numeric: tabular-nums;
}
* { box-sizing: border-box; }
body { margin: 0; padding: 0; overflow: hidden; }

/* ── Shell ── */
.app-shell { display: flex; flex-direction: column; height: 100vh; }
.app-body  { display: flex; flex: 1; overflow: hidden; }
.app-main  { flex: 1; overflow-y: auto; padding: 20px 24px 48px; }

/* ── Side nav ── */
.side-nav {
  width: 52px; background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column; align-items: center;
  padding: 12px 0; gap: 4px; flex-shrink: 0;
}
.nav-icon {
  width: 40px; height: 40px; border-radius: 10px; border: none;
  background: transparent; color: var(--muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; transition: background .15s, color .15s;
}
.nav-icon:hover { background: var(--elevated); color: var(--text); }
.nav-icon--active { background: var(--elevated); color: var(--cyan); }
.nav-spacer { flex: 1; }

/* ── Live header ── */
.live-header {
  height: 56px; background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 16px; gap: 14px; flex-shrink: 0;
}
.header-logo {
  font-family: "Space Grotesk", sans-serif;
  font-size: 15px; font-weight: 700; letter-spacing: 2px; color: var(--cyan);
}
.header-equity {
  font-family: "Space Grotesk", sans-serif; font-size: 22px; font-weight: 700;
}
.header-pnl { font-size: 13px; font-weight: 600; }
.header-sep { width: 1px; height: 28px; background: var(--border); }
.header-spacer { flex: 1; }

/* ── Regime badge ── */
.regime-badge {
  padding: 3px 10px; border-radius: 999px;
  font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
}

/* ── Mode badge ── */
.mode-badge {
  padding: 3px 10px; border-radius: 6px;
  font-size: 11px; font-weight: 700; letter-spacing: 1px;
}
.mode-badge--paper   { background: #ffd60a18; color: var(--yellow); border: 1px solid #ffd60a30; }
.mode-badge--mainnet { background: #ff306018; color: var(--red);    border: 1px solid #ff306030; }
.mode-badge--testnet { background: #00d4ff18; color: var(--cyan);   border: 1px solid #00d4ff30; }

/* ── Status dot ── */
.status-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; display: inline-block;
}

/* ── Agent ticker ── */
.agent-ticker {
  height: 30px; background: var(--surface); border-top: 1px solid var(--border);
  display: flex; align-items: center; overflow: hidden; flex-shrink: 0;
}
.ticker-track {
  display: flex; gap: 64px; white-space: nowrap;
  animation: ticker-scroll 80s linear infinite;
}
@keyframes ticker-scroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}
.ticker-item { font-size: 11px; color: var(--muted); }
.ticker-item__agent { font-weight: 700; margin-right: 5px; }

/* ── Stat card ── */
.stat-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: 16px;
}
.stat-label {
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.6px; color: var(--muted); margin-bottom: 8px;
}
.stat-value {
  font-family: "Space Grotesk", sans-serif;
  font-size: 26px; font-weight: 700; line-height: 1;
}
.stat-sub { font-size: 12px; color: var(--muted); margin-top: 6px; }

/* ── Kill switch (header size) ── */
.kill-switch {
  width: 44px; height: 44px; border-radius: 50%; border: none;
  cursor: pointer; padding: 3px; display: flex; align-items: center;
  justify-content: center; flex-shrink: 0;
  user-select: none; -webkit-user-select: none; touch-action: none;
}
.kill-switch__inner {
  width: 100%; height: 100%; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 8px; font-weight: 900; letter-spacing: 0.5px;
  pointer-events: none;
}
.kill-switch--halt   .kill-switch__inner { background: #12040a; color: var(--red); }
.kill-switch--resume .kill-switch__inner { background: #01120a; color: var(--green); }
/* ── Kill switch (hero size for ControlsView) ── */
.kill-switch-hero {
  width: 120px; height: 120px; border-radius: 50%; border: none;
  cursor: pointer; padding: 5px; display: flex; align-items: center;
  justify-content: center; margin: 0 auto;
  user-select: none; -webkit-user-select: none; touch-action: none;
}
.kill-switch-hero .kill-switch__inner {
  font-size: 14px; font-weight: 900; letter-spacing: 1px;
}

/* ── Positions grid ── */
.positions-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
@media (max-width: 1200px) { .positions-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px)  { .positions-grid { grid-template-columns: 1fr; } }

/* ── Position card ── */
.position-card {
  background: var(--surface); border-radius: 16px; padding: 16px;
  border: 1px solid var(--border);
  transition: border-color .3s, box-shadow .3s;
}
.position-card--win  { border-color: #00ff9d30; box-shadow: 0 0 20px #00ff9d0a; }
.position-card--loss { border-color: #ff306030; box-shadow: 0 0 20px #ff30600a; }
.position-card__header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;
}
.position-card__symbol {
  font-family: "Space Grotesk", sans-serif; font-size: 17px; font-weight: 700;
}
.position-card__side {
  font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 6px;
  background: #00d4ff18; color: var(--cyan); letter-spacing: 1px;
}
.sparkline-empty {
  height: 56px; background: var(--elevated); border-radius: 8px; margin-bottom: 10px;
}
.position-card__prices {
  display: flex; align-items: center; gap: 8px; margin: 10px 0 8px;
}
.price-col { flex: 1; }
.price-label { font-size: 10px; color: var(--muted); margin-bottom: 2px; }
.price-value {
  font-family: "Space Grotesk", sans-serif; font-size: 13px; font-weight: 600;
}
.price-arrow { color: var(--muted); font-size: 14px; }
.position-card__stats {
  display: flex; justify-content: space-between; align-items: center; margin-top: 8px;
}
.position-card__size { font-size: 12px; color: var(--muted); }
.position-card__pnl  {
  font-family: "Space Grotesk", sans-serif; font-size: 15px; font-weight: 700;
}
.pnl--pos { color: var(--green); }
.pnl--neg { color: var(--red); }

/* ── Agent card ── */
.agents-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;
}
@media (max-width: 640px) { .agents-grid { grid-template-columns: 1fr; } }
.agent-card {
  background: var(--surface); border: 1px solid var(--border); border-radius: 16px;
  padding: 20px; cursor: pointer;
  transition: border-color .2s, background .2s;
}
.agent-card:hover { background: var(--elevated); }
.agent-card__header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.agent-card__avatar {
  width: 42px; height: 42px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 900; flex-shrink: 0;
}
.agent-card__name {
  font-family: "Space Grotesk", sans-serif; font-size: 16px; font-weight: 700;
}
.agent-card__role { font-size: 12px; color: var(--muted); }
.agent-card__last {
  font-size: 13px; color: var(--text); opacity: .8; line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.agent-card__meta { font-size: 11px; color: var(--muted); margin-top: 8px; }

/* ── Panel ── */
.panel {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: 20px; margin-bottom: 16px;
}
.panel-title {
  font-family: "Space Grotesk", sans-serif; font-size: 12px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.6px; color: var(--muted); margin: 0 0 14px;
}

/* ── Overview stats grid ── */
.overview-stats {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;
}
@media (max-width: 900px) { .overview-stats { grid-template-columns: repeat(2, 1fr); } }

/* ── Tables ── */
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: .4px; }

/* ── Tags ── */
.tag { padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; }
.tag-allow    { background: #00ff9d18; color: var(--green); }
.tag-block    { background: #ff306018; color: var(--red); }
.tag-reduce   { background: #ffd60a18; color: var(--yellow); }
.tag-observe  { background: #00ff9d18; color: var(--green); }
.tag-analysis { background: #00d4ff18; color: var(--cyan); }
.tag-verdict  { background: #ffd60a18; color: var(--yellow); }
.tag-action   { background: #a855f718; color: var(--purple); }
.tag-handoff  { background: #00ff9d10; color: #86efac; }
.tag-control  { background: #ff306018; color: var(--red); }

/* ── Buttons ── */
.btn {
  border: none; border-radius: 10px; padding: 10px 18px;
  font-weight: 700; cursor: pointer; font-size: 13px; font-family: inherit;
  transition: opacity .15s, transform .1s;
}
.btn:hover:not(:disabled) { opacity: .85; transform: translateY(-1px); }
.btn:active:not(:disabled) { transform: translateY(0); }
.btn:disabled { opacity: .35; cursor: default; }
.btn--halt    { background: var(--red);    color: #1a0608; }
.btn--resume  { background: var(--green);  color: #011408; }
.btn--pause   { background: var(--yellow); color: #141000; }
.btn--ghost   { background: var(--elevated); color: var(--muted); border: 1px solid var(--border); }
.btn--primary { background: var(--cyan);   color: #040d14; }
.btn--danger  { background: #ff306018; color: var(--red); border: 1px solid #ff306030; }
.btn--sm { padding: 6px 12px; font-size: 12px; border-radius: 8px; }

/* ── Strategy cards ── */
.strategy-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.strategy-card {
  background: var(--elevated); border: 1.5px solid var(--border);
  border-radius: 12px; padding: 14px; cursor: pointer; text-align: left;
  transition: border-color .15s; font-family: inherit; width: 100%;
}
.strategy-card:hover { border-color: var(--border-hi); }
.strategy-card--active { border-color: var(--cyan); background: #00d4ff0c; }
.strategy-card__name { font-weight: 700; font-size: 14px; color: var(--text); margin-bottom: 4px; }
.strategy-card__blurb { font-size: 12px; color: var(--muted); line-height: 1.4; }

/* ── Segmented toggle ── */
.seg {
  display: inline-flex; background: var(--bg); border: 1px solid var(--border);
  border-radius: 10px; padding: 3px; gap: 3px; width: 100%;
}
.seg-btn {
  flex: 1; border: none; background: transparent; color: var(--muted); cursor: pointer;
  padding: 8px 12px; border-radius: 8px; font-weight: 700; font-size: 12px;
  text-transform: uppercase; letter-spacing: .4px; font-family: inherit;
  transition: background .15s, color .15s;
}
.seg-btn:disabled { cursor: default; opacity: .4; }
.seg-btn--active.seg-btn--testnet { background: #00d4ff18; color: var(--cyan); }
.seg-btn--active.seg-btn--paper   { background: #ffd60a18; color: var(--yellow); }
.seg-btn--active.seg-btn--mainnet { background: #ff306018; color: var(--red); }

/* ── Inputs ── */
.num-input {
  background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
  color: var(--text); padding: 9px 12px; font-size: 13px;
  font-family: "JetBrains Mono", "IBM Plex Mono", monospace; width: 120px;
  transition: border-color .15s;
}
.num-input:focus { outline: none; border-color: var(--cyan); }

/* ── Channel / log ── */
.channel {
  display: flex; flex-direction: column; gap: 6px;
  max-height: 500px; overflow-y: auto; padding-right: 4px;
}
.evt { background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; }
.evt-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; flex-wrap: wrap; }
.evt-agent { font-weight: 700; font-size: 12px; }
.evt-time  { font-size: 11px; color: var(--muted); margin-left: auto; }
.evt-cycle { font-size: 10px; color: var(--border-hi); font-family: "IBM Plex Mono", monospace; }
.evt-headline { font-size: 13px; color: var(--text); line-height: 1.4; }

.logconsole {
  max-height: 320px; overflow-y: auto;
  font-family: "IBM Plex Mono", monospace; font-size: 11px; line-height: 1.5;
  background: #02060c; border: 1px solid var(--border); border-radius: 8px; padding: 10px;
}
.logline { display: flex; gap: 8px; padding: 1px 0; white-space: nowrap; }
.logline .log-time    { color: #364a60; flex-shrink: 0; }
.logline .log-type    { color: var(--cyan); flex-shrink: 0; min-width: 96px; }
.logline .log-cycle   { color: #364a60; flex-shrink: 0; }
.logline .log-payload { color: #7090aa; overflow: hidden; text-overflow: ellipsis; }
.log-warn  .log-payload { color: var(--yellow); }
.log-error .log-payload { color: var(--red); }
.log-error .log-type    { color: var(--red); }

/* ── Co-pilot drawer ── */
.copilot-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.5); z-index: 90;
}
.copilot-drawer {
  position: fixed; top: 0; right: 0; bottom: 0; width: 420px;
  background: var(--surface); border-left: 1px solid var(--border);
  z-index: 100; display: flex; flex-direction: column;
}
@media (max-width: 480px) { .copilot-drawer { width: 100%; } }
.copilot-drawer__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid var(--border);
}
.copilot-drawer__title {
  font-family: "Space Grotesk", sans-serif; font-weight: 700; font-size: 16px;
  color: var(--purple);
}
.copilot-drawer__messages {
  flex: 1; overflow-y: auto; padding: 16px 20px;
  display: flex; flex-direction: column; gap: 10px;
}
.copilot-drawer__chips {
  display: flex; gap: 6px; padding: 8px 20px 0; flex-wrap: wrap;
}
.copilot-drawer__input-row {
  display: flex; gap: 8px; padding: 12px 20px 16px; border-top: 1px solid var(--border);
}
.chip {
  background: var(--elevated); border: 1px solid var(--border); border-radius: 20px;
  padding: 4px 12px; font-size: 12px; color: var(--muted); cursor: pointer;
  font-family: inherit; transition: color .15s, border-color .15s;
}
.chip:hover { color: var(--text); border-color: var(--border-hi); }
.chat-msg {
  padding: 10px 14px; border-radius: 12px; font-size: 13px; line-height: 1.5; max-width: 92%;
}
.chat-msg--user { background: #00d4ff12; border: 1px solid #00d4ff20; align-self: flex-end; }
.chat-msg--assistant { background: var(--elevated); border: 1px solid var(--border); align-self: flex-start; }
.chat-msg__role { font-size: 10px; font-weight: 700; margin-bottom: 4px; }
.chat-msg--user .chat-msg__role { color: var(--cyan); }
.chat-msg--assistant .chat-msg__role { color: var(--purple); }

/* ── Alerts ── */
.alert-banner {
  border-radius: 12px; padding: 12px 16px; margin-bottom: 12px;
  font-weight: 600; font-size: 13px;
}
.alert-banner--halt { background: #ff306018; color: var(--red);    border: 1px solid #ff306040; }
.alert-banner--warn { background: #ffd60a18; color: var(--yellow); border: 1px solid #ffd60a30; }

/* ── Feedback rate buttons ── */
.btn-rate {
  background: var(--elevated); border: 1px solid var(--border); border-radius: 6px;
  cursor: pointer; font-size: 13px; line-height: 1; padding: 7px 10px;
  min-width: 34px; min-height: 32px; transition: background .15s, transform .1s;
}
.btn-rate:hover { background: var(--border); transform: translateY(-1px); }

/* ── Empty state ── */
.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 64px 32px; text-align: center; gap: 12px;
}
.empty-state__icon  { font-size: 52px; }
.empty-state__title { font-family: "Space Grotesk", sans-serif; font-size: 18px; font-weight: 700; }
.empty-state__sub   { font-size: 14px; color: var(--muted); max-width: 320px; }

/* ── Pairing screen ── */
.pairing-screen { display: grid; place-items: center; height: 100vh; }
.pairing-card {
  max-width: 400px; width: 90%; text-align: center; padding: 40px 32px;
  background: var(--surface); border: 1px solid var(--border); border-radius: 20px;
}
.pairing-title {
  font-family: "Space Grotesk", sans-serif; font-size: 28px; font-weight: 700;
  color: var(--cyan); letter-spacing: 2px; margin-bottom: 8px;
}
.pairing-sub { font-size: 14px; color: var(--muted); margin-bottom: 24px; line-height: 1.6; }

/* ── Win cards ── */
.win-card {
  background: #00ff9d08; border: 1px solid #00ff9d20; border-radius: 12px; padding: 12px 14px;
}

/* ── AP row ── */
.ap-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.ap-row span { font-size: 13px; color: var(--muted); }
.ap-row .num-input { width: 80px; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
  }
}
@media (pointer: coarse) {
  .seg-btn { min-height: 44px; }
  .nav-icon { width: 44px; height: 44px; }
  .btn-rate { min-width: 44px; min-height: 44px; }
}
```

- [ ] Verify dev server starts: `cd /root/claude/projects/alien-trade/web && bun run dev`

- [ ] Commit
```bash
git add web/src/index.css web/src/main.tsx web/index.html web/package.json web/bun.lock
git commit -m "feat(ui): new design token system — Space Grotesk, Inter, neon palette"
```

---

### Task 2: formatters.ts + tests

**Files:**
- Create: `web/src/lib/formatters.ts`
- Create: `web/src/lib/formatters.test.ts`

- [ ] Create `web/src/lib/formatters.ts`
```ts
export const usd = (n?: number | null) =>
  n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });

export const pct = (n?: number | null) =>
  n == null ? "—" : `${(n * 100).toFixed(2)}%`;

export const ts = (ms: number) =>
  new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

export const tsShort = (ms: number) =>
  new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

export const elapsed = (ms: number) => {
  const s = Math.floor((Date.now() - ms) / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
};
```

- [ ] Create `web/src/lib/formatters.test.ts`
```ts
import { describe, it, expect } from "vitest";
import { usd, pct, elapsed } from "./formatters";

describe("usd", () => {
  it("formats positive numbers", () => {
    expect(usd(1234.5)).toBe("$1,234.50");
  });
  it("returns dash for null", () => {
    expect(usd(null)).toBe("—");
  });
  it("returns dash for undefined", () => {
    expect(usd(undefined)).toBe("—");
  });
});

describe("pct", () => {
  it("converts 0.1 to 10.00%", () => {
    expect(pct(0.1)).toBe("10.00%");
  });
  it("returns dash for null", () => {
    expect(pct(null)).toBe("—");
  });
});

describe("elapsed", () => {
  it("returns seconds for <60s", () => {
    const result = elapsed(Date.now() - 30_000);
    expect(result).toBe("30s");
  });
  it("returns minutes for 2m", () => {
    const result = elapsed(Date.now() - 120_000);
    expect(result).toBe("2m");
  });
});
```

- [ ] Run tests: `cd /root/claude/projects/alien-trade/web && bun run test`
  Expected: 6 passing tests

- [ ] Commit
```bash
git add web/src/lib/formatters.ts web/src/lib/formatters.test.ts
git commit -m "feat(ui): formatters.ts extracted + tested"
```

---

### Task 3: Convex price_ticks backend

**Files:**
- Modify: `convex/schema.ts`
- Create: `convex/priceTicks.ts`

- [ ] Add `price_ticks` table to `convex/schema.ts` — append inside `defineSchema({...})` before the closing `})`
```ts
  price_ticks: defineTable({
    symbol: v.string(),
    price: v.float64(),
    timestamp_ms: v.float64(),
  })
    .index("by_symbol_ts", ["symbol", "timestamp_ms"]),
```

- [ ] Create `convex/priceTicks.ts`
```ts
import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const append = mutation({
  args: {
    symbol: v.string(),
    price: v.float64(),
    timestamp_ms: v.optional(v.float64()),
  },
  returns: v.id("price_ticks"),
  handler: async (ctx, args) => {
    return await ctx.db.insert("price_ticks", {
      symbol: args.symbol,
      price: args.price,
      timestamp_ms: args.timestamp_ms ?? Date.now(),
    });
  },
});

export const forSymbol = query({
  args: { symbol: v.string(), limit: v.optional(v.number()) },
  returns: v.array(v.object({
    _id: v.id("price_ticks"),
    _creationTime: v.number(),
    symbol: v.string(),
    price: v.float64(),
    timestamp_ms: v.float64(),
  })),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("price_ticks")
      .withIndex("by_symbol_ts", (q) => q.eq("symbol", args.symbol))
      .order("desc")
      .take(args.limit ?? 24);
  },
});
```

- [ ] Verify Convex picks up the changes: `cd /root/claude/projects/alien-trade && bunx convex dev --once` (or check the running dev server output for no errors)

- [ ] Commit
```bash
git add convex/schema.ts convex/priceTicks.ts
git commit -m "feat(convex): price_ticks table + forSymbol query for sparklines"
```

---

### Task 4: StatCard + RegimeBadge

**Files:**
- Create: `web/src/components/StatCard.tsx`
- Create: `web/src/components/RegimeBadge.tsx`

- [ ] Create `web/src/components/StatCard.tsx`
```tsx
import { motion } from "framer-motion";

type Tone = "positive" | "negative" | "neutral" | "warn";

const TONE_COLOR: Record<Tone, string> = {
  positive: "var(--green)",
  negative: "var(--red)",
  neutral:  "var(--text)",
  warn:     "var(--yellow)",
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
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <motion.div
        className="stat-value"
        style={{ color: TONE_COLOR[tone] }}
        key={animKey ?? value}
        initial={{ scale: 1.06 }}
        animate={{ scale: 1 }}
        transition={{ duration: 0.25 }}
      >
        {value}
      </motion.div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}
```

- [ ] Create `web/src/components/RegimeBadge.tsx`
```tsx
type Props = { regime?: string | null };

const CFG: Record<string, { color: string; bg: string; border: string; icon: string }> = {
  bull:    { color: "#00ff9d", bg: "#00ff9d18", border: "#00ff9d30", icon: "↑" },
  trend:   { color: "#00ff9d", bg: "#00ff9d18", border: "#00ff9d30", icon: "↑" },
  bear:    { color: "#ff3060", bg: "#ff306018", border: "#ff306030", icon: "↓" },
  crash:   { color: "#ff3060", bg: "#ff306030", border: "#ff306050", icon: "⚠" },
  chop:    { color: "#ffd60a", bg: "#ffd60a18", border: "#ffd60a30", icon: "↔" },
  high_vol:{ color: "#ffd60a", bg: "#ffd60a18", border: "#ffd60a30", icon: "⚡" },
};
const DEFAULT = { color: "#6080a0", bg: "#6080a018", border: "#6080a030", icon: "?" };

export function RegimeBadge({ regime }: Props) {
  const key = (regime ?? "").toLowerCase().replace(/ /g, "_");
  const c = CFG[key] ?? DEFAULT;
  return (
    <span
      className="regime-badge"
      style={{ color: c.color, background: c.bg, border: `1px solid ${c.border}` }}
    >
      {c.icon} {(regime ?? "UNKNOWN").toUpperCase()}
    </span>
  );
}
```

- [ ] Commit
```bash
git add web/src/components/StatCard.tsx web/src/components/RegimeBadge.tsx
git commit -m "feat(ui): StatCard + RegimeBadge components"
```

---

### Task 5: KillSwitch (hold-to-confirm)

**Files:**
- Create: `web/src/components/KillSwitch.tsx`

- [ ] Create `web/src/components/KillSwitch.tsx`
```tsx
import { useRef, useState } from "react";
import { motion } from "framer-motion";

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
      if (p >= 1) {
        stopHold();
        onToggle();
      }
    }, TICK_MS);
  };

  const stopHold = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setProgress(0);
  };

  const deg = progress * 360;
  const color = halted ? "var(--green)" : "var(--red)";
  const cls = hero ? "kill-switch-hero" : "kill-switch";

  return (
    <motion.button
      className={`${cls} ${halted ? "kill-switch--resume" : "kill-switch--halt"}`}
      style={{
        background: `conic-gradient(${color} ${deg}deg, var(--border) ${deg}deg)`,
      }}
      onMouseDown={startHold}
      onMouseUp={stopHold}
      onMouseLeave={stopHold}
      onTouchStart={(e) => { e.preventDefault(); startHold(); }}
      onTouchEnd={stopHold}
      animate={!halted && progress === 0
        ? { boxShadow: ["0 0 0px #ff306000", "0 0 12px #ff306040", "0 0 0px #ff306000"] }
        : {}}
      transition={{ duration: 2, repeat: Infinity }}
      title={halted ? "Hold to resume trading" : "Hold to halt trading"}
    >
      <span className="kill-switch__inner">
        {progress > 0
          ? `${Math.round(progress * 100)}%`
          : halted ? "RESUME" : "KILL"}
      </span>
    </motion.button>
  );
}
```

- [ ] Commit
```bash
git add web/src/components/KillSwitch.tsx
git commit -m "feat(ui): KillSwitch hold-to-confirm component"
```

---

### Task 6: Sparkline

**Files:**
- Create: `web/src/components/Sparkline.tsx`

- [ ] Create `web/src/components/Sparkline.tsx`
```tsx
import { Area, AreaChart, ResponsiveContainer } from "recharts";

export type PriceTick = { t: number; p: number };

type Props = {
  ticks: PriceTick[];
  positive: boolean;
  height?: number;
};

export function Sparkline({ ticks, positive, height = 56 }: Props) {
  if (ticks.length < 2) {
    return <div className="sparkline-empty" style={{ height }} />;
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
```

- [ ] Commit
```bash
git add web/src/components/Sparkline.tsx
git commit -m "feat(ui): Sparkline recharts micro-chart component"
```

---

### Task 7: PositionCard (hero component)

**Files:**
- Create: `web/src/components/PositionCard.tsx`

- [ ] Create `web/src/components/PositionCard.tsx`
```tsx
import { motion } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Sparkline } from "./Sparkline";
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

type Props = { position: Position };

export function PositionCard({ position }: Props) {
  const rawTicks = useQuery(api.priceTicks.forSymbol, {
    symbol: position.symbol,
    limit: 24,
  }) ?? [];
  // Ticks come newest-first from query; reverse for the chart (oldest→newest)
  const ticks = [...rawTicks].reverse().map((t) => ({ t: t.timestamp_ms, p: t.price }));

  const positive = position.unrealized_pnl_usd >= 0;
  const pnlPct = position.avg_entry_price > 0
    ? (position.current_price - position.avg_entry_price) / position.avg_entry_price
    : 0;
  const sign = positive ? "+" : "";

  return (
    <motion.div
      className={`position-card ${positive ? "position-card--win" : "position-card--loss"}`}
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
    >
      <div className="position-card__header">
        <span className="position-card__symbol">{position.symbol}</span>
        <span className="position-card__side">LONG</span>
      </div>

      <Sparkline ticks={ticks} positive={positive} />

      <div className="position-card__prices">
        <div className="price-col">
          <div className="price-label">Entry</div>
          <div className="price-value">{usd(position.avg_entry_price)}</div>
        </div>
        <div className="price-arrow">→</div>
        <div className="price-col" style={{ textAlign: "right" }}>
          <div className="price-label">Now</div>
          <motion.div
            className="price-value"
            key={position.current_price}
            animate={{ scale: [1.07, 1] }}
            transition={{ duration: 0.28 }}
          >
            {usd(position.current_price)}
          </motion.div>
        </div>
      </div>

      <div className="position-card__stats">
        <span className="position-card__size">{usd(position.current_value_usd)}</span>
        <motion.span
          className={`position-card__pnl ${positive ? "pnl--pos" : "pnl--neg"}`}
          key={position.unrealized_pnl_usd}
          animate={{ scale: [1.08, 1] }}
          transition={{ duration: 0.28 }}
        >
          {sign}{usd(position.unrealized_pnl_usd)} ({sign}{pct(pnlPct)})
        </motion.span>
      </div>

      <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 8 }}>
        Updated {elapsed(position.updated_ms)} ago
      </div>
    </motion.div>
  );
}
```

- [ ] Commit
```bash
git add web/src/components/PositionCard.tsx
git commit -m "feat(ui): PositionCard hero component with sparkline + live pnl"
```

---

### Task 8: AgentCard + EquityChart + AgentTicker

**Files:**
- Create: `web/src/components/AgentCard.tsx`
- Create: `web/src/components/EquityChart.tsx`
- Create: `web/src/components/AgentTicker.tsx`

- [ ] Create `web/src/components/AgentCard.tsx`
```tsx
import { motion } from "framer-motion";
import { ts } from "../lib/formatters";

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

type Props = {
  def: AgentDef;
  lastEvent?: { ts_ms: number; kind: string; headline: string };
  onClick: () => void;
};

export function AgentCard({ def, lastEvent, onClick }: Props) {
  const now = Date.now();
  const ageSec = lastEvent ? (now - lastEvent.ts_ms) / 1000 : Infinity;
  const isActive = ageSec < 60;
  const isRecent = ageSec < 300;
  const dotColor = isActive ? "var(--green)" : isRecent ? "var(--yellow)" : "var(--border-hi)";

  return (
    <div className="agent-card" onClick={onClick}>
      <div className="agent-card__header">
        <motion.div
          className="agent-card__avatar"
          style={{ color: def.color, background: def.bg, border: `1.5px solid ${def.color}40` }}
          animate={isActive
            ? { boxShadow: [`0 0 8px ${def.color}40`, `0 0 20px ${def.color}80`, `0 0 8px ${def.color}40`] }
            : { scale: [1, 1.03, 1] }}
          transition={{ duration: isActive ? 1.5 : 4, repeat: Infinity, ease: "easeInOut" }}
        >
          {def.label}
        </motion.div>
        <div>
          <div className="agent-card__name" style={{ color: def.color }}>{def.name}</div>
          <div className="agent-card__role">{def.role}</div>
        </div>
        <motion.div
          className="status-dot"
          style={{ background: dotColor, marginLeft: "auto", flexShrink: 0 }}
          animate={isActive ? { opacity: [1, 0.4, 1] } : {}}
          transition={{ duration: 1, repeat: Infinity }}
        />
      </div>
      {lastEvent ? (
        <>
          <div className="agent-card__last">{lastEvent.headline}</div>
          <div className="agent-card__meta">{ts(lastEvent.ts_ms)} · {lastEvent.kind}</div>
        </>
      ) : (
        <div className="agent-card__last" style={{ color: "var(--muted)", fontStyle: "italic" }}>
          No activity yet
        </div>
      )}
    </div>
  );
}
```

- [ ] Create `web/src/components/EquityChart.tsx`
```tsx
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import {
  Area, CartesianGrid, ComposedChart, Line,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { ts } from "../lib/formatters";

export function EquityChart() {
  const raw = useQuery(api.ledger.history, { limit: 100 }) ?? [];
  const data = [...raw].reverse().map((r) => ({
    t: r.timestamp_ms,
    pnl: Number(r.cumulative_pnl_usd.toFixed(2)),
    dd:  Number((r.current_drawdown_pct * 100).toFixed(2)),
  }));

  if (data.length === 0) {
    return (
      <div className="empty-state" style={{ padding: "32px 0" }}>
        <div className="empty-state__sub">No trade history yet — equity curve appears after first cycle.</div>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1a2737" vertical={false} />
        <XAxis dataKey="t" tickFormatter={(v) => ts(Number(v))}
          tick={{ fontSize: 10, fill: "var(--muted)" }} tickLine={false} axisLine={false} />
        <YAxis yAxisId="pnl" tick={{ fontSize: 10, fill: "var(--muted)" }}
          tickFormatter={(v) => `$${v}`} tickLine={false} axisLine={false} width={48} />
        <YAxis yAxisId="dd" orientation="right" tick={{ fontSize: 10, fill: "var(--muted)" }}
          tickFormatter={(v) => `${v}%`} tickLine={false} axisLine={false} width={36}
          domain={[0, "auto"]} reversed />
        <Tooltip
          contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
          labelFormatter={(l) => ts(Number(l))}
          formatter={(val, name) => {
            const n = Number(val);
            return name === "Equity" ? [`$${n.toFixed(2)}`, name] : [`${n.toFixed(2)}%`, name];
          }}
        />
        <Area yAxisId="dd" type="monotone" dataKey="dd" name="Drawdown"
          stroke="var(--red)" fill="#ff306018" strokeWidth={1} />
        <Line yAxisId="pnl" type="monotone" dataKey="pnl" name="Equity"
          stroke="var(--green)" strokeWidth={2} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
```

- [ ] Create `web/src/components/AgentTicker.tsx`
```tsx
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { AGENT_DEFS } from "./AgentCard";

export function AgentTicker() {
  const events = useQuery(api.agentEvents.recent, { limit: 20 }) ?? [];
  if (events.length === 0) return null;

  const items = events.map((e) => {
    const def = AGENT_DEFS.find((a) => a.name === e.agent);
    return { id: e._id, agent: e.agent, color: def?.color ?? "var(--muted)", headline: e.headline };
  });
  // Duplicate for seamless loop
  const doubled = [...items, ...items];

  return (
    <div className="agent-ticker">
      <div className="ticker-track">
        {doubled.map((item, i) => (
          <span key={`${item.id}-${i}`} className="ticker-item">
            <span className="ticker-item__agent" style={{ color: item.color }}>{item.agent}</span>
            <span className="ticker-item__kind">{item.headline}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
```

- [ ] Commit
```bash
git add web/src/components/AgentCard.tsx web/src/components/EquityChart.tsx web/src/components/AgentTicker.tsx
git commit -m "feat(ui): AgentCard, EquityChart, AgentTicker components"
```

---

### Task 9: CoPilotDrawer

**Files:**
- Create: `web/src/components/CoPilotDrawer.tsx`

- [ ] Create `web/src/components/CoPilotDrawer.tsx`
```tsx
import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useAction, useMutation, useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";

const CHIPS = [
  "What's the current regime?",
  "What was the last trade?",
  "What's my risk state?",
  "Why is the agent flat?",
];

type Props = {
  isOpen: boolean;
  onClose: () => void;
  prefill?: string;
};

export function CoPilotDrawer({ isOpen, onClose, prefill = "" }: Props) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const msgs = useQuery(api.copilot.messages, { limit: 40 }) ?? [];
  const addMessage = useMutation(api.copilot.addMessage);
  const ask = useAction(api.copilot.ask);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Accept prefill once
  const [lastPrefill, setLastPrefill] = useState("");
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
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className="copilot-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="copilot-drawer"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 320, damping: 32 }}
          >
            <div className="copilot-drawer__header">
              <span className="copilot-drawer__title">Co-Pilot</span>
              <button className="btn btn--ghost btn--sm" onClick={onClose}>✕ Close</button>
            </div>

            <div className="copilot-drawer__chips">
              {CHIPS.map((c) => (
                <button key={c} className="chip" onClick={() => send(c)}>{c}</button>
              ))}
            </div>

            <div className="copilot-drawer__messages">
              {msgs.length === 0 && (
                <div style={{ color: "var(--muted)", fontSize: 13, fontStyle: "italic", padding: "8px 0" }}>
                  Ask anything — regime, last trade, risk state…
                </div>
              )}
              <AnimatePresence initial={false}>
                {msgs.map((m) => (
                  <motion.div
                    key={m._id}
                    className={`chat-msg chat-msg--${m.role}`}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <div className="chat-msg__role">{m.role === "user" ? "You" : "CoPilot"}</div>
                    <div>{m.content}</div>
                  </motion.div>
                ))}
              </AnimatePresence>
              {loading && (
                <motion.div className="chat-msg chat-msg--assistant" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <div className="chat-msg__role">CoPilot</div>
                  <motion.span animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 1.2, repeat: Infinity }}>
                    thinking…
                  </motion.span>
                </motion.div>
              )}
              <div ref={bottomRef} />
            </div>

            <div className="copilot-drawer__input-row">
              <input
                className="num-input"
                style={{ flex: 1, width: "auto" }}
                placeholder="Ask the co-pilot…"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                disabled={loading}
              />
              <button className="btn btn--primary btn--sm" onClick={() => send()} disabled={loading || !question.trim()}>
                {loading ? "…" : "Ask"}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
```

- [ ] Commit
```bash
git add web/src/components/CoPilotDrawer.tsx
git commit -m "feat(ui): CoPilotDrawer slide-over panel with quick-ask chips"
```

---

### Task 10: AppShell + SideNav + LiveHeader

**Files:**
- Create: `web/src/components/SideNav.tsx`
- Create: `web/src/components/LiveHeader.tsx`
- Create: `web/src/components/AppShell.tsx`

- [ ] Create `web/src/components/SideNav.tsx`
```tsx
type View = "overview" | "positions" | "agents" | "controls" | "logs";

const NAV_ITEMS: { view: View; icon: string; label: string }[] = [
  { view: "overview",  icon: "◈",  label: "Overview" },
  { view: "positions", icon: "⬡",  label: "Positions" },
  { view: "agents",    icon: "🤖", label: "Agents" },
  { view: "controls",  icon: "⚙",  label: "Controls" },
  { view: "logs",      icon: "📋", label: "Logs" },
];

type Props = {
  active: View;
  onSelect: (v: View) => void;
  onCopilot: () => void;
};

export function SideNav({ active, onSelect, onCopilot }: Props) {
  return (
    <nav className="side-nav">
      {NAV_ITEMS.map((item) => (
        <button
          key={item.view}
          className={`nav-icon ${active === item.view ? "nav-icon--active" : ""}`}
          title={item.label}
          onClick={() => onSelect(item.view)}
        >
          {item.icon}
        </button>
      ))}
      <div className="nav-spacer" />
      <button className="nav-icon" title="Co-Pilot" onClick={onCopilot}
        style={{ color: "var(--purple)" }}>
        💬
      </button>
    </nav>
  );
}

export type { View };
```

- [ ] Create `web/src/components/LiveHeader.tsx`
```tsx
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { KillSwitch } from "./KillSwitch";
import { RegimeBadge } from "./RegimeBadge";
import { usd } from "../lib/formatters";

type Props = {
  halted: boolean;
  mode?: string;
  onKillToggle: () => void;
};

export function LiveHeader({ halted, mode, onKillToggle }: Props) {
  const ledger    = useQuery(api.ledger.latest);
  const decisions = useQuery(api.decisions.recent, { limit: 1 });

  const equity = ledger?.equity_usd ?? ledger?.cumulative_pnl_usd;
  const pnl    = ledger?.cumulative_pnl_usd;
  const regime = decisions?.[0]?.regime ?? null;
  const pnlPos = (pnl ?? 0) >= 0;

  return (
    <header className="live-header">
      <span className="header-logo">ALIEN-TRADE</span>

      <div className="header-sep" />

      {regime && <RegimeBadge regime={regime} />}

      {mode && (
        <span className={`mode-badge mode-badge--${mode}`}>
          {mode === "mainnet" ? "LIVE" : mode.toUpperCase()}
        </span>
      )}

      <div className="header-sep" />

      {equity != null && (
        <span className="header-equity" style={{ color: pnlPos ? "var(--green)" : "var(--red)" }}>
          {usd(equity)}
        </span>
      )}
      {pnl != null && (
        <span className="header-pnl" style={{ color: pnlPos ? "var(--green)" : "var(--red)" }}>
          {pnlPos ? "+" : ""}{usd(pnl)}
        </span>
      )}

      <div className="header-spacer" />

      {halted && (
        <span style={{ fontSize: 12, fontWeight: 700, color: "var(--red)",
          background: "#ff306018", padding: "3px 10px", borderRadius: 6 }}>
          HALTED
        </span>
      )}

      <KillSwitch halted={halted} onToggle={onKillToggle} />
    </header>
  );
}
```

- [ ] Create `web/src/components/AppShell.tsx`
```tsx
import { ReactNode } from "react";
import { SideNav, View } from "./SideNav";
import { LiveHeader } from "./LiveHeader";
import { AgentTicker } from "./AgentTicker";

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
    <div className="app-shell">
      <LiveHeader halted={halted} mode={mode} onKillToggle={onKillToggle} />
      <div className="app-body">
        <SideNav active={activeView} onSelect={onViewChange} onCopilot={onCopilot} />
        <main className="app-main">{children}</main>
      </div>
      <AgentTicker />
    </div>
  );
}
```

- [ ] Commit
```bash
git add web/src/components/SideNav.tsx web/src/components/LiveHeader.tsx web/src/components/AppShell.tsx
git commit -m "feat(ui): AppShell + SideNav + LiveHeader layout components"
```

---

### Task 11: OverviewView + PositionsView

**Files:**
- Create: `web/src/views/OverviewView.tsx`
- Create: `web/src/views/PositionsView.tsx`

- [ ] Create `web/src/views/OverviewView.tsx`
```tsx
import { AnimatePresence, motion } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { StatCard } from "../components/StatCard";
import { EquityChart } from "../components/EquityChart";
import { AgentCard, AGENT_DEFS } from "../components/AgentCard";
import { PositionCard } from "../components/PositionCard";
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
    <div>
      <AnimatePresence>
        {floorHalt && (
          <motion.div className="alert-banner alert-banner--halt"
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
            Trading HALTED — equity floor hit. Fund wallet or raise floor, then Resume.
          </motion.div>
        )}
        {floorWarn && (
          <motion.div className="alert-banner alert-banner--warn"
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
            Portfolio approaching equity floor. Consider adding capital.
          </motion.div>
        )}
      </AnimatePresence>

      {/* Stats row */}
      <div className="overview-stats">
        <StatCard label="Cumulative PnL"  value={usd(pnl)}  tone={(pnl ?? 0) >= 0 ? "positive" : "negative"} animKey={pnl} />
        <StatCard label="Max Drawdown"    value={pct(dd)}   tone={(dd ?? 0) > 0.05 ? "negative" : (dd ?? 0) > 0 ? "warn" : "positive"} />
        <StatCard label="Open Exposure"   value={usd(risk?.open_exposure_usd)} />
        <StatCard label="Circuit Breaker" value={risk?.circuit_breaker_active ? "TRIPPED" : "OK"}
          tone={risk?.circuit_breaker_active ? "negative" : "positive"} />
      </div>

      {/* Equity chart */}
      <div className="panel">
        <div className="panel-title">Equity &amp; Drawdown</div>
        <EquityChart />
      </div>

      {/* Open positions mini grid (max 3) */}
      {positions.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div className="panel-title" style={{ marginBottom: 10 }}>Open Positions</div>
          <div className="positions-grid">
            {positions.slice(0, 3).map((p) => <PositionCard key={p._id} position={p} />)}
          </div>
        </div>
      )}

      {/* Agent strip */}
      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="panel-title">Agent Team</div>
        <div className="agents-grid">
          {AGENT_DEFS.map((def) => (
            <AgentCard
              key={def.name}
              def={def}
              lastEvent={rosterMap.get(def.name)}
              onClick={() => onAgentClick(def.name)}
            />
          ))}
        </div>
      </div>

      {/* Recent decisions */}
      {(decisions ?? []).length > 0 && (
        <div className="panel">
          <div className="panel-title">Recent Decisions</div>
          <table>
            <thead>
              <tr><th>Time</th><th>Symbol</th><th>Regime</th><th>Verdict</th><th>Size</th></tr>
            </thead>
            <tbody>
              {(decisions ?? []).map((d) => (
                <tr key={d._id}>
                  <td style={{ color: "var(--muted)" }}>{ts(d.timestamp_ms)}</td>
                  <td style={{ color: "var(--cyan)", fontWeight: 700 }}>{d.symbol}</td>
                  <td style={{ color: "var(--text)" }}>{d.regime}</td>
                  <td><span className={`tag tag-${d.risk_verdict}`}>{d.risk_verdict}</span></td>
                  <td>{usd(d.final_size_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

- [ ] Create `web/src/views/PositionsView.tsx`
```tsx
import { AnimatePresence } from "framer-motion";
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { PositionCard } from "../components/PositionCard";

export function PositionsView() {
  const positions = useQuery(api.positions.open) ?? [];

  if (positions.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state__icon">👽</div>
        <div className="empty-state__title">Watching the market</div>
        <div className="empty-state__sub">
          No open positions — the agent is flat and waiting for a high-conviction setup.
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 20, fontWeight: 700 }}>
          Positions
        </span>
        <span style={{ fontSize: 13, color: "var(--muted)" }}>
          {positions.length} open
        </span>
      </div>
      <div className="positions-grid">
        <AnimatePresence>
          {positions.map((p) => <PositionCard key={p._id} position={p} />)}
        </AnimatePresence>
      </div>
    </div>
  );
}
```

- [ ] Commit
```bash
git add web/src/views/OverviewView.tsx web/src/views/PositionsView.tsx
git commit -m "feat(ui): OverviewView + PositionsView (trade card grid)"
```

---

### Task 12: AgentsView + ControlsView + LogsView

**Files:**
- Create: `web/src/views/AgentsView.tsx`
- Create: `web/src/views/ControlsView.tsx`
- Create: `web/src/views/LogsView.tsx`

- [ ] Create `web/src/views/AgentsView.tsx`
```tsx
import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { AgentCard, AGENT_DEFS } from "../components/AgentCard";

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
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 20, fontWeight: 700, marginBottom: 6 }}>
          Agent Team
        </div>
        <div style={{ fontSize: 13, color: "var(--muted)" }}>
          Click an agent to ask the co-pilot about them.
        </div>
      </div>
      <div className="agents-grid">
        {AGENT_DEFS.map((def) => (
          <AgentCard
            key={def.name}
            def={def}
            lastEvent={rosterMap.get(def.name)}
            onClick={() => onAgentClick(def.name)}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] Create `web/src/views/ControlsView.tsx`
```tsx
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useQuery, useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { KillSwitch } from "../components/KillSwitch";
import { withToken } from "../lib/control";
import { usd, pct } from "../lib/formatters";

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

  const halted  = config?.halted ?? false;
  const paused  = control?.agents_paused ?? false;
  const mode    = config?.trading_mode;
  const floor   = config?.equity_floor ?? 0;
  const active  = config?.strategy_name ?? "balanced";
  const ap      = config?.autopilot;

  const onKillSwitch = () => {
    setHalted({ halted: !halted });
    setControl({ trading_halted: !halted, updated_by: "user" });
  };
  const onSetFloor = () => {
    const v = parseFloat(floorInput);
    if (!isNaN(v) && v >= 0) { updateLimits({ equity_floor: v }); setFloorInput(""); }
  };

  return (
    <div style={{ maxWidth: 680, margin: "0 auto" }}>
      <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 20, fontWeight: 700, marginBottom: 24 }}>
        Controls
      </div>

      {/* Kill switch */}
      <div className="panel" style={{ textAlign: "center" }}>
        <div className="panel-title">Emergency Stop</div>
        <KillSwitch halted={halted} onToggle={onKillSwitch} hero />
        <div style={{ marginTop: 12, fontSize: 13, color: "var(--muted)" }}>
          {halted ? "Agent is HALTED. Hold to resume trading." : "Hold for 1.5s to halt all trading."}
        </div>
        <div style={{ marginTop: 12, display: "flex", gap: 8, justifyContent: "center" }}>
          <button className="btn btn--ghost btn--sm" onClick={() => {
            if (!paused && !window.confirm("Pause advisory agents? Trading continues.")) return;
            setControl({ agents_paused: !paused, updated_by: "user" });
          }}>
            {paused ? "Resume Agents" : "Pause Agents"}
          </button>
          <button className="btn btn--danger btn--sm" onClick={() => {
            if (!window.confirm("Cancel the current in-flight agent action?")) return;
            setControl({ stop_response_id: String(Date.now()), updated_by: "user" });
          }}>
            Stop Response
          </button>
        </div>
      </div>

      {/* Trading mode */}
      <div className="panel">
        <div className="panel-title">Trading Mode</div>
        <div className="seg">
          {(["testnet", "paper", "mainnet"] as const).map((m) => (
            <button
              key={m}
              className={`seg-btn ${mode === m ? `seg-btn--active seg-btn--${m}` : ""}`}
              onClick={() => {
                if (m === mode) return;
                if (m === "mainnet" && !window.confirm("Switch to LIVE mainnet? This trades real funds.")) return;
                setTradingMode({ trading_mode: m });
              }}
              disabled={config === undefined}
            >
              {m === "mainnet" ? "LIVE" : m}
            </button>
          ))}
        </div>
      </div>

      {/* Strategy */}
      <div className="panel">
        <div className="panel-title">Strategy</div>
        <div className="strategy-grid">
          {STRATEGIES.map((s) => (
            <button
              key={s.name}
              className={`strategy-card ${active === s.name ? "strategy-card--active" : ""}`}
              onClick={() => setStrategy({ strategy_name: s.name })}
            >
              <div className="strategy-card__name">{s.label}</div>
              <div className="strategy-card__blurb">{s.blurb}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Equity floor */}
      <div className="panel">
        <div className="panel-title">Equity Floor</div>
        <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 10 }}>
          {floor > 0 ? <strong style={{ color: "var(--text)" }}>Floor: {usd(floor)}</strong> : "Disabled — agent trades until manually halted."}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input className="num-input" type="number" min="0" placeholder="e.g. 50"
            value={floorInput} onChange={(e) => setFloorInput(e.target.value)} />
          <button className="btn btn--primary btn--sm" onClick={onSetFloor} disabled={!floorInput}>Set</button>
          {floor > 0 && (
            <button className="btn btn--ghost btn--sm" onClick={() => updateLimits({ equity_floor: 0 })}>Remove</button>
          )}
        </div>
      </div>

      {/* Autopilot */}
      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div className="panel-title" style={{ margin: 0 }}>Autopilot</div>
          <button
            className={`btn btn--sm ${ap?.enabled ? "btn--primary" : "btn--ghost"}`}
            onClick={() => setAutopilot({ autopilot: { ...(ap ?? {}), enabled: !(ap?.enabled ?? false) } as any })}
          >
            {ap?.enabled ? "ON" : "OFF"}
          </button>
        </div>
        {ap?.enabled && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {[
              { label: "Take profit %", key: "profit_target_pct", factor: 100 },
              { label: "Trailing give-back %", key: "trailing_giveback_pct", factor: 100 },
              { label: "Daily target %", key: "daily_profit_target_pct", factor: 100 },
            ].map(({ label, key }) => (
              <div key={key} className="ap-row">
                <span>{label}</span>
                <input
                  className="num-input"
                  type="number" min="0" style={{ width: 80 }}
                  placeholder="—"
                  defaultValue={(ap as any)[key] != null ? ((ap as any)[key] * 100).toFixed(1) : ""}
                  onBlur={(e) => {
                    const v = parseFloat(e.target.value);
                    setAutopilot({ autopilot: { ...ap, [key]: isNaN(v) ? undefined : v / 100 } as any });
                  }}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Risk caps */}
      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: showSliders ? 14 : 0 }}>
          <div className="panel-title" style={{ margin: 0 }}>Risk Caps</div>
          <button className="btn btn--ghost btn--sm" onClick={() => setShowSliders(!showSliders)}>
            {showSliders ? "Hide" : "Edit"}
          </button>
        </div>
        <AnimatePresence>
          {showSliders && config && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} style={{ overflow: "hidden" }}>
              {[
                { label: "Max position", key: "max_position_usd", min: 100, max: 10000, step: 100, fmt: usd },
                { label: "Daily loss limit", key: "daily_loss_limit_usd", min: 50, max: 2000, step: 50, fmt: usd },
              ].map(({ label, key, min, max, step, fmt }) => (
                <div key={key} style={{ marginBottom: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                    <span style={{ color: "var(--muted)" }}>{label}</span>
                    <span style={{ fontWeight: 600 }}>{fmt((config as any)[key])}</span>
                  </div>
                  <input type="range" min={min} max={max} step={step}
                    defaultValue={(config as any)[key]}
                    style={{ width: "100%", accentColor: "var(--cyan)", cursor: "pointer" }}
                    onMouseUp={(e) => updateLimits({ [key]: Number((e.target as HTMLInputElement).value) })}
                    onTouchEnd={(e) => updateLimits({ [key]: Number((e.target as HTMLInputElement).value) })}
                  />
                </div>
              ))}
              <div style={{ marginBottom: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                  <span style={{ color: "var(--muted)" }}>Max drawdown</span>
                  <span style={{ fontWeight: 600 }}>{pct(config.max_drawdown_pct)}</span>
                </div>
                <input type="range" min={1} max={50} step={1}
                  defaultValue={Math.round(config.max_drawdown_pct * 100)}
                  style={{ width: "100%", accentColor: "var(--red)", cursor: "pointer" }}
                  onMouseUp={(e) => updateLimits({ max_drawdown_pct: Number((e.target as HTMLInputElement).value) / 100 })}
                  onTouchEnd={(e) => updateLimits({ max_drawdown_pct: Number((e.target as HTMLInputElement).value) / 100 })}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        {!showSliders && config && (
          <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 8 }}>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>Max position: <strong style={{ color: "var(--text)" }}>{usd(config.max_position_usd)}</strong></div>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>Daily loss limit: <strong style={{ color: "var(--text)" }}>{usd(config.daily_loss_limit_usd)}</strong></div>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>Max drawdown: <strong style={{ color: "var(--text)" }}>{pct(config.max_drawdown_pct)}</strong></div>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] Create `web/src/views/LogsView.tsx`
```tsx
import { useQuery, useMutation } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { motion } from "framer-motion";
import { ts } from "../lib/formatters";
import { usd } from "../lib/formatters";
import { AGENT_DEFS } from "../components/AgentCard";

const KIND_COLOR: Record<string, string> = {
  observation: "tag-observe", analysis: "tag-analysis", verdict: "tag-verdict",
  action: "tag-action", handoff: "tag-handoff", control: "tag-control",
};

export function LogsView() {
  const decisions = useQuery(api.decisions.recent, { limit: 20 });
  const auditLog  = useQuery(api.audit.recent, { limit: 60 });
  const events    = useQuery(api.agentEvents.recent, { limit: 40 });
  const wins      = useQuery(api.reflections.wins, { limit: 5 });
  const recordFeedback = useMutation(api.feedback.record);

  return (
    <div>
      <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 20, fontWeight: 700, marginBottom: 20 }}>
        Logs
      </div>

      {/* Decisions */}
      <div className="panel">
        <div className="panel-title">Decision History</div>
        <table>
          <thead>
            <tr><th>Time</th><th>Symbol</th><th>Regime</th><th>Verdict</th><th>Size</th><th>Rate</th></tr>
          </thead>
          <tbody>
            {(decisions ?? []).map((d) => (
              <tr key={d._id}>
                <td style={{ color: "var(--muted)" }}>{ts(d.timestamp_ms)}</td>
                <td style={{ color: "var(--cyan)", fontWeight: 700 }}>{d.symbol}</td>
                <td style={{ color: "var(--text)" }}>{d.regime}</td>
                <td><span className={`tag tag-${d.risk_verdict}`}>{d.risk_verdict}</span></td>
                <td>{usd(d.final_size_usd)}</td>
                <td>
                  {d.setup_key ? (
                    <span style={{ display: "inline-flex", gap: 4 }}>
                      <button className="btn-rate" title="Good setup"
                        onClick={() => recordFeedback({ cycle_id: d.cycle_id, setup_key: d.setup_key!, symbol: d.symbol, label: "good" })}>👍</button>
                      <button className="btn-rate" title="Bad setup"
                        onClick={() => recordFeedback({ cycle_id: d.cycle_id, setup_key: d.setup_key!, symbol: d.symbol, label: "bad" })}>👎</button>
                    </span>
                  ) : <span style={{ color: "var(--muted)" }}>—</span>}
                </td>
              </tr>
            ))}
            {decisions?.length === 0 && (
              <tr><td colSpan={6} style={{ color: "var(--muted)" }}>No decisions yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Wins */}
      {(wins ?? []).length > 0 && (
        <div className="panel">
          <div className="panel-title">Winning Trades</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {(wins ?? []).map((w) => (
              <motion.div key={w._id} className="win-card" initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <span className="tag tag-allow">WIN</span>
                  <span style={{ color: "var(--green)", fontWeight: 700 }}>+{usd(w.outcome_pnl_usd)}</span>
                </div>
                <div style={{ fontSize: 12, color: "var(--muted)" }}>{w.regime} · {ts(w.timestamp_ms)}</div>
                {w.lesson && <div style={{ fontSize: 12, color: "var(--muted)", fontStyle: "italic", marginTop: 4 }}>"{w.lesson}"</div>}
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Agent activity */}
      <div className="panel">
        <div className="panel-title">Agent Activity Channel</div>
        {(events ?? []).length === 0 ? (
          <div style={{ color: "var(--muted)", fontSize: 13 }}>No activity yet.</div>
        ) : (
          <div className="channel">
            {(events ?? []).map((e) => {
              const def = AGENT_DEFS.find((a) => a.name === e.agent);
              return (
                <div key={e._id} className="evt">
                  <div className="evt-meta">
                    <span className="evt-agent" style={{ color: def?.color ?? "var(--cyan)" }}>{e.agent}</span>
                    <span className={`tag ${KIND_COLOR[e.kind] ?? "tag-observe"}`}>{e.kind}</span>
                    <span className="evt-time">{ts(e.ts_ms)}</span>
                    {e.cycle_id && <span className="evt-cycle">{String(e.cycle_id).slice(-8)}</span>}
                  </div>
                  <div className="evt-headline">{e.headline}</div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Log console */}
      <div className="panel">
        <div className="panel-title">Live Log Console</div>
        {(auditLog ?? []).length === 0 ? (
          <div style={{ color: "var(--muted)", fontSize: 13 }}>No log entries yet.</div>
        ) : (
          <div className="logconsole">
            {(auditLog ?? []).map((a) => (
              <div key={a._id} className={`logline log-${a.severity}`}>
                <span className="log-time">{ts(a.timestamp_ms)}</span>
                <span className="log-type">{a.event_type}</span>
                {a.cycle_id && <span className="log-cycle">{String(a.cycle_id).slice(-8)}</span>}
                <span className="log-payload">{a.payload}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] Commit
```bash
git add web/src/views/AgentsView.tsx web/src/views/ControlsView.tsx web/src/views/LogsView.tsx
git commit -m "feat(ui): AgentsView, ControlsView, LogsView"
```

---

### Task 13: App.tsx rewrite + ThesisLedger CSS patch

**Files:**
- Rewrite: `web/src/App.tsx`
- Modify: `web/src/components/ThesisLedger.tsx`

- [ ] Rewrite `web/src/App.tsx`
```tsx
import { useState } from "react";
import { useMutation, useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import { loadToken, setToken, withToken } from "./lib/control";
import { AppShell } from "./components/AppShell";
import { CoPilotDrawer } from "./components/CoPilotDrawer";
import { OverviewView } from "./views/OverviewView";
import { PositionsView } from "./views/PositionsView";
import { AgentsView } from "./views/AgentsView";
import { ControlsView } from "./views/ControlsView";
import { LogsView } from "./views/LogsView";
import { View } from "./components/SideNav";

function PairingScreen({ onPaired }: { onPaired: (t: string) => void }) {
  const [val, setVal] = useState("");
  const submit = () => { const t = val.trim(); if (t) onPaired(t); };
  return (
    <div className="pairing-screen">
      <div className="pairing-card">
        <div className="pairing-title">ALIEN-TRADE</div>
        <div className="pairing-sub">
          Pair this cockpit to control the agent. Scan the onboarding QR or paste your control token below.
        </div>
        <input
          type="password"
          value={val}
          placeholder="control token"
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
          className="num-input"
          style={{ width: "100%", marginBottom: 12 }}
        />
        <button className="btn btn--primary" onClick={submit} disabled={!val.trim()} style={{ width: "100%" }}>
          Pair cockpit
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const config  = useQuery(api.config.get);
  const control = useQuery(api.agentControl.get);

  const _setHalted  = useMutation(api.config.setHalted);
  const _setControl = useMutation(api.agentControl.set);
  const setHalted   = (a: Parameters<typeof _setHalted>[0])  => _setHalted(withToken(a));
  const setControl  = (a: Parameters<typeof _setControl>[0]) => _setControl(withToken(a));

  const [token, setTokenState] = useState<string | null>(loadToken());
  const [view, setView]       = useState<View>("overview");
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [copilotPrefill, setCopilotPrefill] = useState("");

  const halted = config?.halted ?? false;
  const mode   = config?.trading_mode;

  const onKillToggle = () => {
    setHalted({ halted: !halted });
    setControl({ trading_halted: !halted, updated_by: "user" });
  };

  const onAgentClick = (name: string) => {
    setCopilotPrefill(`What is ${name} currently doing?`);
    setCopilotOpen(true);
  };

  if (!token) {
    return <PairingScreen onPaired={(t) => { setToken(t); setTokenState(t); }} />;
  }

  const renderView = () => {
    switch (view) {
      case "overview":  return <OverviewView  onAgentClick={onAgentClick} />;
      case "positions": return <PositionsView />;
      case "agents":    return <AgentsView    onAgentClick={onAgentClick} />;
      case "controls":  return <ControlsView />;
      case "logs":      return <LogsView />;
    }
  };

  return (
    <>
      <AppShell
        activeView={view}
        onViewChange={setView}
        onCopilot={() => setCopilotOpen(true)}
        halted={halted}
        mode={mode}
        onKillToggle={onKillToggle}
      >
        {renderView()}
      </AppShell>
      <CoPilotDrawer
        isOpen={copilotOpen}
        onClose={() => { setCopilotOpen(false); setCopilotPrefill(""); }}
        prefill={copilotPrefill}
      />
    </>
  );
}
```

- [ ] Update `web/src/components/ThesisLedger.tsx` — replace hardcoded `className="panel"` color strings with CSS vars. The existing logic is unchanged; only fix inline style references that used old hex values:
  - Replace `background: "#0b0f17"` → `background: "var(--bg)"`
  - Replace `border: "1px solid #1e2937"` → `border: "1px solid var(--border)"`
  - Replace `color: "#8b98a5"` → `color: "var(--muted)"`
  - Replace `color: "#e6edf3"` → `color: "var(--text)"`
  (Read the file first, then apply targeted edits. Do NOT rewrite logic.)

- [ ] Build check: `cd /root/claude/projects/alien-trade/web && bun run typecheck`
  Expected: zero errors (fix any that appear)

- [ ] Start dev server and visually verify: `bun run dev`
  Check in browser: http://localhost:5173
  - Pairing screen shows with new design
  - After pairing: header with logo, regime badge, equity
  - Sidebar with 5 icons + co-pilot
  - Overview shows stat cards, equity chart, agent strip
  - Positions view shows trade grid or alien empty state
  - Controls view shows large kill switch
  - Co-pilot drawer slides in from right

- [ ] Final commit
```bash
git add web/src/App.tsx web/src/components/ThesisLedger.tsx
git commit -m "feat(ui): full cockpit redesign — sidebar nav, trade card grid, neon design system"
```

---

### Task 14: Production build + deploy

- [ ] Build: `cd /root/claude/projects/alien-trade/web && bun run build`
  Expected: dist/ generated with no errors

- [ ] Restart cockpit service: `systemctl restart alien-cockpit`

- [ ] Verify: open http://76.13.243.12:4173/ and confirm new UI is live

- [ ] Commit build confirmation
```bash
git add -A
git commit -m "chore(ui): production build verified on VPS cockpit"
```
