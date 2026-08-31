"use client";

/**
 * The Zodi mark: a rayed sun/moon medallion.
 *
 * Everything is sized as a percentage of the box, so one `size` prop drives
 * every usage (24px inline label up to 268px on the splash). Spinning it is
 * the app's entire loading state — there is no separate spinner.
 */

const RAY_COUNT = 16;
const RAY_STEP_DEG = 360 / RAY_COUNT;

export default function ZodiMark({
  size = 96,
  night = false,
  spin = false,
  className = "",
}: {
  size?: number;
  night?: boolean;
  spin?: boolean;
  className?: string;
}) {
  return (
    <div
      className={`relative shrink-0 ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {/* Halo. The centring lives on the wrapper because the animation drives
          `transform` itself and would otherwise overwrite it. */}
      <div className="absolute inset-0 grid place-items-center">
        <div
          className="zm-glow rounded-full"
          style={{
            width: size * 0.78,
            height: size * 0.78,
            filter: "blur(10px)",
            background: night
              ? "radial-gradient(circle, rgba(142,134,214,.55), rgba(94,124,196,.28) 45%, transparent 70%)"
              : "radial-gradient(circle, rgba(228,186,110,.65), rgba(240,206,140,.30) 45%, transparent 70%)",
          }}
        />
      </div>

      {/* Orbiting stars, night only */}
      <div
        className={`absolute ${spin ? "zm-orbit-fast" : "zm-orbit-rest"}`}
        style={{
          inset: "-4%",
          opacity: night ? 0.9 : 0,
          transition: "opacity 900ms ease",
        }}
      >
        {[0, 72, 144, 216, 288].map((angle, i) => (
          <span
            key={angle}
            className="absolute left-1/2 top-1/2 rounded-full"
            style={{
              width: i % 2 ? 2 : 3,
              height: i % 2 ? 2 : 3,
              background: "#C7D0EA",
              transform: `rotate(${angle}deg) translateY(-${size * 0.52}px)`,
            }}
          />
        ))}
      </div>

      {/* Rays — 16 spokes, alternating long and short */}
      <div
        className={`absolute inset-0 ${spin ? "zm-spin-fast" : "zm-spin-rest"}`}
        style={{ color: "var(--mark-ray)", opacity: "var(--mark-ray-opacity)" }}
      >
        <div className="zm-breathe absolute inset-0">
          {Array.from({ length: RAY_COUNT }).map((_, i) => {
            const long = i % 2 === 0;
            return (
              <span
                key={i}
                className="zm-shimmer absolute left-1/2 top-1/2 block rounded-sm"
                style={{
                  width: long ? 2 : 1.5,
                  height: long ? "47%" : "33%",
                  background: "linear-gradient(to top, currentColor, transparent)",
                  transformOrigin: "50% 100%",
                  transform: `translate(-50%, -100%) rotate(${i * RAY_STEP_DEG}deg)`,
                  animationDelay: `${-0.4 * i}s`,
                }}
              />
            );
          })}
        </div>
      </div>

      {/* Medallion. The artwork's baked cream background has been knocked out
          to transparency, so it composites onto either theme directly — the
          soft-light tint the handoff described was only needed to disguise
          that cream, and would now dull the gold. */}
      <div
        className="absolute left-1/2 top-1/2 overflow-hidden rounded-full"
        style={{
          width: "52%",
          height: "52%",
          transform: "translate(-50%, -50%)",
          backgroundImage: "url(/zodi-logo.png)",
          backgroundSize: "306%",
          backgroundPosition: "50.2% 45.4%",
        }}
      />
    </div>
  );
}
