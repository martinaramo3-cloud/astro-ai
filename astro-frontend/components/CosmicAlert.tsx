"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../lib/api";

type NatalHit = {
  natal_point: string;
  aspect: string;
  orb: number;
  house: number | null;
  personal: boolean;
};

export type CosmicEvent = {
  type: "lunation" | "eclipse" | "station";
  name: string;
  date: string;
  sign: string;
  degree: number;
  significance: number;
  is_personal: boolean;
  days_away: number;
  natal_hits: NatalHit[];
};

export type CosmicEvents = {
  moon: { phase_name: string; moon_sign: string; illumination: number };
  retrograde_now: string[];
  headline: CosmicEvent | null;
  events: CosmicEvent[];
};

const EVENT_ICON: Record<CosmicEvent["type"], string> = {
  eclipse: "🌑",
  lunation: "🌕",
  station: "℞",
};

/** "tonight" / "tomorrow" / "in 4 days" — vaguer than a date, but friendlier. */
function whenLabel(daysAway: number) {
  if (daysAway < 0) return "happening now";
  if (daysAway < 1) return "today";
  if (daysAway < 2) return "tomorrow";
  return `in ${Math.round(daysAway)} days`;
}

function hitLabel(event: CosmicEvent) {
  const hit = event.natal_hits.find((h) => h.personal) ?? event.natal_hits[0];
  if (!hit) return null;
  const verb =
    hit.aspect === "conjunction" ? "sits on" :
    hit.aspect === "opposition" ? "opposes" : "squares";
  return `${verb} your ${hit.natal_point}`;
}

export default function CosmicAlert({
  onAsk,
}: {
  onAsk?: (question: string) => void;
}) {
  const [data, setData] = useState<CosmicEvents | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    let active = true;
    apiFetch("/cosmic-events")
      .then((res) => (res.ok ? res.json() : null))
      .then((json) => {
        if (active && json) setData(json);
      })
      .catch(() => {
        /* the alert is a bonus; never block the chat on it */
      });
    return () => {
      active = false;
    };
  }, []);

  const event = data?.headline ?? null;

  // Only re-surface when the event itself changes, so dismissing sticks.
  useEffect(() => {
    if (!event) return;
    const key = `cosmic-dismissed:${event.name}:${event.date.slice(0, 10)}`;
    setDismissed(window.localStorage.getItem(key) === "1");
  }, [event]);

  if (!event || dismissed) return null;

  const dismiss = () => {
    window.localStorage.setItem(
      `cosmic-dismissed:${event.name}:${event.date.slice(0, 10)}`,
      "1",
    );
    setDismissed(true);
  };

  const hit = hitLabel(event);
  const question = `There's a ${event.name} in ${event.sign} ${whenLabel(
    event.days_away,
  )}${hit ? ` that ${hit}` : ""}. What does it mean for me?`;

  return (
    <div
      className="zo-msg mb-5"
      style={{
        border: "1px solid var(--line)",
        background: event.is_personal ? "var(--gold-soft)" : "var(--surface)",
        borderRadius: 16,
        padding: "14px 16px",
      }}
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-lg leading-none" aria-hidden="true">
          {EVENT_ICON[event.type]}
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-reading" style={{ fontSize: 17 }}>
            {event.name} in {event.sign}
            <span className="ml-2" style={{ color: "var(--ink-3)" }}>
              {whenLabel(event.days_away)}
            </span>
          </p>
          {hit && (
            <p
              className="font-reading mt-1"
              style={{ fontSize: 15, lineHeight: 1.6, color: "var(--ink-2)" }}
            >
              It {hit} — this one lands close to home.
            </p>
          )}
          {onAsk && (
            <button
              onClick={() => onAsk(question)}
              className="mt-3 uppercase"
              style={{
                borderRadius: 999,
                border: "1px solid var(--line-2)",
                padding: "7px 14px",
                fontSize: 10,
                letterSpacing: "0.16em",
                color: "var(--ink-2)",
              }}
            >
              Ask what it means for me
            </button>
          )}
        </div>
        <button
          onClick={dismiss}
          aria-label="Dismiss"
          className="shrink-0"
          style={{ fontSize: 14, color: "var(--ink-3)" }}
        >
          ✕
        </button>
      </div>
    </div>
  );
}
