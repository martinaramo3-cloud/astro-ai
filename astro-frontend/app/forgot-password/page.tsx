"use client";

import { useState } from "react";
import { apiFetch } from "../../lib/api";
import ZodiMark from "../../components/ZodiMark";
import { ThemeToggle, useTheme } from "../../components/ThemeProvider";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ForgotPasswordPage() {
  const { theme } = useTheme();
  const night = theme === "night";

  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    if (!EMAIL_RE.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await apiFetch("/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      // The server answers the same whether or not the account exists, so the
      // page does too — no way to fish for who has an account.
      setSent(true);
    } catch {
      setError("Couldn't reach the server. Try again in a moment.");
    }
    setLoading(false);
  };

  return (
    <main
      className="auth-main relative flex min-h-screen flex-col items-center"
      style={{ background: "var(--sky)" }}
    >
      <div
        className="z-10 mb-6 flex w-full justify-end lg:absolute lg:right-[22px] lg:top-[22px] lg:mb-0 lg:w-auto"
        style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}
      >
        <ThemeToggle />
      </div>

      <div style={{ width: "min(430px, 100%)" }} className="mx-auto flex flex-col items-center">
        <ZodiMark night={night} sizeFromCss className="auth-mark" />
        <div style={{ marginTop: 10 }} />

        <div className="auth-card w-full" style={{ background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow)" }}>
          {sent ? (
            <>
              <h1 className="font-display" style={{ fontSize: 26, marginBottom: 8 }}>Check your inbox</h1>
              <p className="font-reading" style={{ fontSize: 15, lineHeight: 1.6, color: "var(--ink-2)" }}>
                If <strong>{email}</strong> has a Zodi account, a link to set a new
                password is on its way. It works for the next hour.
              </p>
              <p className="font-reading" style={{ fontSize: 14, lineHeight: 1.6, color: "var(--ink-3)", marginTop: 14 }}>
                Didn&rsquo;t get it? Check spam, or{" "}
                <button
                  onClick={() => { setSent(false); }}
                  style={{ color: "var(--gold-deep)", textDecoration: "underline" }}
                >
                  try another email
                </button>.
              </p>
              <a href="/" className="auth-cta mt-4 block text-center uppercase"
                 style={{ background: "linear-gradient(135deg, var(--gold), var(--gold-deep))", color: "var(--on-gold)", fontSize: 12, letterSpacing: "0.2em", textDecoration: "none" }}>
                Back to sign in
              </a>
            </>
          ) : (
            <>
              <h1 className="font-display" style={{ fontSize: 26, marginBottom: 6 }}>Forgot your password?</h1>
              <p className="font-reading" style={{ fontSize: 15, lineHeight: 1.6, color: "var(--ink-2)", marginBottom: 16 }}>
                Enter your email and we&rsquo;ll send you a link to set a new one.
              </p>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
                placeholder="you@somewhere.com"
                className="auth-field"
                autoFocus
              />
              {error && (
                <p className="font-reading" style={{ fontSize: 14, color: "var(--gold-deep)", marginTop: 10 }}>{error}</p>
              )}
              <button
                onClick={submit}
                disabled={loading}
                className="auth-cta mt-4 w-full uppercase"
                style={{ background: "linear-gradient(135deg, var(--gold), var(--gold-deep))", color: "var(--on-gold)", fontSize: 12, letterSpacing: "0.2em", opacity: loading ? 0.6 : 1 }}
              >
                {loading ? "Sending…" : "Send reset link"}
              </button>
              <a href="/" className="mt-4 block text-center micro-label" style={{ color: "var(--ink-3)", textDecoration: "none" }}>
                Back to sign in
              </a>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
