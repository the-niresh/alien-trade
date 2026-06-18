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
        element: '[data-tour="brand"]',
        popover: {
          title: "Kill Switch",
          description: "The kill switch (top-right on desktop) halts all trading instantly. Hold again to resume. Red = halted, Green = live.",
          side: "bottom",
          align: "start",
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

// ── Post-trade tour (fires once when 0→1 trades) ─────────────────────────────

const POST_TOUR_KEY = "alien-trade:posttrade-tour-seen-v1";

export function hasPostTradeTourBeenSeen(): boolean {
  return localStorage.getItem(POST_TOUR_KEY) === "1";
}

export function startPostTradeTour(): void {
  const driverObj = driver({
    showProgress: true,
    progressText: "{{current}} / {{total}}",
    animate: true,
    overlayOpacity: 0.65,
    popoverClass: "alien-tour-popover",
    onDestroyed: () => localStorage.setItem(POST_TOUR_KEY, "1"),
    steps: [
      {
        element: '[data-tour="nav-trackers"]',
        popover: {
          title: "First trade logged",
          description: "Your agent made its first trade. The Trackers view shows all ongoing positions and queued commands.",
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
  });
  driverObj.drive();
}
