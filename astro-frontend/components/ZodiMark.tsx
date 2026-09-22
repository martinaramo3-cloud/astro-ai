"use client";

/**
 * The Zoli mark: a rayed sun/moon medallion.
 *
 * Two stacked copies of one cut-out PNG. The outer copy — rays, flames, outer
 * stars — turns; the inner copy is masked to the medallion rim and never does,
 * so the Z and the moon's face stay upright however long it spins. The masks
 * are exact complements, measured to this artwork's rim: change one radius and
 * you must change the other, or you get a seam or a doubled image.
 *
 * Nothing sits behind it. A glow, a plate, a drop-shadow — each was tried, and
 * each reads as a grey disc on the night ground. The artwork carries its own
 * highlights and needs no night variant.
 *
 * Everything is sized from the box, so one `size` prop drives every usage (24px
 * inline in the transcript up to 268px on the splash). Spinning it is the app's
 * entire loading state — there is no separate spinner.
 */
export default function ZodiMark({
  size = 96,
  spin = false,
  className = "",
  sizeFromCss = false,
}: {
  size?: number;
  /** true while a reply is generating — the rays speed up */
  spin?: boolean;
  className?: string;
  /** Let a stylesheet set the dimensions — inline sizing would win otherwise. */
  sizeFromCss?: boolean;
}) {

  return (
    <div
      className={`zodiMark shrink-0 ${className}`}
      data-spin={spin ? "true" : "false"}
      style={sizeFromCss ? undefined : { width: size, height: size }}
      aria-hidden="true"
    >
      <div className="zodiMark__layer zodiMark__rays" />
      <div className="zodiMark__layer zodiMark__core" />
    </div>
  );
}
