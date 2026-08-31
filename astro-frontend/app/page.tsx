"use client";

import { useEffect, useState } from "react";
import { apiFetch, saveAuth } from "../lib/api";
import PlaceAutocomplete from "../components/PlaceAutocomplete";
import ZodiMark from "../components/ZodiMark";
import Wordmark from "../components/Wordmark";
import { ThemeToggle, useTheme } from "../components/ThemeProvider";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// The splash is a ceiling, not a fixed wait — a warm load should not feel
// padded. The floor exists so the wordmark animation isn't cut off mid-reveal.
const SPLASH_MAX_MS = 3200;
const SPLASH_MIN_MS = 1600;
const SPLASH_SEEN_KEY = "zodi-splash-seen";

const fieldStyle: React.CSSProperties = {
  border: "1px solid var(--line-2)",
  background: "var(--ground)",
  borderRadius: 14,
  padding: "13px 16px",
  fontSize: 16,
  width: "100%",
  outline: "none",
};

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span className="micro-label mb-[7px] block" style={{ letterSpacing: "0.22em" }}>
      {children}
    </span>
  );
}

export default function Home() {
  const { theme } = useTheme();
  const night = theme === "night";

  // The splash covers app boot on a cold open; it shouldn't replay all session.
  const [showSplash, setShowSplash] = useState(true);

  const [mode, setMode] = useState<"signup" | "login">("signup");
  const [form, setForm] = useState({
    name: "", email: "", password: "", birth_date: "", birth_time: "", birth_place: "",
  });
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let seen = false;
    try {
      seen = window.sessionStorage.getItem(SPLASH_SEEN_KEY) === "1";
    } catch {
      /* private mode — just show it */
    }
    if (seen) {
      setShowSplash(false);
      return;
    }

    let done = false;
    const advance = () => {
      if (done) return;
      done = true;
      setShowSplash(false);
      try {
        window.sessionStorage.setItem(SPLASH_SEEN_KEY, "1");
      } catch {
        /* non-critical */
      }
    };

    // Hard ceiling, so a slow load never strands anyone on the splash.
    const ceiling = setTimeout(advance, SPLASH_MAX_MS);

    // Ready = webfonts loaded, since that is what the brand moment depends on.
    const readiness = document.fonts?.ready ?? Promise.resolve();
    const floor = new Promise((r) => setTimeout(r, SPLASH_MIN_MS));
    Promise.all([readiness, floor]).then(advance);

    return () => clearTimeout(ceiling);
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const switchMode = (next: "signup" | "login") => {
    setMode(next);
    setMessage("");
  };

  const validate = () => {
    if (!form.name.trim()) {
      setMessage("Please enter your full name.");
      return false;
    }
    if (!EMAIL_RE.test(form.email)) {
      setMessage("Please enter a valid email address.");
      return false;
    }
    if (form.password.length < 6) {
      setMessage("Password must be at least 6 characters.");
      return false;
    }
    if (!form.birth_date) {
      setMessage("Please enter your birth date.");
      return false;
    }
    if (!form.birth_time) {
      setMessage("Please enter your birth time.");
      return false;
    }
    if (!form.birth_place.trim()) {
      setMessage("Please enter your birth place.");
      return false;
    }
    return true;
  };

  const handleSignup = async () => {
    setMessage("");
    if (!validate()) return;
    setLoading(true);
    try {
      const response = await apiFetch("/signup", {
        method: "POST",
        body: JSON.stringify(form),
      });
      const data = await response.json();
      if (!response.ok) {
        setMessage(data.detail || "Signup failed.");
        setLoading(false);
        return;
      }
      saveAuth(data);
      setMessage("Account created successfully.");
      setTimeout(() => { window.location.href = "/chat"; }, 700);
    } catch {
      setMessage("Taking a moment to wake up — please try again in 30 seconds.");
    }
    setLoading(false);
  };

  const handleLogin = async () => {
    setMessage("");
    if (!EMAIL_RE.test(form.email)) {
      setMessage("Please enter a valid email address.");
      return;
    }
    setLoading(true);
    try {
      const response = await apiFetch("/login", {
        method: "POST",
        body: JSON.stringify({ email: form.email, password: form.password }),
      });
      const data = await response.json();
      if (!response.ok) {
        setMessage(data.detail || "Invalid email or password.");
        setLoading(false);
        return;
      }
      saveAuth(data);
      window.location.href = "/chat";
    } catch {
      setMessage("Taking a moment to wake up — please try again in 30 seconds.");
    }
    setLoading(false);
  };

  /* ─── Splash ─── */
  if (showSplash) {
    return (
      <main
        className="flex min-h-screen flex-col items-center justify-center px-6"
        style={{ background: "var(--sky)" }}
      >
        <div className="zo-fade">
          <ZodiMark size={268} night={night} className="max-w-[56vw]" />
        </div>
        <div style={{ marginTop: 26 }}>
          <Wordmark zSize="clamp(52px, 13vw, 84px)" restSize="clamp(28px, 6.6vw, 44px)" animate />
        </div>
        <p
          className="zo-fade mt-4 uppercase"
          style={{
            fontSize: 12,
            letterSpacing: "0.28em",
            color: "var(--ink-3)",
            animationDelay: "1100ms",
          }}
        >
          the sky, in plain language
        </p>
      </main>
    );
  }

  /* ─── Auth ─── */
  const isSignup = mode === "signup";

  return (
    <main
      className="zo-rise relative flex min-h-screen flex-col items-center px-6 py-12"
      style={{ background: "var(--sky)" }}
    >
      <div className="safe-top absolute right-[22px] top-[22px] z-10">
        <ThemeToggle />
      </div>

      <div style={{ width: "min(430px, 100%)" }} className="mx-auto flex flex-col items-center">
        <ZodiMark size={96} night={night} />
        <div style={{ marginTop: 14 }}>
          <Wordmark zSize={52} restSize={28} />
        </div>

        <p
          className="font-reading mt-3 text-center"
          style={{ fontSize: 17, lineHeight: 1.6, color: "var(--ink-2)", maxWidth: "32ch" }}
        >
          {isSignup
            ? "A few details about the sky when you arrived, and we can begin."
            : "Welcome back. The sky has moved since you were here."}
        </p>

        {/* Card */}
        <div
          className="w-full"
          style={{
            marginTop: 26,
            background: "var(--surface)",
            border: "1px solid var(--line)",
            borderRadius: 28,
            boxShadow: "var(--shadow)",
            padding: "26px 26px 24px",
          }}
        >
          {/* Tabs */}
          <div
            className="flex gap-1 p-1"
            style={{ background: "var(--sunk)", borderRadius: 999 }}
          >
            {([["login", "Sign in"], ["signup", "Create account"]] as const).map(
              ([value, label]) => {
                const active = mode === value;
                return (
                  <button
                    key={value}
                    onClick={() => switchMode(value)}
                    className="flex-1"
                    style={{
                      fontSize: 13,
                      letterSpacing: "0.1em",
                      borderRadius: 999,
                      padding: "11px 12px",
                      background: active ? "var(--surface)" : "transparent",
                      color: active ? "var(--ink)" : "var(--ink-3)",
                      boxShadow: active ? "var(--shadow-sm)" : "none",
                    }}
                  >
                    {label}
                  </button>
                );
              },
            )}
          </div>

          {/* Fields */}
          <div className="mt-5 flex flex-col" style={{ gap: 14 }}>
            {isSignup && (
              <label className="block">
                <Label>Your name</Label>
                <input
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  placeholder="Martina"
                  style={fieldStyle}
                />
              </label>
            )}

            <label className="block">
              <Label>Email</Label>
              <input
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder="you@somewhere.com"
                style={fieldStyle}
              />
            </label>

            <label className="block">
              <Label>Password</Label>
              <input
                name="password"
                type="password"
                value={form.password}
                onChange={handleChange}
                placeholder={isSignup ? "At least 6 characters" : "••••••••"}
                style={fieldStyle}
              />
            </label>

            {isSignup && (
              <>
                <div>
                  <Label>Born</Label>
                  <div className="flex" style={{ gap: 10 }}>
                    <input
                      name="birth_date"
                      type="date"
                      value={form.birth_date}
                      onChange={handleChange}
                      style={{ ...fieldStyle, flex: 1 }}
                    />
                    <input
                      name="birth_time"
                      type="time"
                      value={form.birth_time}
                      onChange={handleChange}
                      style={{ ...fieldStyle, width: 92 }}
                    />
                  </div>
                </div>

                <label className="block">
                  {/* Not in the handoff, but the chart can't be cast without it. */}
                  <Label>Birth place</Label>
                  <PlaceAutocomplete
                    value={form.birth_place}
                    onChange={(v) => setForm({ ...form, birth_place: v })}
                    placeholder="Lisbon, Portugal"
                    style={fieldStyle}
                  />
                </label>
              </>
            )}
          </div>

          {/* Primary CTA */}
          <button
            onClick={isSignup ? handleSignup : handleLogin}
            disabled={loading}
            className="mt-5 w-full uppercase"
            style={{
              borderRadius: 999,
              padding: "15px 20px",
              background: "linear-gradient(135deg, var(--gold), var(--gold-deep))",
              color: "var(--on-gold)",
              fontSize: 13,
              letterSpacing: "0.2em",
              boxShadow: "var(--shadow-sm)",
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading
              ? "One moment…"
              : isSignup
                ? "Create account"
                : "Continue"}
          </button>

          {message && (
            <p
              className="font-reading mt-4 text-center"
              style={{ fontSize: 15, lineHeight: 1.6, color: "var(--ink-2)" }}
            >
              {message}
            </p>
          )}
        </div>

        <p
          className="mt-5 text-center"
          style={{ fontSize: 12, lineHeight: 1.7, color: "var(--ink-3)", maxWidth: "34ch" }}
        >
          Your birth details are used to cast your chart, and nothing else.
        </p>
      </div>
    </main>
  );
}
