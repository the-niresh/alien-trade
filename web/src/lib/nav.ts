import {
  Activity, Bell, BookOpen, Brain, FileText, History, LayoutDashboard, LineChart,
  List, PieChart, Settings, Users, Workflow, Wrench,
} from "lucide-react";

/**
 * One place that decides what every view is called and which icon it gets.
 *
 * The desktop rail and the mobile bottom bar used to keep separate copies of this
 * list, and they drifted: Pipeline was an Activity icon in one and a Cpu icon in the
 * other, and Trackers and Pipeline ended up sharing Activity — two rail buttons that
 * looked identical. Two lists of the same thing will always drift, so there is now
 * one, and `nav.test.ts` fails if any icon or label is reused.
 */

export type View =
  | "overview"
  | "trackers"
  | "intelligence"
  | "chart"
  | "portfolio"
  | "pipeline"
  | "positions"
  | "history"
  | "tools"
  | "agents"
  | "controls"
  | "logs"
  | "notifications"
  | "docs";

type IconComponent = React.ComponentType<{ className?: string }>;

export interface ViewMeta {
  icon: IconComponent;
  /** Rail tooltip and bottom-bar caption. Short — it sits under a 44px button. */
  label: string;
  /** One line, plain words, for anyone who has not seen this app before. */
  blurb: string;
}

export const VIEW_META: Record<View, ViewMeta> = {
  overview:      { icon: LayoutDashboard, label: "Overview",   blurb: "Account value, today's activity and the agent's current stance." },
  trackers:      { icon: Activity,        label: "Trackers",   blurb: "Price watches you set, and whether they have fired." },
  intelligence:  { icon: Brain,           label: "Intel",      blurb: "What the model layer wrote about the market, and what it cost." },
  chart:         { icon: LineChart,       label: "Markets",    blurb: "Live price charts for the tokens the agent is allowed to trade." },
  portfolio:     { icon: PieChart,        label: "Portfolio",  blurb: "What the wallet holds right now, and in what proportion." },
  pipeline:      { icon: Workflow,        label: "Pipeline",   blurb: "One decision cycle end to end: data in, gates, order out." },
  positions:     { icon: List,            label: "Positions",  blurb: "Open positions with entry price and unrealised profit or loss." },
  history:       { icon: History,         label: "History",    blurb: "Every trade the agent has made, oldest to newest." },
  tools:         { icon: Wrench,          label: "Tools",      blurb: "Manual actions: fund the wallet, convert, withdraw." },
  agents:        { icon: Users,           label: "Agents",     blurb: "The four helper agents and any you have spawned yourself." },
  controls:      { icon: Settings,        label: "Controls",   blurb: "Kill switch, risk caps and trading mode." },
  logs:          { icon: FileText,        label: "Logs",       blurb: "Raw decision and audit records, newest first." },
  notifications: { icon: Bell,            label: "Alerts",     blurb: "Things the agent wanted to tell you about." },
  docs:          { icon: BookOpen,        label: "Docs",       blurb: "How the strategy, risk engine and agents actually work." },
};

/** Rail order, top to bottom. Also the order the mobile bar derives from. */
export const NAV_ORDER: View[] = [
  "overview", "trackers", "intelligence", "chart", "portfolio", "pipeline",
  "positions", "history", "tools", "agents", "controls", "logs",
  "notifications", "docs",
];

export interface NavItem extends ViewMeta {
  view: View;
}

export const NAV_ITEMS: NavItem[] = NAV_ORDER.map((view) => ({ view, ...VIEW_META[view] }));

/** The mobile bottom bar shows these first; the rest go in its "More" sheet. */
export const PRIMARY_VIEWS: NavItem[] = [
  "overview", "trackers", "chart", "portfolio", "intelligence", "controls",
].map((v) => ({ view: v as View, ...VIEW_META[v as View] }));

export const MORE_VIEWS: NavItem[] = NAV_ORDER
  .filter((v) => !PRIMARY_VIEWS.some((p) => p.view === v))
  .map((view) => ({ view, ...VIEW_META[view] }));

export const VALID_VIEWS: ReadonlySet<string> = new Set<string>(NAV_ORDER);
