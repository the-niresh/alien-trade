import { driver, type DriveStep } from "driver.js";
import "driver.js/dist/driver.css";

const TOUR_KEY = "alien-trade:tour-seen-v1";

export function hasTourBeenSeen(): boolean {
  return localStorage.getItem(TOUR_KEY) === "1";
}

export function markTourSeen(): void {
  localStorage.setItem(TOUR_KEY, "1");
}

function makeTour(steps: DriveStep[], onDone?: () => void) {
  const obj = driver({
    showProgress: true,
    progressText: "{{current}} / {{total}}",
    animate: true,
    overlayOpacity: 0.65,
    popoverClass: "alien-tour-popover",
    onDestroyed: onDone,
    steps,
  });
  obj.drive();
}

// ── Per-tab tours ─────────────────────────────────────────────────────────────

const TAB_TOURS: Record<string, DriveStep[]> = {
  overview: [
    {
      element: '[data-tour="nav-overview"]',
      popover: {
        title: "Overview",
        description: "Live equity curve, cumulative PnL, max drawdown, and signal scores — everything you need to judge the agent's health at a glance.",
        side: "right",
      },
    },
    {
      element: '[data-tour="kill-switch"]',
      popover: {
        title: "Kill Switch",
        description: "Halts ALL trading instantly. Red = halted, pulsing green = live. One click — no confirmation dialog.",
        side: "bottom",
        align: "end",
      },
    },
  ],
  chart: [
    {
      element: '[data-tour="nav-chart"]',
      popover: {
        title: "Markets",
        description: "OHLCV candles for each eligible token (ETH / CAKE / UNI / LINK / AAVE). Your agent's buys (▲) and sells (▼) are marked on the chart.",
        side: "right",
      },
    },
    {
      element: '[data-tour="deposit-btn"]',
      popover: {
        title: "Fund Your Wallet",
        description: "Deposit USDT to increase position size, or convert tokens. All custody stays in your TWAK self-custody wallet.",
        side: "bottom",
      },
    },
  ],
  portfolio: [
    {
      element: '[data-tour="nav-portfolio"]',
      popover: {
        title: "Portfolio",
        description: "Your TWAK self-custody wallet holdings in real time: USDT, ETH, BNB, and total equity. Scroll down for per-trade realized PnL.",
        side: "right",
      },
    },
    {
      element: '[data-tour="nav-trackers"]',
      popover: {
        title: "Track Open Positions",
        description: "Switch to Trackers to see live unrealized PnL and the agent's queued commands.",
        side: "right",
      },
    },
  ],
  trackers: [
    {
      element: '[data-tour="nav-trackers"]',
      popover: {
        title: "Trackers",
        description: "Activity tab: open positions, next regime decision, and command queue. KOL Feed tab: the 100 top crypto influencers powering the S3 sentiment signal.",
        side: "right",
      },
    },
  ],
  controls: [
    {
      element: '[data-tour="nav-controls"]',
      popover: {
        title: "Risk Controls",
        description: "Set max position size, daily loss limit, equity floor, and drawdown cap. Changes take effect on the next trade cycle.",
        side: "right",
      },
    },
    {
      element: '[data-tour="kill-switch"]',
      popover: {
        title: "Emergency Stop",
        description: "If something looks wrong, hit the kill switch first — then adjust controls. Safe-first, always.",
        side: "bottom",
        align: "end",
      },
    },
  ],
  intelligence: [
    {
      element: '[data-tour="nav-intelligence"]',
      popover: {
        title: "Intelligence Layer",
        description: "See how CMC data, Trust Wallet Agent Kit, and BNB AI Agent SDK power the agent — plus the Hermes reflection loop and Second Brain memory.",
        side: "right",
      },
    },
  ],
  deposit: [
    {
      element: '[data-tour="deposit-btn"]',
      popover: {
        title: "Deposit & Convert",
        description: "Scan the QR to send USDT to your self-custody wallet, or use Convert to swap tokens inside the cockpit.",
        side: "bottom",
      },
    },
  ],
  pipeline: [
    {
      element: '[data-tour="nav-pipeline"]',
      popover: {
        title: "Decision Pipeline",
        description: "The agent's full decision flow, stage by stage: data ingest → signals → regime → risk gate → execution. Each stage lights up as the cycle runs.",
        side: "right",
      },
    },
    {
      element: '[data-tour="nav-intelligence"]',
      popover: {
        title: "What feeds it",
        description: "Intelligence shows the sponsor data sources — CMC OHLCV, funding/OI, and social — powering the signals at the top of this pipeline.",
        side: "right",
      },
    },
  ],
  positions: [
    {
      element: '[data-tour="nav-positions"]',
      popover: {
        title: "Positions",
        description: "Every open and closed position — size, entry price, and live unrealized PnL. Your per-trade ground truth.",
        side: "right",
      },
    },
    {
      element: '[data-tour="nav-portfolio"]',
      popover: {
        title: "Rolled up in Portfolio",
        description: "Portfolio aggregates these positions into your total TWAK self-custody wallet equity.",
        side: "right",
      },
    },
  ],
  agents: [
    {
      element: '[data-tour="nav-agents"]',
      popover: {
        title: "Your Agent Team",
        description: "Each agent composes the specialized, sponsor-powered Agent Tools — CMC research, TWAK signing, and Hermes memory — to pursue a goal you set.",
        side: "right",
      },
    },
    {
      element: '[data-tour="nav-copilot"]',
      popover: {
        title: "Spawn one here",
        description: 'Tell the Co-Pilot "make an agent that watches CAKE and alerts me when funding flips negative" — it spawns a new agent for you.',
        side: "right",
      },
    },
  ],
  logs: [
    {
      element: '[data-tour="nav-logs"]',
      popover: {
        title: "Decision & Audit Logs",
        description: "The raw decision/audit JSON stream, one entry per cycle — exactly what the agent did and why. Nothing hidden.",
        side: "right",
      },
    },
    {
      element: '[data-tour="kill-switch"]',
      popover: {
        title: "Something off?",
        description: "If a log entry looks wrong, hit the kill switch first — it halts all trading instantly — then investigate.",
        side: "bottom",
        align: "end",
      },
    },
  ],
  notifications: [
    {
      element: '[data-tour="nav-notifications"]',
      popover: {
        title: "Alerts",
        description: "Every non-routine event lands here: trades, halts, stalled agents, and agent updates. A red dot on this tab means unread alerts.",
        side: "right",
      },
    },
    {
      element: '[data-tour="nav-copilot"]',
      popover: {
        title: "Explain any alert",
        description: 'Ask the Co-Pilot "why did I get that halt alert?" and it explains the event in plain language.',
        side: "right",
      },
    },
  ],
  docs: [
    {
      element: '[data-tour="nav-docs"]',
      popover: {
        title: "Docs",
        description: "The strategy, architecture, and sponsor-integration writeups behind the cockpit — the thinking under the hood.",
        side: "right",
      },
    },
    {
      element: '[data-tour="nav-overview"]',
      popover: {
        title: "Back to live",
        description: "Head back to Overview any time for the live snapshot of the agent's health.",
        side: "right",
      },
    },
  ],
};

