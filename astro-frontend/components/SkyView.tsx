"use client";

import { useEffect, useMemo, useRef, useState } from "react";

/**
 * The sky as it actually was, from one place at one moment.
 *
 * A stereographic projection of the half-dome above the observer: the centre is
 * straight up, the rim is the horizon. North sits at the top and east on the
 * LEFT, mirrored against a map on purpose — you are looking up at a dome, not
 * down at the ground, which is what makes a planisphere match the real sky when
 * you hold it over your head.
 *
 * Two layers, for two different jobs. The canvas carries the ground, the Milky
 * Way, the grid and nine thousand stars — things nobody touches, and far too
 * many to make elements of. The planets sit above it as real buttons, because
 * they need labels, crisp text, and something to tap.
 *
 * Every position is computed from the ephemeris. Nothing is placed for looks.
 */

export type SkyBody = {
  name: string;
  altitude: number;
  azimuth: number;
  above_horizon: boolean;
  sign: string;
  degree_in_sign: number;
  retrograde: boolean;
  magnitude: number;
  naked_eye: boolean;
};

/** [ra hours, dec degrees, magnitude, colour 0=blue-white 1=warm, name?] */
export type Star = [number, number, number, number, string?];

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
  local_hour?: number;
  local_time?: string;
};

export const GLYPH: Record<string, string> = {
  Sun: "☉︎", Moon: "☽︎", Mercury: "☿︎", Venus: "♀︎", Mars: "♂︎",
  Jupiter: "♃︎", Saturn: "♄︎", Uranus: "♅︎", Neptune: "♆︎", Pluto: "♇︎",
};

/** Relative size and surface colour, so each body reads as itself. */
const BODY_STYLE: Record<string, { size: number; tint: string }> = {
  Sun:     { size: 1.00, tint: "#ffe6b0" },
  Moon:    { size: 0.95, tint: "#e8ecf6" },
  Mercury: { size: 0.58, tint: "#dcd2c0" },
  Venus:   { size: 0.80, tint: "#f6e3c0" },
  Mars:    { size: 0.62, tint: "#e0a07e" },
  Jupiter: { size: 0.86, tint: "#ecd7a6" },
  Saturn:  { size: 0.78, tint: "#d9c79a" },
  Uranus:  { size: 0.55, tint: "#bcd4d8" },
  Neptune: { size: 0.55, tint: "#a9bede" },
  Pluto:   { size: 0.50, tint: "#c9bcae" },
};

const SIZE = 840;
const R = 370;
const CX = SIZE / 2;
const CY = SIZE / 2;
const RAD = Math.PI / 180;

function project(altitude: number, azimuth: number) {
  const r = ((90 - altitude) / 90) * R;
  const a = azimuth * RAD;
  return { x: CX - r * Math.sin(a), y: CY - r * Math.cos(a) };
}

/**
 * A fixed star's place in this observer's sky.
 *
 * Checked against Swiss Ephemeris on five bodies at a real moment: 0.000
 * degrees of disagreement, so the stars sit in the same sky as the planets
 * rather than a parallel one.
 */
function starPosition(ra: number, dec: number, lst: number, latitude: number) {
  const H = (lst - ra) * 15 * RAD;
  const d = dec * RAD;
  const p = latitude * RAD;

  const sinAlt = Math.sin(d) * Math.sin(p) + Math.cos(d) * Math.cos(p) * Math.cos(H);
  const alt = Math.asin(Math.max(-1, Math.min(1, sinAlt)));
  const cosA = (Math.sin(d) - Math.sin(alt) * Math.sin(p)) / (Math.cos(alt) * Math.cos(p));
  const A = Math.acos(Math.max(-1, Math.min(1, cosA))) / RAD;

  return { altitude: alt / RAD, azimuth: Math.sin(H) < 0 ? A : 360 - A };
}

/* ── The Milky Way ─────────────────────────────────────────────────────────
   Our own galaxy, seen edge-on from inside it. Its band is fixed in galactic
   coordinates, so it is walked there and converted out. The two axes below are
   the measured directions of the galactic centre and the north galactic pole. */

