"use client";

export type Planet = {
  planet: string;
  degree: number; // absolute ecliptic longitude 0-360
  sign: string;
  degree_in_sign: number;
  house: number;
  retrograde?: boolean;
};
export type HouseCusp = { house: number; degree: number; sign: string };
export type Ascendant = { degree: number; sign: string };
export type Aspect = { planet_1: string; planet_2: string; aspect: string; orb: number };

export type NatalChart = {
  planet_positions: Planet[];
  houses: HouseCusp[];
  ascendant: Ascendant;
  aspects: Aspect[];
};

const PLANET_GLYPH: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
  Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
};
const SIGN_GLYPH: Record<string, string> = {
  Aries: "♈", Taurus: "♉", Gemini: "♊", Cancer: "♋", Leo: "♌", Virgo: "♍",
  Libra: "♎", Scorpio: "♏", Sagittarius: "♐", Capricorn: "♑", Aquarius: "♒", Pisces: "♓",
};
const SIGN_ORDER = [
  "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
  "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
];

// Harmonious vs. tense aspects get different colors.
const ASPECT_COLOR: Record<string, string> = {
  trine: "#6fd3c0", sextile: "#6fd3c0",
  square: "#e0857f", opposition: "#e0857f",
  conjunction: "#b9a6ff",
};

const CX = 200;
const CY = 200;

export default function ChartWheel({ chart }: { chart: NatalChart }) {
  const asc = chart.ascendant.degree;

  // Map an ecliptic longitude to a screen point. Ascendant sits at the left
  // (9 o'clock) and longitude increases counter-clockwise, as in a real chart.
  const point = (lon: number, r: number) => {
    const angle = (180 + (lon - asc)) * (Math.PI / 180);
    return { x: CX + r * Math.cos(angle), y: CY - r * Math.sin(angle) };
  };

  // Spread planets that sit very close together so glyphs don't overlap.
  const sorted = [...chart.planet_positions].sort((a, b) => a.degree - b.degree);
  const radii: Record<string, number> = {};
  let lastDeg = -999;
  let step = 0;
  for (const p of sorted) {
    const rel = ((p.degree - asc) % 360 + 360) % 360;
    if (rel - lastDeg < 9) step += 1;
    else step = 0;
    radii[p.planet] = 95 - step * 16;
    lastDeg = rel;
  }

  return (
    <svg viewBox="0 0 400 400" width="100%" style={{ maxWidth: 440 }} role="img" aria-label="Your natal chart wheel">
      <rect x="0" y="0" width="400" height="400" rx="24" fill="#070b1f" />

      {/* Rings */}
      {[192, 150, 118, 38].map((r) => (
        <circle key={r} cx={CX} cy={CY} r={r} fill="none" stroke="#5b4b9e" strokeWidth="1" opacity="0.5" />
      ))}

      {/* Sign segment dividers + glyphs */}
      {SIGN_ORDER.map((sign, i) => {
        const boundary = point(i * 30, 192);
        const inner = point(i * 30, 150);
        const glyph = point(i * 30 + 15, 171);
        return (
          <g key={sign}>
            <line x1={inner.x} y1={inner.y} x2={boundary.x} y2={boundary.y} stroke="#5b4b9e" strokeWidth="1" opacity="0.45" />
            <text x={glyph.x} y={glyph.y + 6} textAnchor="middle" fontSize="17" fill="#d9b961">{SIGN_GLYPH[sign]}</text>
          </g>
        );
      })}

      {/* House cusps + numbers */}
      {chart.houses.map((h, i) => {
        const outer = point(h.degree, 118);
        const inner = point(h.degree, 38);
        const next = chart.houses[(i + 1) % 12];
        const midLon = h.degree + (((next.degree - h.degree) % 360 + 360) % 360) / 2;
        const num = point(midLon, 132);
        const emphasize = h.house === 1 || h.house === 10; // Asc & MC
        return (
          <g key={h.house}>
            <line
              x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y}
              stroke={emphasize ? "#d9b961" : "#3c3470"}
              strokeWidth={emphasize ? 1.4 : 1}
              opacity={emphasize ? 0.8 : 0.6}
            />
            <text x={num.x} y={num.y + 3} textAnchor="middle" fontSize="9" fill="#8a7fc0">{h.house}</text>
          </g>
        );
      })}

      {/* Aspect lines (drawn behind planets) */}
      {chart.aspects.map((a, i) => {
        const p1 = chart.planet_positions.find((p) => p.planet === a.planet_1);
        const p2 = chart.planet_positions.find((p) => p.planet === a.planet_2);
        if (!p1 || !p2) return null;
        const from = point(p1.degree, radii[p1.planet] ?? 95);
        const to = point(p2.degree, radii[p2.planet] ?? 95);
        return (
          <line
            key={i}
            x1={from.x} y1={from.y} x2={to.x} y2={to.y}
            stroke={ASPECT_COLOR[a.aspect] ?? "#7c6bd6"}
            strokeWidth="0.8"
            opacity="0.4"
          />
        );
      })}

      {/* Planets */}
      {chart.planet_positions.map((p) => {
        const pos = point(p.degree, radii[p.planet] ?? 95);
        return (
          <g key={p.planet}>
            <circle cx={pos.x} cy={pos.y} r="13" fill="#12173a" stroke="#7c6bd6" strokeWidth="1" />
            <text x={pos.x} y={pos.y + 5} textAnchor="middle" fontSize="14" fill="#f3eeff">{PLANET_GLYPH[p.planet] ?? p.planet[0]}</text>
            {p.retrograde && (
              <text x={pos.x + 11} y={pos.y - 8} textAnchor="middle" fontSize="7" fill="#d9b961">℞</text>
            )}
          </g>
        );
      })}

      {/* Ascendant marker */}
      <text x={point(asc, 205).x} y={point(asc, 205).y + 3} textAnchor="middle" fontSize="9" fill="#d9b961">ASC</text>
    </svg>
  );
}
