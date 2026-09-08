"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";
import SkyView, { GLYPH, type SkyData } from "../../components/SkyView";
import ZodiMark from "../../components/ZodiMark";
import { ThemeToggle, useTheme } from "../../components/ThemeProvider";

type Which = "birth" | "now";

/**
 * What to call the moment someone arrived.
 *
 * "The night you arrived" was written for the sound of it and is wrong for
 * roughly half of everyone, including anyone born at breakfast. The hour is the
 * one a clock on the wall there would have shown.
 */
function arrivalHeading(sky: SkyData | null): string {
  if (!sky || sky.birth_time_known === false || sky.local_hour === undefined) {
    return "The sky you arrived under";
  }
  const h = sky.local_hour;
  if (h >= 5 && h < 12) return "The morning you arrived";
  if (h >= 12 && h < 17) return "The afternoon you arrived";
  if (h >= 17 && h < 21) return "The evening you arrived";
  return "The night you arrived";
}

/** Which way you would have had to turn to see it. */
function compassWord(azimuth: number): string {
  const points = [
    "north", "north-east", "east", "south-east",
    "south", "south-west", "west", "north-west",
  ];
  return points[Math.round(azimuth / 45) % 8];
}

export default function SkyPage() {
  const { theme } = useTheme();
  const night = theme === "night";

  const [which, setWhich] = useState<Which>("birth");
  const [sky, setSky] = useState<Record<Which, SkyData | null>>({ birth: null, now: null });
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  // "Right now" is about where you are standing, which is very often not where
  // you were born. Never asked for unprompted: a location prompt on arrival is
  // rude, and the birthplace is a reasonable answer until someone says otherwise.
  const [here, setHere] = useState<{ lat: number; lon: number } | null>(null);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState("");

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      setLocationError("This browser can't share a location.");
      return;
    }
    setLocating(true);
    setLocationError("");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setHere({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        setSky((prev) => ({ ...prev, now: null }));   // refetch from the new spot
        setLocating(false);
      },
      () => {
        setLocating(false);
        setLocationError("Couldn't get your location. Showing your birthplace instead.");
      },
      { timeout: 10000, maximumAge: 300000 },
    );
  };

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
        const path =
          which === "birth"
            ? "/sky-at-birth"
            : here
            ? `/sky-now?latitude=${here.lat}&longitude=${here.lon}`
            : "/sky-now";
        const res = await apiFetch(path);
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
  }, [which, sky, here]);

  const current = sky[which];
  const up = current?.bodies.filter((b) => b.above_horizon) ?? [];

  return (
    <main
      className="min-h-screen"
      style={{
        background: "var(--sky)",
        paddingTop: "calc(clamp(18px, 4vw, 44px) + env(safe-area-inset-top, 0px))",
        paddingBottom: "calc(clamp(18px, 4vw, 44px) + env(safe-area-inset-bottom, 0px))",
        paddingLeft: "calc(clamp(18px, 4vw, 44px) + env(safe-area-inset-left, 0px))",
        paddingRight: "calc(clamp(18px, 4vw, 44px) + env(safe-area-inset-right, 0px))",
      }}
    >
      <div className="mx-auto flex w-full flex-col" style={{ maxWidth: 1120 }}>
        <header className="mb-7 flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <ZodiMark size={34} night={night} />
            <div>
              <p className="micro-label" style={{ letterSpacing: "0.26em" }}>Your sky</p>
              <h1
                className="font-display"
                style={{
                  fontSize: "clamp(27px, 5vw, 42px)",
                  lineHeight: 1.1,
                  marginTop: 2,
                  textWrap: "balance",
                }}
              >
                {which === "birth" ? arrivalHeading(sky.birth) : "Above you now"}
              </h1>
            </div>
          </div>
          <ThemeToggle />
        </header>

        <div className="mb-6 flex flex-wrap items-center gap-2">
          {([["birth", "At my birth"], ["now", "Right now"]] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => { setWhich(key); setSelected(null); }}
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
          {current?.local_time && which === "birth" && (
            <span className="micro-label" style={{ marginLeft: 4, color: "var(--ink-3)" }}>
              {current.local_time} · {current.place}
            </span>
          )}

          {which === "now" && (
            <>
              <span className="micro-label" style={{ marginLeft: 4, color: "var(--ink-3)" }}>
                Over {current?.place ?? "…"}
              </span>
              {!here && (
                <button
                  onClick={useMyLocation}
                  disabled={locating}
                  className="uppercase"
                  style={{
                    borderRadius: 999,
                    padding: "7px 14px",
                    fontSize: 10,
                    letterSpacing: "0.16em",
                    border: "1px dashed var(--line-2)",
                    background: "transparent",
                    color: "var(--gold-deep)",
                  }}
                >
                  {locating ? "Finding you…" : "Not there? Use my location"}
                </button>
              )}
            </>
          )}
        </div>

        {locationError && which === "now" && (
          <p className="font-reading" style={{ fontSize: 13, color: "var(--gold-deep)", marginTop: -12, marginBottom: 14 }}>
            {locationError}
          </p>
        )}

        {loading && !current && (
          <p className="font-reading" style={{ fontSize: 15, color: "var(--ink-3)" }}>
            Working out where everything was…
          </p>
        )}

        {error && (
          <p className="font-reading" style={{ fontSize: 15, color: "var(--gold-deep)" }}>{error}</p>
        )}

        {current && (
          <>
            {which === "birth" && current.birth_time_known === false && (
              <div className="time-warning" style={{ marginTop: 0, marginBottom: 18 }}>
                <p className="micro-label" style={{ letterSpacing: "0.18em" }}>Birth time unknown</p>
                <p className="font-reading mt-1">
                  This is cast for midday, so it isn&rsquo;t the sky you were actually born
                  under &mdash; the whole picture turns a full circle every day. Add your
                  birth time and it becomes yours.
                </p>
              </div>
            )}

            <div className="sky-layout">
              <div>
                <SkyView sky={current} selected={selected} onSelect={setSelected} />
                <p
                  className="font-reading"
                  style={{ fontSize: 14, color: "var(--ink-3)", marginTop: 18, lineHeight: 1.65 }}
                >
                  {current.daylight
                    ? "The Sun was up, so the sky was too bright to see any of this — but it was all there."
                    : current.twilight
                    ? "Twilight. The brightest of these were just coming out."
                    : `${current.visible_count} of these were visible to the naked eye.`}{" "}
                  Looking straight up from {current.place}: the centre is directly overhead,
                  the edge is the horizon, and the gold band is the ecliptic &mdash; the road
                  the planets keep to.
                </p>
              </div>

              {/* The list answers the only question the picture provokes: which
                  one is that? Tapping either side selects both. */}
              <aside>
                <div className="wanderers-head">
                  <span
                    className="micro-label"
                    style={{ letterSpacing: "0.32em", color: "var(--gold-deep)" }}
                  >
                    The wanderers
                  </span>
                  <span className="micro-label" style={{ color: "var(--ink-3)" }}>
                    {up.length} of {current.bodies.length} up
                  </span>
                </div>

                {current.bodies.map((b) => {
                  const isSelected = selected === b.name;
                  return (
                    <button
                      key={b.name}
                      onClick={() => setSelected(isSelected ? null : b.name)}
                      aria-pressed={isSelected}
                      className={
                        "wanderer" +
                        (isSelected ? " is-selected" : "") +
                        (b.above_horizon ? "" : " is-down")
                      }
                    >
                      <span className="wanderer-medallion">{GLYPH[b.name] ?? b.name[0]}</span>
                      <span className="min-w-0 text-left">
                        <span className="wanderer-name font-display">{b.name}</span>
                        <span className="wanderer-sub">
                          {b.above_horizon
                            ? `${Math.round(b.altitude)}° up, ${compassWord(b.azimuth)}`
                            : "below the horizon"}
                        </span>
                      </span>
                      <span className="wanderer-sign font-reading">
                        {Math.round(b.degree_in_sign)}° {b.sign}
                        {b.retrograde ? " ℞" : ""}
                      </span>
                    </button>
                  );
                })}

                <p
                  className="font-reading"
                  style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 14, lineHeight: 1.6 }}
                >
                  {current.moon_illumination > 0.97
                    ? "The Moon was full."
                    : current.moon_illumination < 0.03
                    ? "The Moon was new — dark, and in the sky regardless."
                    : `The Moon was ${Math.round(current.moon_illumination * 100)}% lit.`}
                </p>
              </aside>
            </div>

            <p style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 26, lineHeight: 1.6, maxWidth: 620 }}>
              Planets calculated with the Swiss Ephemeris. 8,920 stars to magnitude 6.5
              from the{" "}
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
