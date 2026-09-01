"use client";

/**
 * "Zodi" — an oversized Z beside widely tracked lowercase.
 *
 * The Z's own letter-spacing supplies the gap before "odi". What used to open
 * that gap too wide was an additional text-indent on "odi", which pushed the
 * whole word right rather than centring it. Centring is handled instead by a
 * negative margin cancelling the trailing space after the final "i".
 */
export default function Wordmark({
  zSize,
  restSize,
  animate = false,
  className = "",
}: {
  zSize: number | string;
  restSize: number | string;
  animate?: boolean;
  className?: string;
}) {
  return (
    <div className={`flex items-baseline justify-center ${className}`}>
      <span
        className="font-display"
        style={{
          fontSize: typeof zSize === "number" ? `${zSize}px` : zSize,
          fontWeight: 300,
          lineHeight: 0.9,
          letterSpacing: "0.12em",
          color: "var(--gold-deep)",
        }}
      >
        Z
      </span>
      <span
        className={`font-display ${animate ? "zo-word" : ""}`}
        style={{
          fontSize: typeof restSize === "number" ? `${restSize}px` : restSize,
          fontWeight: 300,
          letterSpacing: animate ? undefined : "0.4em",
          // Same for the trailing "i", so the pair sits optically centred.
          marginRight: "-0.4em",
          color: "var(--ink)",
        }}
      >
        odi
      </span>
    </div>
  );
}