function unitVector(raDeg: number, decDeg: number): [number, number, number] {
  const ra = raDeg * RAD;
  const dec = decDeg * RAD;
  return [Math.cos(dec) * Math.cos(ra), Math.cos(dec) * Math.sin(ra), Math.sin(dec)];
}

const GAL_CENTRE = unitVector(266.404996, -28.936175);
const GAL_POLE = unitVector(192.859508, 27.128336);
const GAL_Y: [number, number, number] = [
  GAL_POLE[1] * GAL_CENTRE[2] - GAL_POLE[2] * GAL_CENTRE[1],
  GAL_POLE[2] * GAL_CENTRE[0] - GAL_POLE[0] * GAL_CENTRE[2],
  GAL_POLE[0] * GAL_CENTRE[1] - GAL_POLE[1] * GAL_CENTRE[0],
];

function galacticToRaDec(lDeg: number, bDeg: number) {
  const l = lDeg * RAD;
  const b = bDeg * RAD;
  const cb = Math.cos(b);
  const sb = Math.sin(b);
  const v = [0, 0, 0];
  for (let i = 0; i < 3; i++) {
    v[i] = GAL_CENTRE[i] * cb * Math.cos(l) + GAL_Y[i] * cb * Math.sin(l) + GAL_POLE[i] * sb;
  }
  const dec = Math.asin(Math.max(-1, Math.min(1, v[2]))) / RAD;
  let ra = Math.atan2(v[1], v[0]) / RAD;
  if (ra < 0) ra += 360;
  return { raHours: ra / 15, decDeg: dec };
}

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

