"use client";

import { use, useEffect, useState } from "react";
import { apiFetch, errorMessage } from "../../../lib/api";
import PlaceAutocomplete from "../../../components/PlaceAutocomplete";
import ZodiMark from "../../../components/ZodiMark";
import { ThemeToggle, useTheme } from "../../../components/ThemeProvider";

/**
 * Someone else's first meeting with Zodi.
 *
 * They arrive because a friend asked for their birth details, not because they
 * wanted an app — so this asks for the four things and gets out of the way. The
 * invitation to try it themselves comes after they've been thanked, never
 * before.
 */

type Invite = { from_name: string; label: string; person_name: string };

export default function InvitePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const { theme } = useTheme();
  const night = theme === "night";

  const [invite, setInvite] = useState<Invite | null>(null);
  const [state, setState] = useState<"loading" | "form" | "gone" | "done">("loading");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    person_name: "",
    birth_date: "",
    birth_time: "",
    birth_place: "",
    birth_time_known: true,
  });

  useEffect(() => {
    (async () => {
      try {
        const res = await apiFetch(`/invite/${token}`);
        if (!res.ok) { setState("gone"); return; }
        const data: Invite = await res.json();
        setInvite(data);
        setForm((f) => ({ ...f, person_name: data.person_name || "" }));
        setState("form");
      } catch {
        setState("gone");
      }
    })();
  }, [token]);

  const submit = async () => {
    if (!form.person_name.trim()) return setError("Please add your name.");
    if (!form.birth_date) return setError("Please add your birth date.");
    if (form.birth_time_known && !form.birth_time) {
      return setError("Add your birth time, or tick that you don't know it.");
    }
    if (!form.birth_place.trim()) return setError("Please add your birth place.");

    setError("");
    setSaving(true);
    try {
      const res = await apiFetch(`/invite/${token}`, {
        method: "POST",
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (res.ok) setState("done");
      else setError(errorMessage(data, "That didn't save. Please try again."));
    } catch {
      setError("Couldn't reach the server. Try again in a moment.");
    }
    setSaving(false);
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

      <div style={{ width: "min(460px, 100%)" }} className="mx-auto flex flex-col items-center">
        <ZodiMark night={night} sizeFromCss className="auth-mark" />
        <div style={{ marginTop: 10 }} />

        <div
          className="auth-card w-full"
          style={{ background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow)" }}
        >
          {state === "loading" && (
            <p className="font-reading" style={{ color: "var(--ink-3)" }}>Opening…</p>
          )}

          {state === "gone" && (
            <>
              <h1 className="font-display" style={{ fontSize: 25, marginBottom: 8 }}>
                This link has expired
              </h1>
              <p className="font-reading" style={{ fontSize: 15.5, lineHeight: 1.6, color: "var(--ink-2)" }}>
                Invitations last two weeks and can only be used once. Ask
                whoever sent it for a fresh one.
              </p>
              <a
                href="/"
                className="mt-4 block text-center micro-label"
                style={{ color: "var(--gold-deep)", textDecoration: "none" }}
              >
                What is Zodi?
              </a>
            </>
          )}

          {state === "done" && (
            <>
              <h1 className="font-display" style={{ fontSize: 27, marginBottom: 8 }}>
                Thank you
              </h1>
              <p className="font-reading" style={{ fontSize: 16, lineHeight: 1.65, color: "var(--ink-2)" }}>
                {invite?.from_name} now has everything needed to read the two
                charts together. Your details are used for nothing else.
              </p>
              <p className="font-reading" style={{ fontSize: 16, lineHeight: 1.65, color: "var(--ink-2)", marginTop: 14 }}>
                Curious what your own chart says? It takes a minute, and Zodi is
                free to try.
              </p>
              <a
                href="/"
                className="auth-cta mt-4 block text-center uppercase"
                style={{
                  background: "linear-gradient(135deg, var(--gold), var(--gold-deep))",
                  color: "var(--on-gold)", fontSize: 12, letterSpacing: "0.2em", textDecoration: "none",
                }}
              >
                Read my chart
              </a>
            </>
          )}

          {state === "form" && invite && (
            <>
              <p className="micro-label" style={{ letterSpacing: "0.22em", color: "var(--gold-deep)" }}>
                An invitation
              </p>
              <h1 className="font-display" style={{ fontSize: 27, lineHeight: 1.15, margin: "8px 0 10px" }}>
                {invite.from_name} wants to read your charts together
              </h1>
              <p className="font-reading" style={{ fontSize: 15.5, lineHeight: 1.6, color: "var(--ink-2)", marginBottom: 18 }}>
                Astrology needs the moment you were born to say anything real.
                Four things, and you never have to make an account.
              </p>

              <input
                value={form.person_name}
                onChange={(e) => setForm({ ...form, person_name: e.target.value })}
                placeholder="First name"
                className="auth-field"
              />

              <div style={{ marginTop: 12 }}>
                <span className="micro-label mb-1 block">Birth date</span>
                <input
                  type="date"
                  value={form.birth_date}
                  onChange={(e) => setForm({ ...form, birth_date: e.target.value })}
                  className="auth-field"
                />
              </div>

              <div style={{ marginTop: 12 }}>
                <span className="micro-label mb-1 block">Birth time</span>
                <input
                  type="time"
                  value={form.birth_time}
                  onChange={(e) => setForm({ ...form, birth_time: e.target.value })}
                  disabled={!form.birth_time_known}
                  className="auth-field"
                  style={{ opacity: form.birth_time_known ? 1 : 0.45 }}
                />
                <label
                  className="font-reading mt-2 flex items-center gap-2"
                  style={{ fontSize: 14, color: "var(--ink-2)", cursor: "pointer" }}
                >
                  <input
                    type="checkbox"
                    checked={!form.birth_time_known}
                    onChange={(e) => setForm({ ...form, birth_time_known: !e.target.checked })}
                  />
                  I don&rsquo;t know my birth time
                </label>
                {!form.birth_time_known && (
                  <p className="font-reading" style={{ fontSize: 13.5, lineHeight: 1.5, color: "var(--ink-3)", marginTop: 6 }}>
                    That&rsquo;s fine — most people don&rsquo;t. Everything except
                    the houses still works.
                  </p>
                )}
              </div>

              <div style={{ marginTop: 12 }}>
                <span className="micro-label mb-1 block">Birth place</span>
                <PlaceAutocomplete
                  value={form.birth_place}
                  onChange={(place) => setForm({ ...form, birth_place: place })}
                  placeholder="City and country"
                  className="auth-field"
                />
              </div>

              {error && (
                <p className="font-reading" style={{ fontSize: 14, color: "var(--gold-deep)", marginTop: 12 }}>
                  {error}
                </p>
              )}

              <button
                onClick={submit}
                disabled={saving}
                className="auth-cta mt-4 w-full uppercase"
                style={{
                  background: "linear-gradient(135deg, var(--gold), var(--gold-deep))",
                  color: "var(--on-gold)", fontSize: 12, letterSpacing: "0.2em",
                  opacity: saving ? 0.6 : 1,
                }}
              >
                {saving ? "Sending…" : `Send to ${invite.from_name}`}
              </button>

              <p className="font-reading" style={{ fontSize: 13, lineHeight: 1.55, color: "var(--ink-3)", marginTop: 14 }}>
                Your details go to {invite.from_name} only, to calculate the two
                charts. Nothing is posted anywhere.{" "}
                <a href="/privacy" style={{ color: "var(--gold-deep)" }}>How data is handled</a>.
              </p>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
