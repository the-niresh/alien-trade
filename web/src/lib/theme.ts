const KEY = "at-theme";

export type Theme = "dark" | "light";

export function getTheme(): Theme {
  return (localStorage.getItem(KEY) as Theme) ?? "dark";
}

export function applyTheme(t: Theme) {
  if (t === "light") {
    document.documentElement.setAttribute("data-theme", "light");
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
  localStorage.setItem(KEY, t);
}

export function toggleTheme(): Theme {
  const next: Theme = getTheme() === "dark" ? "light" : "dark";
  applyTheme(next);
  return next;
}
