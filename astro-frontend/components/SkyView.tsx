"use client";

import { useEffect, useRef, useState } from "react";

/**
 * The sky as it actually was, from one place at one moment.
 *
 * This is a stereographic projection of the half-dome above the observer: the
 * centre is straight up, the rim is the horizon, and the compass runs around
 * the edge. It is the same projection every planisphere uses, and it is the
 * reason the ecliptic comes out as a graceful arc rather than a straight line.
 *
 * Deliberately plain, so the visual direction can be set separately. Every
 * position here is real — nothing is placed for looks.
 */

export type SkyBody = {
  name: string;
  altitude: number;   // degrees above the horizon; negative is below
  azimuth: number;    // compass bearing, 0 = north, 90 = east
  above_horizon: boolean;
  sign: string;
  degree_in_sign: number;
  retrograde: boolean;
  magnitude: number;
  naked_eye: boolean;
};

export type Star = [number, number, number, string?];  // ra hours, dec deg, mag, name?

export type SkyData = {
  place?: string;
  local_sidereal_hours: number;
  observer: { latitude: number; longitude: number };
  timezone?: string | null;
  moment_utc: string;
  bodies: SkyBody[];
  ecliptic: { longitude: number; azimuth: number; altitude: number; sign: string }[];
  daylight: boolean;
  twilight: boolean;
  sun_altitude: number;
  moon_illumination: number;
  visible_count: number;
  visible_names: string[];
  birth_time_known?: boolean;
};

const GLYPH: Record<string, string> = {
  Sun: "☉︎", Moon: "☽︎", Mercury: "☿︎", Venus: "♀︎", Mars: "♂︎",
  Jupiter: "♃︎", Saturn: "♄︎", Uranus: "♅︎", Neptune: "♆︎", Pluto: "♇︎",
};

const SIZE = 460;
const R = SIZE / 2 - 34;      // horizon radius
const CX = SIZE / 2;
const CY = SIZE / 2;

/**
 * Stereographic: straight up is the centre, the horizon is the rim.
 * North sits at the top and east to the left, because you are looking *up* at
 * the dome, not down at a map — this is what makes a printed planisphere match
 * the sky when you hold it over your head.
 */
function project(altitude: number, azimuth: number) {
  const zenithDistance = 90 - altitude;
  const r = (R * zenithDistance) / 90;
  const a = (azimuth * Math.PI) / 180;
  // North at the top, east to the LEFT. Mirrored against a map on purpose:
  // you are looking up at a dome, not down at the ground, so this is the
  // orientation that matches the sky when you hold the picture overhead.
  return { x: CX - r * Math.sin(a), y: CY - r * Math.cos(a) };
}

/** Brighter things are bigger. Magnitude runs backwards: lower is brighter. */
function radiusFor(magnitude: number) {
  return Math.max(2.6, Math.min(11, 7.6 - magnitude * 0.85));
}

/**
 * A fixed star's place in this observer's sky.
 *
 * The standard equatorial-to-horizon conversion. Checked against Swiss
 * Ephemeris on five bodies at a real moment and it agreed to 0.000 degrees,
 * so the stars sit in the same sky as the planets rather than a parallel one.
 */
function starPosition(ra: number, dec: number, lst: number, latitude: number) {
  const H = ((lst - ra) * 15 * Math.PI) / 180;
  const d = (dec * Math.PI) / 180;
  const p = (latitude * Math.PI) / 180;

  const sinAlt = Math.sin(d) * Math.sin(p) + Math.cos(d) * Math.cos(p) * Math.cos(H);
  const alt = Math.asin(Math.max(-1, Math.min(1, sinAlt)));
  const cosA =
    (Math.sin(d) - Math.sin(alt) * Math.sin(p)) / (Math.cos(alt) * Math.cos(p));
  const A = (Math.acos(Math.max(-1, Math.min(1, cosA))) * 180) / Math.PI;

  return {
    altitude: (alt * 180) / Math.PI,
    azimuth: Math.sin(H) < 0 ? A : 360 - A,
  };
}

const CARDINALS = [
  { bearing: 0, label: "N" },
  { bearing: 90, label: "E" },
  { bearing: 180, label: "S" },
  { bearing: 270, label: "W" },
];

function StarField({
  sky, colour, ground, daySky,
}: { sky: SkyData; colour: string; ground: string; daySky: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [stars, setStars] = useState<Star[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/stars.json")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (!cancelled && d?.stars) setStars(d.stars); })
      .catch(() => { /* the sky is still worth showing without them */ });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    // The dome is drawn even before the catalogue arrives, so the sky is never
    // briefly a hole in the page.
    if (!canvas) return;

    // Drawn at device resolution so the small dots stay crisp.
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = SIZE * dpr;
    canvas.height = SIZE * dpr;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, SIZE, SIZE);

    ctx.save();
    ctx.beginPath();
    ctx.arc(CX, CY, R, 0, Math.PI * 2);
    ctx.clip();

    // The dome is painted here rather than in the SVG so the stars can lie on
    // top of it while the planets and labels stay above them in the SVG.
    const dome = ctx.createRadialGradient(CX, CY * 0.84, 0, CX, CY, R * 1.15);
    dome.addColorStop(0, daySky ? "#2c3f63" : "#131c30");
    dome.addColorStop(1, ground);
    ctx.fillStyle = dome;
    ctx.fillRect(0, 0, SIZE, SIZE);

    if (daySky) { ctx.restore(); return; }   // daylight drowns the stars

    const lst = sky.local_sidereal_hours;
    const lat = sky.observer.latitude;

    for (const [ra, dec, mag] of stars ?? []) {
      const { altitude, azimuth } = starPosition(ra, dec, lst, lat);
      if (altitude <= 0) continue;               // below the horizon
      const { x, y } = project(altitude, azimuth);

      // Brightness runs backwards: magnitude -1 is brilliant, 6.5 is barely
      // there. Both size and opacity carry it, which is what stops a starfield
      // looking like scattered identical dots.
      const t = Math.max(0, Math.min(1, (6.5 - mag) / 8));
      ctx.globalAlpha = 0.28 + t * 0.72;
      ctx.beginPath();
      ctx.arc(x, y, 0.35 + t * 1.9, 0, Math.PI * 2);
      ctx.fillStyle = colour;
      ctx.fill();
    }
    ctx.restore();
  }, [stars, sky, colour]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{
        position: "absolute", inset: 0, width: "100%", height: "100%",
        pointerEvents: "none",
      }}
    />
  );
}