// ── Main tour entry point ─────────────────────────────────────────────────────

export function startTour(view?: string): void {
  if (view && TAB_TOURS[view]) {
    makeTour(TAB_TOURS[view]);
    return;
  }

  makeTour(
    [
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
          description: "Halts all trading instantly. Hold again to resume. Red = halted, pulsing green = live.",
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
          title: "Markets",
          description: "Price chart for each eligible token with your entry and exit markers.",
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
          description: "The agent is watching the market 24/7. Click this button any time to start a tour for whichever view you're on.",
          side: "right",
        },
      },
    ],
    markTourSeen,
  );
}

// ── Post-trade tour (fires once when 0→1 trades) ─────────────────────────────

const POST_TOUR_KEY = "alien-trade:posttrade-tour-seen-v1";

export function hasPostTradeTourBeenSeen(): boolean {
  return localStorage.getItem(POST_TOUR_KEY) === "1";
}

export function startPostTradeTour(): void {
  makeTour(
    [
      {
        element: '[data-tour="nav-trackers"]',
        popover: {
          title: "First trade logged",
          description: "Your agent made its first trade. Trackers shows all ongoing positions and queued commands.",
          side: "right",
        },
      },
      {
        element: '[data-tour="nav-portfolio"]',
        popover: {
          title: "Check your portfolio",
          description: "Portfolio shows your TWAK wallet balance — USDT, ETH, BNB, and total value after the trade.",
          side: "right",
        },
      },
      {
        element: '[data-tour="nav-chart"]',
        popover: {
          title: "See the entry on the chart",
          description: "The chart marks your buy with a green ▲ and sell with a red ▼.",
          side: "right",
        },
      },
      {
        element: '[data-tour="nav-copilot"]',
        popover: {
          title: "Withdraw or take profit",
          description: 'Ask the Co-Pilot: "withdraw 2 USDT to 0x…" or "take profit at 5%" to set up autopilot.',
          side: "right",
        },
      },
    ],
    () => localStorage.setItem(POST_TOUR_KEY, "1"),
  );
}
