/**
 * An answer, drawn as something worth posting.
 *
 * People already screenshot readings and put them on Stories. A screenshot
 * carries the app's chrome, the composer, someone's own name in the corner —
 * and none of the brand. This draws the answer properly instead: Zoli's
 * colours, Zoli's typeface, the mark at the foot, sized 1080x1920 so it drops
 * straight into a Story.
 *
 * Deliberately only the question and the answer. Not the birth details, not
 * the saved person's name, not anything from the rest of the conversation.
 */

const W = 1080;
const H = 1920;

type Theme = { ground: string; ink: string; ink2: string; gold: string };

const DAY: Theme = { ground: "#fbf6ec", ink: "#241f19", ink2: "#5c5346", gold: "#9a7128" };
const NIGHT: Theme = { ground: "#101422", ink: "#ece7dc", ink2: "#b9b2a4", gold: "#d8ac5e" };

/** Break text into lines that fit, at a given font. */
function wrap(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = [];
  for (const paragraph of text.split("\n")) {
    if (!paragraph.trim()) { lines.push(""); continue; }
    let line = "";
    for (const word of paragraph.split(/\s+/)) {
      const candidate = line ? `${line} ${word}` : word;
      if (ctx.measureText(candidate).width > maxWidth && line) {
        lines.push(line);
        line = word;
      } else {
        line = candidate;
      }
    }
    if (line) lines.push(line);
  }
  return lines;
}

export async function drawShareCard(
  question: string,
  answer: string,
  night: boolean,
): Promise<Blob | null> {
  // The card is the brand, so it must not be drawn in a fallback face.
  try { await document.fonts?.ready; } catch { /* proceed regardless */ }

  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  const t = night ? NIGHT : DAY;
  ctx.fillStyle = t.ground;
  ctx.fillRect(0, 0, W, H);

  // A soft glow behind the text, the same gesture as the app's own sky.
  const glow = ctx.createRadialGradient(W / 2, H * 0.18, 0, W / 2, H * 0.18, W * 0.9);
  glow.addColorStop(0, night ? "rgba(216,172,94,0.10)" : "rgba(201,154,69,0.13)");
  glow.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, W, H);

  const margin = 96;
  const maxWidth = W - margin * 2;

  // The question, small and quiet above the answer.
  ctx.fillStyle = t.gold;
  ctx.font = '500 26px Jost, system-ui, sans-serif';
  ctx.letterSpacing = "5px";
  const qLines = wrap(ctx, question.toUpperCase(), maxWidth).slice(0, 3);
  ctx.letterSpacing = "0px";

  // Fit the answer: step the size down until it fits the space available.
  let size = 46;
  let lines: string[] = [];
  let lineHeight = 0;
  const available = H * 0.62;
  for (; size >= 26; size -= 2) {
    ctx.font = `400 ${size}px "EB Garamond", Georgia, serif`;
    lines = wrap(ctx, answer.trim(), maxWidth);
    lineHeight = size * 1.5;
    if (lines.length * lineHeight <= available) break;
  }

  const qHeight = qLines.length * 40;
  const blockHeight = qHeight + 46 + lines.length * lineHeight;
  // Centred, with the composition sitting a little above middle: Instagram
  // lays its own controls over the top and bottom of a Story.
  let y = Math.max(H * 0.18, (H - blockHeight) / 2 - 20);

  ctx.font = '500 26px Jost, system-ui, sans-serif';
  ctx.letterSpacing = "5px";
  ctx.fillStyle = t.gold;
  for (const line of qLines) {
    ctx.fillText(line, margin, y);
    y += 40;
  }
  ctx.letterSpacing = "0px";
  y += 46;

  ctx.fillStyle = t.ink;
  ctx.font = `400 ${size}px "EB Garamond", Georgia, serif`;
  for (const line of lines) {
    if (!line) { y += lineHeight * 0.5; continue; }
    ctx.fillText(line, margin, y);
    y += lineHeight;
  }

  // The signature: a small sun-moon mark and the name, at the foot.
  // Clear of the Story UI, which covers roughly the bottom eighth.
  const footY = H - 250;
  ctx.strokeStyle = t.gold;
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.arc(margin + 20, footY - 10, 20, 0, Math.PI * 2);
  ctx.stroke();
  ctx.fillStyle = t.gold;
  ctx.beginPath();
  ctx.arc(margin + 27, footY - 10, 14, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = t.ink2;
  ctx.font = '400 30px Jost, system-ui, sans-serif';
  ctx.letterSpacing = "9px";
  ctx.fillText("ZOLI", margin + 60, footY);
  ctx.letterSpacing = "0px";

  return new Promise((resolve) => canvas.toBlob((b) => resolve(b), "image/png", 0.95));
}

/**
 * Hand the card to the phone's share sheet, or fall back to saving it.
 * Returns a short note for the caller to show, or "" when nothing needs saying.
 */
export async function shareAnswer(
  question: string,
  answer: string,
  night: boolean,
): Promise<string> {
  const blob = await drawShareCard(question, answer, night);
  if (!blob) return "Couldn't draw the card.";

  const file = new File([blob], "zoli.png", { type: "image/png" });
  const nav = navigator as Navigator & { canShare?: (d: unknown) => boolean };

  if (nav.share && nav.canShare?.({ files: [file] })) {
    try {
      await nav.share({ files: [file] });
      return "";
    } catch {
      return "";   // they closed the sheet; not a failure
    }
  }

  // No share sheet — save it, which is what a desktop browser can do.
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "zoli.png";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return "Saved as an image.";
}
