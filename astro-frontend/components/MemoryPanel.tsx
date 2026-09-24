"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../lib/api";

/**
 * What Zoli remembers, and the controls to change it.
 *
 * Everything here is one tap from deletion on purpose. A memory feature people
 * cannot see is a feature they have to trust blindly, and the whole reason to
 * ask before turning it on is that trusting blindly is not something to ask of
 * someone who came here to talk about their life.
 */

type Memory = {
  id: number;
  kind: "fact" | "plan" | "conclusion";
  text: string;
  said_on: string;
  status: string;
};

const KIND_LABEL: Record<string, string> = {
  fact: "About you",
  plan: "Something you were planning",
  conclusion: "What Zoli read",
};

function said(on: string) {
  const days = Math.round((Date.now() - new Date(on).getTime()) / 86400000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.round(days / 30);
  return months === 1 ? "a month ago" : `${months} months ago`;
}

export default function MemoryPanel() {
  const [enabled, setEnabled] = useState(false);
  const [asked, setAsked] = useState(true);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await apiFetch("/me/memory");
      if (!res.ok) return;
      const data = await res.json();
      setEnabled(data.enabled);
      setAsked(data.asked);
      setMemories(data.memories ?? []);
    } catch {
      /* the panel is not worth an error message of its own */
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const setMemoryOn = async (on: boolean) => {
    setBusy(true);
    try {
      await apiFetch("/me/memory", { method: "PATCH", body: JSON.stringify({ enabled: on }) });
      await load();
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: number) => {
    await apiFetch(`/me/memory/${id}`, { method: "DELETE" });
    setMemories((all) => all.filter((m) => m.id !== id));
  };

  const save = async (id: number) => {
    if (!draft.trim()) return;
    await apiFetch(`/me/memory/${id}`, { method: "PATCH", body: JSON.stringify({ text: draft }) });
    setEditing(null);
    await load();
  };

  // Never been asked: the question, in plain words, before anything is kept.
  if (!asked) {
    return (
      <section className="mt-6 pt-5" style={{ borderTop: "1px solid var(--line)" }}>
        <p className="micro-label">Memory</p>
        <p className="font-reading mt-2" style={{ fontSize: 15, lineHeight: 1.6, color: "var(--ink-2)" }}>
          Want Zoli to remember things you tell it, so readings get more
          personal? You can see and delete anything, any time.
        </p>
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => setMemoryOn(true)}
            disabled={busy}
            className="micro-label"
            style={{
              letterSpacing: "0.14em", color: "var(--on-gold)",
              background: "linear-gradient(135deg, var(--gold), var(--gold-deep))",
              borderRadius: 999, padding: "9px 18px",
            }}
          >
            Yes, remember
          </button>
          <button
            onClick={() => setMemoryOn(false)}
            disabled={busy}
            className="micro-label"
            style={{
              letterSpacing: "0.14em", color: "var(--ink-2)",
              border: "1px solid var(--line-2)", borderRadius: 999, padding: "9px 18px",
            }}
          >
            No thanks
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="mt-6 pt-5" style={{ borderTop: "1px solid var(--line)" }}>
      <div className="flex items-center justify-between">
        <p className="micro-label">Memory</p>
        <button
          onClick={() => setMemoryOn(!enabled)}
          disabled={busy}
          className="micro-label"
          style={{ letterSpacing: "0.14em", color: enabled ? "var(--gold-deep)" : "var(--ink-3)" }}
        >
          {enabled ? "On · turn off" : "Off · turn on"}
        </button>
      </div>

      {!enabled && (
        <p className="font-reading mt-2" style={{ fontSize: 14, lineHeight: 1.55, color: "var(--ink-3)" }}>
          Zoli isn&rsquo;t keeping anything between conversations. Turning it on
          starts from scratch &mdash; nothing was saved while it was off.
        </p>
      )}

      {enabled && memories.length === 0 && (
        <p className="font-reading mt-2" style={{ fontSize: 14, lineHeight: 1.55, color: "var(--ink-3)" }}>
          Nothing saved yet. Things you mention get kept after a conversation ends.
        </p>
      )}

      {enabled && memories.length > 0 && (
        <>
          <ul className="mt-3 flex flex-col gap-2" style={{ listStyle: "none", padding: 0 }}>
            {memories.map((memory) => (
              <li
                key={memory.id}
                style={{
                  background: "var(--sunk)", borderRadius: 14, padding: "11px 13px",
                }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="micro-label" style={{ letterSpacing: "0.14em" }}>
                      {KIND_LABEL[memory.kind] ?? memory.kind}
                      {memory.status === "needs_check_in" && " · Zoli will ask about this"}
                    </p>
                    {editing === memory.id ? (
                      <input
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && save(memory.id)}
                        autoFocus
                        className="font-reading mt-1 w-full"
                        style={{
                          fontSize: 14.5, background: "var(--surface)",
                          border: "1px solid var(--line-2)", borderRadius: 9,
                          padding: "6px 9px",
                        }}
                      />
                    ) : (
                      <p className="font-reading mt-1" style={{ fontSize: 14.5, lineHeight: 1.5 }}>
                        {memory.text}
                      </p>
                    )}
                    <p style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 2 }}>
                      you said this {said(memory.said_on)}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    {editing === memory.id ? (
                      <button onClick={() => save(memory.id)} className="row-action" style={{ fontSize: 13 }}>
                        ✓
                      </button>
                    ) : (
                      <button
                        onClick={() => { setEditing(memory.id); setDraft(memory.text); }}
                        aria-label="Edit"
                        className="row-action"
                        style={{ fontSize: 13 }}
                      >
                        {"✎︎"}
                      </button>
                    )}
                    <button
                      onClick={() => remove(memory.id)}
                      aria-label="Forget this"
                      className="row-action"
                      style={{ fontSize: 14 }}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
          <button
            onClick={async () => {
              await apiFetch("/me/memory", { method: "DELETE" });
              setMemories([]);
            }}
            className="micro-label mt-3"
            style={{ letterSpacing: "0.14em", color: "var(--gold-deep)" }}
          >
            Forget everything
          </button>
        </>
      )}
    </section>
  );
}
