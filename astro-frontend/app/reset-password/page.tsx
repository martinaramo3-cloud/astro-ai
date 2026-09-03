"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiFetch, errorMessage, saveAuth } from "../../lib/api";
import ZodiMark from "../../components/ZodiMark";
import { ThemeToggle, useTheme } from "../../components/ThemeProvider";

// Mirrors the server's rule; the server is the one that counts.
const PASSWORD_RULES: { label: string; ok: (p: string) => boolean }[] = [
  { label: "8 characters or more", ok: (p) => p.length >= 8 },
  { label: "a capital letter", ok: (p) => /[A-Z]/.test(p) },
  { label: "a number", ok: (p) => /[0-9]/.test(p) },
  { label: "a symbol, like ! or ?", ok: (p) => /[^A-Za-z0-9]/.test(p) },
];

function EyeIcon({ open }: { open: boolean }) {
  return (
    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12Z"
        stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="2.6" stroke="currentColor" strokeWidth="1.4" />
      {!open && <path d="M4 20 20 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />}
    </svg>
  );
}

function ResetForm() {
  const { theme } = useTheme();
  const night = theme === "night";
  const params = useSearchParams();
  const token = params.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const missing = PASSWORD_RULES.filter((r) => !r.ok(password));

  const submit = async () => {
    if (missing.length) { setError(`Password needs ${missing.map((m) => m.label).join(", ")}.`); return; }
    if (confirm !== password) { setError("The two passwords don't match."); return; }
    setError("");
    setLoading(true);
    try {
      const res = await apiFetch("/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, password }),
      });
      const data = await res.json();
      if (res.ok) {
        // The reset signs you in fresh, so drop straight into the app.
        saveAuth(data);
        window.location.href = "/chat";
      } else {
        setError(errorMessage(data, "That reset link is invalid or has expired."));
      }
    } catch {
      setError("Couldn't reach the server. Try again in a moment.");
    }
    setLoading(false);
  };

  if (!token) {
    return (
      <div className="auth-card w-full" style={{ background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow)" }}>
        <h1 className="font-display" style={{ fontSize: 24, marginBottom: 8 }}>Link missing</h1>
        <p className="font-reading" style={{ fontSize: 15, color: "var(--ink-2)" }}>
          This page needs a reset link from your email. Request a fresh one:
        </p>
        <a href="/forgot-password" className="auth-cta mt-4 block text-center uppercase"
           style={{ background: "linear-gradient(135deg, var(--gold), var(--gold-deep))", color: "var(--on-gold)", fontSize: 12, letterSpacing: "0.2em", textDecoration: "none" }}>
          Send a reset link
        </a>
      </div>
    );
  }

  return (
    <div className="auth-card w-full" style={{ background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow)" }}>
      <h1 className="font-display" style={{ fontSize: 26, marginBottom: 6 }}>Set a new password</h1>
      <p className="font-reading" style={{ fontSize: 15, color: "var(--ink-2)", marginBottom: 16 }}>
        Choose something you&rsquo;ll remember. You&rsquo;ll be signed in once it&rsquo;s set.
      </p>

      <div className="pw-wrap">
        <input
          type={show ? "text" : "password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="New password"
          className="auth-field"
          autoComplete="new-password"
          autoFocus
        />
        <button type="button" onClick={() => setShow((v) => !v)} aria-label={show ? "Hide" : "Show"} className="pw-eye">
          <EyeIcon open={show} />
        </button>
      </div>

      {password.length > 0 && (
        <ul className="pw-rules">
          {PASSWORD_RULES.map((rule) => {
            const met = rule.ok(password);
            return (
              <li key={rule.label} className={met ? "is-met" : ""}>
                <span aria-hidden="true">{met ? "✓" : "·"}</span>
                {rule.label}
              </li>
            );
          })}
        </ul>
      )}

      <div className="pw-wrap" style={{ marginTop: 12 }}>
        <input
          type={show ? "text" : "password"}
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
          placeholder="Type it again"
          className="auth-field"
          autoComplete="new-password"
          style={confirm.length > 0 && confirm !== password ? { borderColor: "var(--gold-deep)" } : undefined}
        />
      </div>
      {confirm.length > 0 && confirm !== password && (
        <span className="pw-mismatch">These don&rsquo;t match yet.</span>
      )}

      {error && (
        <p className="font-reading" style={{ fontSize: 14, color: "var(--gold-deep)", marginTop: 10 }}>{error}</p>
      )}

      <button
        onClick={submit}
        disabled={loading}
        className="auth-cta mt-4 w-full uppercase"
        style={{ background: "linear-gradient(135deg, var(--gold), var(--gold-deep))", color: "var(--on-gold)", fontSize: 12, letterSpacing: "0.2em", opacity: loading ? 0.6 : 1 }}
      >
        {loading ? "Saving…" : "Set password & sign in"}
      </button>

      <ZodiMark night={night} size={0} className="hidden" />
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="auth-main relative flex min-h-screen flex-col items-center" style={{ background: "var(--sky)" }}>
      <div className="z-10 mb-6 flex w-full justify-end lg:absolute lg:right-[22px] lg:top-[22px] lg:mb-0 lg:w-auto"
           style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}>
        <ThemeToggle />
      </div>
      <div style={{ width: "min(430px, 100%)" }} className="mx-auto flex flex-col items-center">
        <Suspense fallback={<p className="font-reading" style={{ color: "var(--ink-3)" }}>Loading…</p>}>
          <ResetForm />
        </Suspense>
      </div>
    </main>
  );
}
