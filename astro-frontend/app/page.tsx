"use client";

import { useEffect, useState } from "react";
import { apiFetch, saveAuth } from "../lib/api";
import PlaceAutocomplete from "../components/PlaceAutocomplete";
import ZodiMark from "../components/ZodiMark";
import Wordmark from "../components/Wordmark";
import { ThemeToggle, useTheme } from "../components/ThemeProvider";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// The splash is a ceiling, not a fixed wait — a warm load should not feel
// padded. The floor has to outlast the wordmark reveal (300ms delay + 1800ms
// animation), plus a beat to read the tagline, or a cached load cuts the brand
// moment off halfway through.
const SPLASH_MAX_MS = 3600;
const SPLASH_MIN_MS = 2700;
const SPLASH_SEEN_KEY = "zodi-splash-seen";

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span className="micro-label auth-label block" style={{ letterSpacing: "0.22em" }}>
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
  // Six fields don't fit a laptop viewport, let alone a phone — so signup is
  // split: who you are, then when and where you were born.
  const [signupStep, setSignupStep] = useState<1 | 2>(1);
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
    setSignupStep(1);
    setMessage("");
  };

  /** Check only the fields on the first step, then advance. */
  const continueToBirthDetails = () => {
    if (!form.name.trim()) return setMessage("Please enter your name.");
    if (!EMAIL_RE.test(form.email)) return setMessage("Please enter a valid email address.");
    if (form.password.length < 6) return setMessage("Password must be at least 6 characters.");
    setMessage("");
    setSignupStep(2);
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
    if (!validate()) {
      // Send them back to whichever step holds the offending field.
      const onFirstStep =
        !form.name.trim() || !EMAIL_RE.test(form.email) || form.password.length < 6;
      if (onFirstStep) setSignupStep(1);
      return;
    }
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
      className="auth-main zo-rise relative flex min-h-screen flex-col items-center"
      style={{ background: "var(--sky)" }}
    >
      {/* In flow on phones, where pinning it to the corner puts it on top of
          the mark; back to the corner once there's room. */}
      <div
        className="z-10 mb-6 flex w-full justify-end lg:absolute lg:right-[22px] lg:top-[22px] lg:mb-0 lg:w-auto"
        style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}
      >
        <ThemeToggle />
      </div>

      <div style={{ width: "min(430px, 100%)" }} className="mx-auto flex flex-col items-center">
        <ZodiMark night={night} sizeFromCss className="auth-mark" />
        <div style={{ marginTop: 10 }}>
          <Wordmark zSize={46} restSize={25} />
        </div>

        <p
          className="font-reading auth-blurb text-center"
          style={{ color: "var(--ink-2)", maxWidth: "34ch" }}
        >
          {!isSignup
            ? "Welcome back. The sky has moved since you were here."
            : signupStep === 1
              ? "First, who you are."
              : "Now the sky when you arrived — this is what your chart is built from."}
        </p>

        {/* Card */}
        <div
          className="auth-card w-full"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--line)",
            boxShadow: "var(--shadow)",
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
          <div className="auth-fields mt-4 flex flex-col">
            {isSignup && signupStep === 1 && (
              <label className="block">
                <Label>Your name</Label>
                <input
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  placeholder="Martina"
                  className="auth-field"
                />
              </label>
            )}

            {(!isSignup || signupStep === 1) && (
            <label className="block">
              <Label>Email</Label>
              <input
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder="you@somewhere.com"
                className="auth-field"
              />
            </label>
            )}

            {(!isSignup || signupStep === 1) && (
            <label className="block">
              <Label>Password</Label>
              <input
                name="password"
                type="password"
                value={form.password}
                onChange={handleChange}
                placeholder={isSignup ? "At least 6 characters" : "••••••••"}
                className="auth-field"
              />
            </label>
            )}

            {isSignup && signupStep === 2 && (
              <>
                <div>
                  <Label>Born</Label>
                  <div className="flex" style={{ gap: 10 }}>
                    <input
                      name="birth_date"
                      type="date"
                      value={form.birth_date}
                      onChange={handleChange}
                      className="auth-field" style={{ flex: 1 }}
                    />
                    <input
                      name="birth_time"
                      type="time"
                      value={form.birth_time}
                      onChange={handleChange}
                      className="auth-field" style={{ width: 92 }}
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
                    className="auth-field"
                  />
                </label>
              </>
            )}
          </div>

          {/* Primary CTA */}
          <button
            onClick={
              !isSignup
                ? handleLogin
                : signupStep === 1
                  ? continueToBirthDetails
                  : handleSignup
            }
            disabled={loading}
            className="auth-cta w-full uppercase"
            style={{
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
              : !isSignup
                ? "Continue"
                : signupStep === 1
                  ? "Next"
                  : "Create account"}
          </button>

          {isSignup && signupStep === 2 && !loading && (
            <button
              onClick={() => { setMessage(""); setSignupStep(1); }}
              className="micro-label mt-3 w-full"
              style={{ letterSpacing: "0.16em" }}
            >
              &larr; Back
            </button>
          )}

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
          style={{ fontSize: 12, lineHeight: 1.7, color: "var(--ink-3)", maxWidth: "36ch" }}
        >
          {isSignup ? (
            <>
              By creating an account you agree to our{" "}
              <a href="/terms" style={{ color: "var(--gold-deep)" }}>Terms</a> and{" "}
              <a href="/privacy" style={{ color: "var(--gold-deep)" }}>Privacy Policy</a>.
              Your birth details are used to cast your chart, and nothing else.
            </>
          ) : (
            <>
              <a href="/terms" style={{ color: "var(--gold-deep)" }}>Terms</a>
              {" · "}
              <a href="/privacy" style={{ color: "var(--gold-deep)" }}>Privacy</a>
            </>
          )}
        </p>
      </div>
    </main>
  );
}
