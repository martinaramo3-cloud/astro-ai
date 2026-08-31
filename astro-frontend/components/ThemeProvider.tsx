"use client";

import { createContext, useContext, useEffect, useState } from "react";

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

export default function ThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  // Render day on the server, then correct on the client — the local hour
  // isn't knowable during SSR, and guessing causes a hydration mismatch.
  const [theme, setThemeState] = useState<Theme>("day");

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = window.localStorage.getItem(STORAGE_KEY);
    } catch {
      /* private mode — fall back to the clock */
    }
    setThemeState(stored === "day" || stored === "night" ? stored : themeFromClock());
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const setTheme = (next: Theme) => {
    setThemeState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* the choice just won't persist */
    }
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
