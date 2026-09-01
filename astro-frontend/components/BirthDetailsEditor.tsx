"use client";

import { useState } from "react";
import { apiFetch } from "../lib/api";
import PlaceAutocomplete from "./PlaceAutocomplete";

/**
 * Edit the birth details behind a chart — your own, or a person you saved.
 *
 * Both forms are the same shape, so they share one component: a chart is only
 * as good as the moment it was cast for, and until this existed a guessed
 * birth time was permanent.
 */

export type EditableDetails = {
  name?: string;
  label?: string;
  person_name?: string;
  relationship_type?: string;
  birth_date: string;
  birth_time: string;
  birth_place: string;
  birth_time_known?: boolean;
};

const fieldStyle: React.CSSProperties = {
  border: "1px solid var(--line-2)",
  background: "var(--ground)",
  borderRadius: 14,
  padding: "10px 13px",
  fontSize: 14,
  width: "100%",
  outline: "none",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="micro-label mb-1 block">{label}</span>
      {children}
    </label>
  );
}

export default function BirthDetailsEditor({
  kind,
  initial,
  endpoint,
  onSaved,
  onClose,
}: {
  /** "me" also edits your name; "person" edits their label and relationship. */
  kind: "me" | "person";
  initial: EditableDetails;
  /** Where the PATCH goes — "/me" or "/profiles/{id}". */
  endpoint: string;
  onSaved: (saved: Record<string, unknown>) => void;
  onClose: () => void;
}) {
  const isMe = kind === "me";

  const [form, setForm] = useState({
    name: initial.name ?? "",
    label: initial.label ?? "",
    person_name: initial.person_name ?? "",
    relationship_type: initial.relationship_type ?? "",
    birth_date: initial.birth_date ?? "",
    // A stored time is meaningless when the flag says it was never known, so
    // the field starts empty rather than showing the noon placeholder back.
    birth_time: initial.birth_time_known === false ? "" : (initial.birth_time ?? ""),
    birth_place: initial.birth_place ?? "",
    birth_time_known: initial.birth_time_known !== false,
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const set = (patch: Partial<typeof form>) => setForm((prev) => ({ ...prev, ...patch }));

  const save = async () => {
    if (saving) return;

    const missing = [
      ...(isMe ? [[form.name, "your name"]] : [
        [form.label, "a label, like “My boyfriend”"],
        [form.person_name, "their name"],
      ]),
      [form.birth_date, "a birth date"],
      ...(form.birth_time_known
        ? [[form.birth_time, "a birth time, or tick that it's unknown"]]
        : []),
      [form.birth_place, "a birth place"],
    ].find(([value]) => !String(value).trim());

    if (missing) {
      setError(`Please add ${missing[1]}.`);
      return;
    }

    setError("");
    setSaving(true);
    try {
      const body = {
        ...(isMe
          ? { name: form.name }
          : { label: form.label, person_name: form.person_name, relationship_type: form.relationship_type }),
        birth_date: form.birth_date,
        birth_time: form.birth_time,
        birth_place: form.birth_place,
        birth_time_known: form.birth_time_known,
      };
      const res = await apiFetch(endpoint, { method: "PATCH", body: JSON.stringify(body) });
      const data = await res.json();
      if (res.ok) onSaved(data);
      else setError(data.detail || "Could not save these details.");
    } catch {
      setError("Could not reach the server. Try again in a moment.");
    }
    setSaving(false);
  };

  return (
    <div
      className="fixed inset-0 z-[70] flex items-start justify-center overflow-y-auto p-4 sm:items-center"
      style={{ background: "rgba(0,0,0,0.55)" }}
      onClick={onClose}
    >
      <div
        className="my-auto w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--surface)",
          border: "1px solid var(--line)",
          borderRadius: 28,
          boxShadow: "var(--shadow)",
          padding: 24,
        }}
      >
        <div className="mb-4 flex items-start justify-between">
          <div>
            <p className="micro-label">{isMe ? "Your details" : "Their details"}</p>
            <h2 className="font-display" style={{ fontSize: 24, marginTop: 4 }}>
              {isMe ? "Edit my chart" : initial.label || "Edit person"}
            </h2>
          </div>
          <button onClick={onClose} aria-label="Close" style={{ fontSize: 18, color: "var(--ink-3)" }}>
            ✕
          </button>
        </div>

        <p
          className="font-reading mb-4"
          style={{ fontSize: 14, lineHeight: 1.6, color: "var(--ink-2)" }}
        >
          Changing any of these recasts the chart, so future answers will read
          from the new one.
        </p>

        <div className="flex flex-col gap-3">
          {isMe ? (
            <Field label="Your name">
              <input
                value={form.name}
                onChange={(e) => set({ name: e.target.value })}
                style={fieldStyle}
              />
            </Field>
          ) : (
            <>
              <Field label="Label">
                <input
                  value={form.label}
                  onChange={(e) => set({ label: e.target.value })}
                  placeholder="My boyfriend"
                  style={fieldStyle}
                />
              </Field>
              <Field label="Their name">
                <input
                  value={form.person_name}
                  onChange={(e) => set({ person_name: e.target.value })}
                  style={fieldStyle}
                />
              </Field>
              <Field label="Relationship (optional)">
                <input
                  value={form.relationship_type}
                  onChange={(e) => set({ relationship_type: e.target.value })}
                  style={fieldStyle}
                />
              </Field>
            </>
          )}

          <Field label="Birth date">
            <input
              type="date"
              value={form.birth_date}
              onChange={(e) => set({ birth_date: e.target.value })}
              style={fieldStyle}
            />
          </Field>

          {form.birth_time_known && (
            <Field label="Birth time">
              <input
                type="time"
                value={form.birth_time}
                onChange={(e) => set({ birth_time: e.target.value })}
                style={fieldStyle}
              />
            </Field>
          )}

          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={!form.birth_time_known}
              onChange={(e) => set({ birth_time_known: !e.target.checked })}
              className="unknown-time-box"
            />
            <span style={{ fontSize: 13, color: "var(--ink-2)" }}>
              {isMe
                ? "I don’t know my birth time"
                : "They don’t know their birth time"}
            </span>
          </label>

          {!form.birth_time_known && (
            <div className="time-warning" style={{ marginTop: 0 }}>
              <p className="micro-label" style={{ letterSpacing: "0.18em" }}>
                Birth time unknown
              </p>
              <p className="font-reading mt-1">
                {isMe ? (
                  <>
                    Without your exact birth time, we can&rsquo;t calculate your
                    Rising sign, houses, or certain degrees and aspects. Your
                    reading will still use the planetary placements available
                    from your birth date.
                  </>
                ) : (
                  <>
                    Without their exact birth time, we can&rsquo;t calculate their
                    Rising sign, houses, or certain degrees and aspects. Your
                    compatibility reading will still use the planetary placements
                    available from their birth date.
                  </>
                )}
              </p>
            </div>
          )}

          <Field label="Birth place">
            <PlaceAutocomplete
              value={form.birth_place}
              onChange={(v) => set({ birth_place: v })}
              placeholder="Birth place"
              style={fieldStyle}
            />
          </Field>

          {error && (
            <p style={{ fontSize: 13, lineHeight: 1.5, color: "var(--gold-deep)" }}>{error}</p>
          )}

          <button
            onClick={save}
            disabled={saving}
            className="uppercase"
            style={{
              borderRadius: 999,
              padding: "12px 16px",
              background: "linear-gradient(135deg, var(--gold), var(--gold-deep))",
              color: "var(--on-gold)",
              fontSize: 12,
              letterSpacing: "0.2em",
              opacity: saving ? 0.6 : 1,
            }}
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
