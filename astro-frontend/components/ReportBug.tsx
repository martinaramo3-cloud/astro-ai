"use client";

import { useEffect, useState } from "react";
import { getBrowserApiBase } from "../lib/api";

/**
 * A way to say something is broken.
 *
 * The error log catches what crashes. It cannot catch an answer that made no
 * sense, a button that did nothing, or a chart that looks wrong — and those are
 * most of what is actually wrong with a young app. Without somewhere to put it,
 * a person who hits one of those just leaves.
 *
 * Small and out of the way on purpose: present when wanted, invisible the rest
 * of the time.
 *
 * The trigger sits in the page's own flow rather than floating in a corner.
 * Floated, it landed on the model chips in chat and on the legal line when
 * signed out — a permanent overlap on a phone, where every corner is spoken
 * for.
 */
export default function ReportBug() {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [state, setState] = useState<"writing" | "sending" | "sent">("writing");
  const [error, setError] = useState("");

  useEffect(() => {
    const escape = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, []);

  const send = async () => {
    if (text.trim().length < 3) { setError("A sentence is plenty — what happened?"); return; }
    setState("sending");
    setError("");
    try {
      // Signed in or not: the bug that stops you logging in is the one most
      // worth hearing about, so the token rides along only when there is one.
      const token = (() => { try { return localStorage.getItem("token"); } catch { return null; } })();
      const res = await fetch(`${getBrowserApiBase()}/bug-reports`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message: text.trim(), page: window.location.pathname }),
      });
      if (!res.ok) throw new Error("rejected");
      setState("sent");
      setText("");
      setTimeout(() => { setOpen(false); setState("writing"); }, 2200);
    } catch {
      setState("writing");
      setError("That didn't send. Try again in a moment.");
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        aria-label="Report a problem"
        title="Something wrong? Tell us"
        className="zo-bug-open"
      >
        Report a bug
      </button>

      {open && (
        <div className="zo-bug-backdrop" onClick={() => setOpen(false)}>
          <div
            className="zo-bug-panel"
            role="dialog"
            aria-label="Report a problem"
            onClick={(e) => e.stopPropagation()}
          >
            {state === "sent" ? (
              <>
                <h2 className="font-display" style={{ fontSize: 22, marginBottom: 6 }}>Thank you</h2>
                <p className="font-reading" style={{ fontSize: 15, color: "var(--ink-2)" }}>
                  That&rsquo;s been logged. It genuinely helps.
                </p>
              </>
            ) : (
              <>
                <h2 className="font-display" style={{ fontSize: 22, marginBottom: 4 }}>
                  What went wrong?
                </h2>
                <p className="font-reading" style={{ fontSize: 14.5, color: "var(--ink-3)", marginBottom: 12 }}>
                  Anything that looked broken, made no sense, or didn&rsquo;t do what
                  you expected. A sentence is plenty.
                </p>
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  autoFocus
                  rows={4}
                  placeholder="The answer mentioned a rising sign but I never gave my birth time…"
                  className="zo-bug-input font-reading"
                />
                {error && (
                  <p className="font-reading" style={{ fontSize: 13.5, color: "var(--gold-deep)", marginTop: 8 }}>
                    {error}
                  </p>
                )}
                <div className="mt-3 flex items-center justify-end gap-3">
                  <button onClick={() => setOpen(false)} className="micro-label" style={{ color: "var(--ink-3)" }}>
                    Cancel
                  </button>
                  <button
                    onClick={send}
                    disabled={state === "sending"}
                    className="micro-label"
                    style={{
                      letterSpacing: "0.14em",
                      color: "var(--on-gold)",
                      background: "linear-gradient(135deg, var(--gold), var(--gold-deep))",
                      borderRadius: 999,
                      padding: "10px 20px",
                      opacity: state === "sending" ? 0.6 : 1,
                    }}
                  >
                    {state === "sending" ? "Sending…" : "Send"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