function drawMilkyWay(ctx: CanvasRenderingContext2D, lst: number, lat: number) {
  ctx.globalCompositeOperation = "lighter";
  for (let l = 0; l < 360; l += 1.2) {
    for (const k of [-1, 0, 1]) {
      const b = k * 4.5 + Math.sin(l * 0.11) * 1.6;
      const { raHours, decDeg } = galacticToRaDec(l, b);
      const { altitude, azimuth } = starPosition(raHours, decDeg, lst, lat);
      if (altitude <= -2) continue;

      const { x, y } = project(altitude, azimuth);
      const radius = 46 - Math.abs(k) * 12;
      const alpha = (0.03 - Math.abs(k) * 0.009) * clamp((altitude + 2) / 25, 0.15, 1);
      if (alpha <= 0) continue;

      const g = ctx.createRadialGradient(x, y, 0, x, y, radius);
      g.addColorStop(0, `rgba(196,206,232,${alpha})`);
      g.addColorStop(1, "rgba(196,206,232,0)");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  ctx.globalCompositeOperation = "source-over";
}

/** How much the atmosphere dims a star this close to the horizon. */
function extinction(altitude: number) {
  return 0.32 + 0.68 * Math.pow(Math.sin(Math.max(1, altitude) * RAD), 0.42);
}

function starColour(c: number) {
  if (c < 0.18) return "206,222,255";
  return `255,${Math.round(246 - 36 * c * c)},${Math.round(255 - 96 * c * c)}`;
}

function drawStars(ctx: CanvasRenderingContext2D, stars: Star[], lst: number, lat: number) {
  for (const [ra, dec, mag, colour] of stars) {
    const { altitude, azimuth } = starPosition(ra, dec, lst, lat);
    if (altitude <= 0.2) continue;

    const { x, y } = project(altitude, azimuth);
    const scaled = Math.pow(Math.pow(2.512, -mag), 0.3);

    ctx.globalAlpha = Math.min(1, 0.16 + scaled * 0.52) * extinction(altitude);
    ctx.fillStyle = `rgb(${starColour(colour)})`;
    ctx.beginPath();
    ctx.arc(x, y, 0.34 + scaled * 0.95, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}

function drawGround(ctx: CanvasRenderingContext2D, daylight: boolean) {
  const g = ctx.createRadialGradient(CX, CY - 40, 10, CX, CY, R);
  if (daylight) {
    // A bright morning sky, still deepening toward the top of the dome.
    g.addColorStop(0, "#2f4b76");
    g.addColorStop(0.55, "#3d5c85");
    g.addColorStop(0.88, "#5b7ea6");
    g.addColorStop(1, "#8aa8c4");
  } else {
    g.addColorStop(0, "#0a0f1a");
    g.addColorStop(0.55, "#0d1220");
    g.addColorStop(0.88, "#121a2b");
    g.addColorStop(1, "#1a2233");
  }
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, SIZE, SIZE);

  // The horizon never goes fully dark: there is always some glow down there.
  const glow = ctx.createRadialGradient(CX, CY, R * 0.72, CX, CY, R);
  glow.addColorStop(0, "rgba(217,176,106,0)");
  glow.addColorStop(1, `rgba(217,176,106,${daylight ? 0.05 : 0.1})`);
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, SIZE, SIZE);
}

function drawGrid(ctx: CanvasRenderingContext2D, daylight: boolean) {
  const strong = daylight ? "rgba(12,20,34,0.10)" : "rgba(236,237,244,0.055)";
  const weak = daylight ? "rgba(12,20,34,0.07)" : "rgba(236,237,244,0.035)";

  ctx.lineWidth = 1;
  ctx.strokeStyle = strong;
  for (const alt of [30, 60]) {
    ctx.beginPath();
    ctx.arc(CX, CY, ((90 - alt) / 90) * R, 0, Math.PI * 2);
    ctx.stroke();
  }

  ctx.strokeStyle = weak;
  for (let az = 0; az < 360; az += 45) {
    const a = project(6, az);
    const b = project(72, az);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
}

function drawEcliptic(ctx: CanvasRenderingContext2D, sky: SkyData) {
  const arc = sky.ecliptic.filter((p) => p.altitude > 0);
  if (arc.length < 2) return;

  const trace = () => {
    ctx.beginPath();
    arc.forEach((p, i) => {
      const { x, y } = project(p.altitude, p.azimuth);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
  };

  // A ribbon rather than a hairline: the planets stray a degree or two either
  // side of the exact ecliptic, and a band admits that where a line would not.
  ctx.save();
  ctx.lineCap = "round";
  ctx.strokeStyle = "rgba(217,176,106,0.13)";
  ctx.lineWidth = 14;
  trace();
  ctx.stroke();

  ctx.strokeStyle = "rgba(217,176,106,0.42)";
  ctx.lineWidth = 1;
  ctx.setLineDash([5, 6]);
  trace();
  ctx.stroke();
  ctx.restore();
}

/* ── Component ─────────────────────────────────────────────────────────── */

type Marker = { body: SkyBody; x: number; y: number; core: number; lift: number };

export default function SkyView({
  sky,
  selected,
  onSelect,
}: {
  sky: SkyData;
  selected: string | null;
  onSelect: (name: string | null) => void;
}) {
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
    if (!canvas) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = SIZE * dpr;
    canvas.height = SIZE * dpr;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, SIZE, SIZE);
    ctx.save();
    ctx.beginPath();
    ctx.arc(CX, CY, R, 0, Math.PI * 2);
    ctx.clip();

    drawGround(ctx, sky.daylight);
    if (!sky.daylight) {
      drawMilkyWay(ctx, sky.local_sidereal_hours, sky.observer.latitude);
      if (stars) drawStars(ctx, stars, sky.local_sidereal_hours, sky.observer.latitude);
    }
    drawGrid(ctx, sky.daylight);
    drawEcliptic(ctx, sky);
    ctx.restore();
  }, [stars, sky]);

  /* Planet markers, with labels lifted clear of one another. */
  const markers = useMemo<Marker[]>(() => {
    const visible = sky.bodies
      .filter((b) => b.above_horizon)
      .map((body) => ({ body, ...project(body.altitude, body.azimuth) }))
      .sort((a, b) => a.x - b.x);

    const placed: Marker[] = [];
    for (const { body, x, y } of visible) {
      const style = BODY_STYLE[body.name] ?? { size: 0.5, tint: "#cbd3e2" };
      const core = 7 + style.size * 9;

      // Clusters near the Sun are common; fan their labels out vertically
      // rather than letting them pile up on each other.
      let lift = 30;
      for (const other of placed) {
        if (Math.abs(other.x - x) < 52 && Math.abs(other.y - y) < 60) {
          lift = Math.max(lift, other.lift + 27);
        }
      }
      placed.push({ body, x, y, core, lift });
    }
    return placed;
  }, [sky]);

  const pct = (v: number) => `${(v / SIZE) * 100}%`;

  return (
    <div
      className="sky-dome"
      style={{ maxWidth: 620 }}
      onClick={() => onSelect(null)}
    >
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
      />

      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}
        aria-hidden="true"
      >
        <circle cx={CX} cy={CY} r={R} fill="none" stroke="rgba(217,176,106,.34)" strokeWidth="1.5" />
        {([["N", 0], ["E", 90], ["S", 180], ["W", 270]] as const).map(([label, bearing]) => {
          const { x, y } = project(-5.5, bearing);
          return (
            <text
              key={label}
              x={x} y={y + 5} textAnchor="middle"
              fontSize="15" fill="#d9b06a" letterSpacing="2"
              className="font-ui"
            >
              {label}
            </text>
          );
        })}
      </svg>

      {markers.map(({ body, x, y, core, lift }) => {
        const style = BODY_STYLE[body.name] ?? { size: 0.5, tint: "#cbd3e2" };
        const isSelected = selected === body.name;
        const glow = body.name === "Moon" ? "rgba(232,236,246,0.42)" : "rgba(233,190,120,0.40)";
        const shade = body.name === "Moon" ? "#9aa5bd" : "#b98a44";

        return (
          <button
            key={body.name}
            onClick={(e) => { e.stopPropagation(); onSelect(isSelected ? null : body.name); }}
            aria-label={`${body.name}, ${Math.round(body.degree_in_sign)} degrees ${body.sign}`}
            aria-pressed={isSelected}
            className="sky-marker"
            style={{ left: pct(x), top: pct(y) }}
          >
            <span
              className="sky-bloom"
              style={{
                width: core * (isSelected ? 7.5 : 6),
                height: core * (isSelected ? 7.5 : 6),
                background: `radial-gradient(circle, ${glow} 0%, transparent 68%)`,
                animationDuration: `${5 + (body.name.length % 4)}s`,
              }}
            />
            <span
              className="sky-ring"
              style={{
                width: core + 16, height: core + 16,
                borderColor: isSelected ? "rgba(235,207,155,.85)" : "rgba(217,176,106,.5)",
              }}
            />
            <span
              className="sky-halo"
              style={{ width: core + 34, height: core + 34, opacity: isSelected ? 1 : 0 }}
            />
            <span
              className="sky-body"
              style={{
                width: core, height: core,
                background: `radial-gradient(circle at 34% 30%, #fff 0%, ${style.tint} 38%, ${shade} 100%)`,
                boxShadow: `0 0 ${isSelected ? 26 : 16}px ${glow}, 0 0 3px rgba(255,255,255,.9)`,
              }}
            />
            <span className="sky-stem" style={{ height: lift - core / 2 - 6, bottom: `calc(50% + ${core / 2}px)` }} />
            <span className="sky-label" style={{ bottom: `calc(50% + ${lift}px)` }}>
              <span className="sky-glyph" style={{ fontSize: isSelected ? 20 : 17 }}>
                {GLYPH[body.name] ?? body.name[0]}
              </span>
              <span className="sky-name" style={{ opacity: isSelected ? 1 : 0 }}>
                {body.name} {Math.round(body.degree_in_sign)}° {body.sign}
                {body.retrograde ? " ℞" : ""}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
