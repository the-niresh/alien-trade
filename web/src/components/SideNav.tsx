import { useState } from "react";
import { toggleTheme, getTheme } from "../lib/theme";

export type View = "overview" | "positions" | "agents" | "controls" | "logs";

const NAV_ITEMS: { view: View; icon: string; label: string }[] = [
  { view: "overview",  icon: "◈", label: "Overview" },
  { view: "positions", icon: "⬡", label: "Positions" },
  { view: "agents",    icon: "⚛", label: "Agents" },
  { view: "controls",  icon: "⚙", label: "Controls" },
  { view: "logs",      icon: "≡", label: "Logs" },
];

type Props = { active: View; onSelect: (v: View) => void; onCopilot: () => void };

export function SideNav({ active, onSelect, onCopilot }: Props) {
  const [theme, setTheme] = useState(getTheme);

  const handleThemeToggle = () => {
    const next = toggleTheme();
    setTheme(next);
  };

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
        ✦
      </button>
      <button
        className="nav-icon"
        title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        onClick={handleThemeToggle}
        style={{ color: "var(--muted)", fontSize: 16 }}
      >
        {theme === "dark" ? "○" : "●"}
      </button>
    </nav>
  );
}
