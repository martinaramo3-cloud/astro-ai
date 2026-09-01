"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";
import SkyView, { type SkyData } from "../../components/SkyView";
import ZodiMark from "../../components/ZodiMark";
import { ThemeToggle, useTheme } from "../../components/ThemeProvider";

type Which = "birth" | "now";

export default function SkyPage() {
  const { theme } = useTheme();
  const night = theme === "night";

  const [which, setWhich] = useState<Which>("birth");
  const [sky, setSky] = useState<Record<Which, SkyData | null>>({ birth: null, now: null });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Each view is fetched once and kept: the sky at birth never changes, and
    // the sky now changes too slowly to be worth refetching on a tab press.
    if (sky[which]) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");

    (async () => {
      try {
        const res = await apiFetch(which === "birth" ? "/sky-at-birth" : "/sky-now");
        const data = await res.json();
        if (cancelled) return;
        if (res.ok) setSky((prev) => ({ ...prev, [which]: data }));
        else setError(typeof data.detail === "string" ? data.detail : "Could not build the sky.");
      } catch {
        if (!cancelled) setError("Could not reach the sky service. Try again in a moment.");
      }
      if (!cancelled) setLoading(false);
    })();

    return () => { cancelled = true; };
  }, [which, sky]);

  const current = sky[which];

  return (
    <main
      className="min-h-screen"
      style={{ background: "var(--sky)", padding: "clamp(18px, 4vw, 40px)" }}
    >
      <div className="mx-auto flex w-full flex-col" style={{ maxWidth: 640 }}>
        <header className="mb-6 flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <ZodiMark size={34} night={night} />
            <div>
              <p className="micro-label" style={{ letterSpacing: "0.24em" }}>
                Your sky
              </p>
              <h1 className="font-display" style={{ fontSize: 27, lineHeight: 1.15, marginTop: 2 }}>
                {which === "birth" ? "The night you arrived" : "Above you now"}
              </h1>
            </div>
          </div>
          <ThemeToggle />
        </header>

        <div className="mb-6 flex gap-2">
          {([["birth", "At my birth"], ["now", "Right now"]] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setWhich(key)}
              className="uppercase"
              style={{
                borderRadius: 999,
                padding: "9px 18px",
                fontSize: 11,
                letterSpacing: "0.18em",
                border: "1px solid var(--line-2)",
                background: which === key ? "var(--gold-soft)" : "transparent",
                color: which === key ? "var(--ink)" : "var(--ink-3)",
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {loading && !current && (
          <p className="font-reading" style={{ fontSize: 15, color: "var(--ink-3)" }}>
            Working out where everything was…
          </p>
        )}

        {error && (
          <p className="font-reading" style={{ fontSize: 15, color: "var(--gold-deep)" }}>
            {error}
          </p>
        )}

        {current && (
          <>
            {which === "birth" && current.birth_time_known === false && (
              <div className="time-warning" style={{ marginTop: 0, marginBottom: 16 }}>
                <p className="micro-label" style={{ letterSpacing: "0.18em" }}>
                  Birth time unknown
                </p>
                <p className="font-reading mt-1">
                  This is cast for midday, so it isn&rsquo;t the sky you were actually
                  born under &mdash; the whole picture turns a full circle every day.
                  Add your birth time and it becomes yours.
                </p>
              </div>
            )}

            <SkyView sky={current} night={night} />

            <p
              className="font-reading"
              style={{ fontSize: 14, color: "var(--ink-3)", marginTop: 20, lineHeight: 1.65 }}
            >
              Looking straight up from {current.place}. The centre is directly
              overhead, the edge is the horizon, and the dotted line is the
              ecliptic &mdash; the path every planet follows, which is why they
              are strung along it rather than scattered.
            </p>

            {/* Required by the catalogue's licence, and it belongs here anyway:
                these are real stars, from real measurements someone made. */}
            <p style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 14, lineHeight: 1.6 }}>
              Planets calculated with the Swiss Ephemeris. 8,920 stars to
              magnitude 6.5 from the{" "}
              <a
                href="https://codeberg.org/astronexus/hyg"
                target="_blank"
                rel="noreferrer noopener"
                style={{ color: "var(--ink-3)", textDecoration: "underline" }}
              >
                HYG Database
              </a>{" "}
              by David Nash, used under CC BY-SA 4.0.
            </p>
          </>
        )}
      </div>
    </main>
  );
}
