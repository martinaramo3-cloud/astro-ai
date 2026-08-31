"use client";

/**
 * "Zodi" — an oversized Z beside widely tracked lowercase.
 *
 * The tracking on "odi" pushes the text right, so a matching text-indent
 * pulls it back and keeps the whole wordmark optically centred.
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
          textIndent: "0.4em",
          color: "var(--ink)",
        }}
      >
        odi
      </span>
    </div>
  );
}
