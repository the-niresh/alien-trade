import { LayoutDashboard, Activity, LineChart, PieChart, Brain, Settings, List, Users, Cpu, FileText, Bell, BookOpen } from "lucide-react";
import type { View } from "../components/SideNav";

export const PRIMARY_VIEWS: { view: View; icon: React.ComponentType<{ className?: string }>; label: string }[] = [
  { view: "overview",     icon: LayoutDashboard, label: "Overview" },
  { view: "trackers",     icon: Activity,        label: "Trackers" },
  { view: "chart",        icon: LineChart,       label: "Markets" },
  { view: "portfolio",    icon: PieChart,        label: "Portfolio" },
  { view: "intelligence", icon: Brain,           label: "Intel" },
  { view: "controls",     icon: Settings,        label: "Controls" },
];

export const MORE_VIEWS: { view: View; icon: React.ComponentType<{ className?: string }>; label: string }[] = [
  { view: "positions",     icon: List,            label: "Positions" },
  { view: "agents",        icon: Users,           label: "Agents" },
  { view: "pipeline",      icon: Cpu,             label: "Pipeline" },
  { view: "logs",          icon: FileText,        label: "Logs" },
  { view: "notifications", icon: Bell,            label: "Alerts" },
  { view: "docs",          icon: BookOpen,        label: "Docs" },
];
