"use client";

import { createContext, useContext, useEffect, useSyncExternalStore } from "react";

type Theme = "day" | "night";

const STORAGE_KEY = "zodi-theme";

const ThemeContext = createContext<{
  theme: Theme;
  setTheme: (t: Theme) => void;
}>({ theme: "day", setTheme: () => {} });

export const useTheme = () => useContext(ThemeContext);

/** Night between 19:00 and 07:00, unless the viewer has chosen otherwise. */
function themeFromClock(): Theme {
  const hour = new Date().getHours();
  return hour >= 19 || hour < 7 ? "night" : "day";
}

let memoryTheme: Theme | null = null;
function readTheme(): Theme {
  if (memoryTheme) return memoryTheme;
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    if (value === "day" || value === "night") return value;
  } catch { /* private mode */ }
  return themeFromClock();
}
function subscribeTheme(listener: () => void) {
  const changed = () => { memoryTheme = null; listener(); };
  window.addEventListener("storage", changed);
  window.addEventListener("zodi-theme-change", listener);
  return () => {
    window.removeEventListener("storage", changed);
    window.removeEventListener("zodi-theme-change", listener);
  };
}

export default function ThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const theme = useSyncExternalStore(subscribeTheme, readTheme, () => "day" as Theme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const setTheme = (next: Theme) => {
    memoryTheme = next;
    try { window.localStorage.setItem(STORAGE_KEY, next); } catch { /* private mode */ }
    window.dispatchEvent(new Event("zodi-theme-change"));
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, setTheme } = useTheme();

  return (
    <div
      className={`flex items-center gap-1 rounded-full p-1 ${className}`}
      style={{
        background: "var(--surface)",
        border: "1px solid var(--line)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      {(["day", "night"] as const).map((option) => {
        const active = theme === option;
        return (
          <button
            key={option}
            onClick={() => setTheme(option)}
            className="rounded-full px-4 py-2 uppercase"
            style={{
              fontSize: 12,
              letterSpacing: "0.14em",
              background: active ? "var(--gold-soft)" : "transparent",
              color: active ? "var(--gold-deep)" : "var(--ink-3)",
            }}
          >
            {option === "day" ? "☀ Day" : "☾ Night"}
          </button>
        );
      })}
    </div>
  );
}
