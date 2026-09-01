"use client";

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

export type SkyData = {
  place?: string;
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

const CARDINALS = [
  { bearing: 0, label: "N" },
  { bearing: 90, label: "E" },
  { bearing: 180, label: "S" },
  { bearing: 270, label: "W" },
];

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
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        width="100%"
        style={{ maxWidth: 520 }}
        role="img"
        aria-label={`The sky over ${sky.place ?? "your birthplace"}, looking up`}
      >
        <defs>
          <radialGradient id="dome" cx="50%" cy="42%" r="72%">
            <stop offset="0%" stopColor={sky.daylight ? "#2c3f63" : "#131c30"} />
            <stop offset="100%" stopColor={ground} />
          </radialGradient>
          {/* A body sitting on the horizon has its glow half outside the dome,
              which reads as a rendering fault rather than as something setting. */}
          <clipPath id="dome-clip">
            <circle cx={CX} cy={CY} r={R} />
          </clipPath>
        </defs>

        <circle cx={CX} cy={CY} r={R} fill="url(#dome)" />

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
