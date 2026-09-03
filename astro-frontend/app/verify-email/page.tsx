"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiFetch } from "../../lib/api";
import ZodiMark from "../../components/ZodiMark";
import { ThemeToggle, useTheme } from "../../components/ThemeProvider";

function VerifyInner() {
  const { theme } = useTheme();
  const night = theme === "night";
  const params = useSearchParams();
  const token = params.get("token") ?? "";

  const [state, setState] = useState<"working" | "done" | "failed">("working");

  useEffect(() => {
    if (!token) { setState("failed"); return; }
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch("/verify-email", {
          method: "POST",
          body: JSON.stringify({ token }),
        });
        if (cancelled) return;
        setState(res.ok ? "done" : "failed");
        // Keep the stored user in step, so the app stops nudging.
        if (res.ok) {
          try {
            const raw = localStorage.getItem("user");
            if (raw) {
              const u = JSON.parse(raw);
              u.email_verified = true;
              localStorage.setItem("user", JSON.stringify(u));
            }
          } catch { /* not signed in on this device — fine */ }
        }
      } catch {
        if (!cancelled) setState("failed");
      }
    })();
    return () => { cancelled = true; };
  }, [token]);

  return (
    <div className="auth-card w-full text-center" style={{ background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow)" }}>
      <div className="mx-auto mb-3"><ZodiMark night={night} size={44} /></div>
      {state === "working" && (
        <p className="font-reading" style={{ fontSize: 16, color: "var(--ink-2)" }}>Confirming your email…</p>
      )}
      {state === "done" && (
        <>
          <h1 className="font-display" style={{ fontSize: 26, marginBottom: 6 }}>Email confirmed</h1>
          <p className="font-reading" style={{ fontSize: 15, color: "var(--ink-2)" }}>
            You&rsquo;re all set. Thank you.
          </p>
          <a href="/chat" className="auth-cta mt-4 block uppercase"
             style={{ background: "linear-gradient(135deg, var(--gold), var(--gold-deep))", color: "var(--on-gold)", fontSize: 12, letterSpacing: "0.2em", textDecoration: "none" }}>
            Open Zodi
          </a>
        </>
      )}
      {state === "failed" && (
        <>
          <h1 className="font-display" style={{ fontSize: 24, marginBottom: 6 }}>Link expired</h1>
          <p className="font-reading" style={{ fontSize: 15, color: "var(--ink-2)" }}>
            This confirmation link is invalid or has expired. You can send a fresh
            one from your account settings inside Zodi.
          </p>
          <a href="/chat" className="mt-4 block micro-label" style={{ color: "var(--ink-3)", textDecoration: "none" }}>
            Open Zodi
          </a>
        </>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <main className="auth-main relative flex min-h-screen flex-col items-center justify-center" style={{ background: "var(--sky)" }}>
      <div className="z-10 mb-6 flex w-full justify-end lg:absolute lg:right-[22px] lg:top-[22px] lg:mb-0"
           style={{ paddingTop: "env(safe-area-inset-top, 0px)" }}>
        <ThemeToggle />
      </div>
      <div style={{ width: "min(430px, 100%)" }} className="mx-auto">
        <Suspense fallback={<p className="font-reading text-center" style={{ color: "var(--ink-3)" }}>Loading…</p>}>
          <VerifyInner />
        </Suspense>
      </div>
    </main>
  );
}