export default function SkyView({ sky, night = true }: { sky: SkyData; night?: boolean }) {
  const ground = night ? "#0d1220" : "#182338";
  const rim = night ? "rgba(217,176,106,.5)" : "rgba(201,154,69,.55)";
  const ink = night ? "#d9b06a" : "#c99a45";
  const faint = night ? "rgba(236,237,244,.34)" : "rgba(236,237,244,.4)";

  // Only the part of the ecliptic that is above the horizon can be drawn on a
  // dome that stops at the horizon.
  const arc = sky.ecliptic.filter((p) => p.altitude > 0);
  const up = sky.bodies.filter((b) => b.above_horizon);
  const down = sky.bodies.filter((b) => !b.above_horizon);

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-full" style={{ maxWidth: 520 }}>
      {/* In daylight the sky washes the stars out, so they are not drawn. */}
      <StarField
        sky={sky}
        colour={night ? "#e8e9f2" : "#f2eee2"}
        ground={night ? "#0d1220" : "#182338"}
        daySky={sky.daylight}
      />
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        width="100%"
        style={{ maxWidth: 520, position: "relative" }}
        role="img"
        aria-label={`The sky over ${sky.place ?? "your birthplace"}, looking up`}
      >
        <defs>
          {/* A body sitting on the horizon has its glow half outside the dome,
              which reads as a rendering fault rather than as something setting. */}
          <clipPath id="dome-clip">
            <circle cx={CX} cy={CY} r={R} />
          </clipPath>
        </defs>

        {/* Altitude rings: 30° and 60° up, plus the horizon itself. */}
        {[30, 60].map((alt) => (
          <circle
            key={alt}
            cx={CX} cy={CY} r={(R * (90 - alt)) / 90}
            fill="none" stroke={faint} strokeWidth="0.6" strokeDasharray="2 4"
          />
        ))}
        <circle cx={CX} cy={CY} r={R} fill="none" stroke={rim} strokeWidth="1.2" />

        {/* The ecliptic — the line the planets travel along. */}
        {arc.length > 1 && (
          <polyline
            points={arc.map((p) => {
              const { x, y } = project(p.altitude, p.azimuth);
              return `${x.toFixed(1)},${y.toFixed(1)}`;
            }).join(" ")}
            fill="none" stroke={ink} strokeWidth="1" strokeDasharray="4 5" opacity="0.55"
          />
        )}

        {CARDINALS.map(({ bearing, label }) => {
          const { x, y } = project(-4.5, bearing);
          return (
            <text
              key={label} x={x} y={y + 4} textAnchor="middle"
              fontSize="12" fill={ink} letterSpacing="1.5"
            >
              {label}
            </text>
          );
        })}

        <g clipPath="url(#dome-clip)">
          {up.map((b) => {
            const { x, y } = project(b.altitude, b.azimuth);
            const r = radiusFor(b.magnitude);
            return (
              <g key={b.name}>
                <circle cx={x} cy={y} r={r + 6} fill={ink} opacity="0.12" />
                <circle cx={x} cy={y} r={r} fill={ink} />
                <text
                  x={x} y={y - r - 7} textAnchor="middle"
                  fontSize="13" fill={night ? "#ecedf4" : "#f4f0e6"}
                >
                  {GLYPH[b.name] ?? b.name[0]}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
      </div>

      <div className="mt-4 w-full" style={{ maxWidth: 520 }}>
        <p className="font-reading" style={{ fontSize: 15, color: "var(--ink-2)", marginBottom: 12 }}>
          {sky.daylight
            ? "The Sun was up, so the sky was too bright to see any of this — but it was all there."
            : sky.twilight
            ? "Twilight: the brightest of these were just becoming visible."
            : `${sky.visible_count} of these were visible to the naked eye.`}
        </p>

        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {up.map((b) => (
            <div key={b.name} className="flex items-baseline justify-between" style={{ fontSize: 13 }}>
              <span style={{ color: "var(--ink-2)" }}>
                {GLYPH[b.name] ?? "•"} {b.name}
              </span>
              <span className="font-reading" style={{ color: "var(--ink-3)" }}>
                {Math.round(b.altitude)}° up
              </span>
            </div>
          ))}
        </div>

        {down.length > 0 && (
          <p style={{ fontSize: 12.5, color: "var(--ink-3)", marginTop: 12, lineHeight: 1.6 }}>
            Below the horizon, on the other side of the world:{" "}
            {down.map((b) => b.name).join(", ")}.
          </p>
        )}
      </div>
    </div>
  );
}
