"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { TERM_PATTERN, lookup, type GlossaryEntry } from "../lib/glossary";

/**
 * Zodi's answer, with the astrology words explained on a tap.
 *
 * Only the first mention of each term lights up. An answer that bolds "Venus"
 * four times reads as a textbook, and the point is to be quietly available,
 * not to teach. Everything else renders exactly as before.
 */

const MAX_TERMS = 6;    // past this it stops being a sentence and becomes a glossary
const MIN_GAP = 12;     // characters of plain text between two marked words

type Piece = { text: string; entry?: GlossaryEntry };
type Hit = { at: number; text: string; entry: GlossaryEntry };

function segment(text: string): Piece[] {
  // Every first mention, in reading order.
  const hits: Hit[] = [];
  const seen = new Set<string>();
  const pattern = new RegExp(TERM_PATTERN.source, "gi");   // fresh: lastIndex is stateful
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    const entry = lookup(match[0]);
    if (!entry || seen.has(entry.title)) continue;
    seen.add(entry.title);
    hits.push({ at: match.index, text: match[0], entry });
  }

  // Choose the obscure words over the familiar ones, and never mark two words
  // close enough to run together — "Moon squares Pluto" entirely in bold is a
  // blob, not emphasis, and the only word worth explaining there is "squares".
  const kept: Hit[] = [];
  for (const hit of [...hits].sort((a, b) => b.entry.weight - a.entry.weight || a.at - b.at)) {
    if (kept.length >= MAX_TERMS) break;
    const collides = kept.some(
      (k) => hit.at < k.at + k.text.length + MIN_GAP && k.at < hit.at + hit.text.length + MIN_GAP,
    );
    if (!collides) kept.push(hit);
  }
  kept.sort((a, b) => a.at - b.at);

  const pieces: Piece[] = [];
  let last = 0;
  for (const hit of kept) {
    if (hit.at > last) pieces.push({ text: text.slice(last, hit.at) });
    pieces.push({ text: hit.text, entry: hit.entry });
    last = hit.at + hit.text.length;
  }
  if (last < text.length) pieces.push({ text: text.slice(last) });
  return pieces;
}

export default function GlossaryText({ text }: { text: string }) {
  const [open, setOpen] = useState<
    { entry: GlossaryEntry; x: number; y: number; height: number } | null
  >(null);
  const cardRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (!cardRef.current?.contains(e.target as Node)) setOpen(null);
    };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(null); };
    // Deferred, or the click that opened this immediately closes it.
    const t = setTimeout(() => document.addEventListener("click", close), 0);
    document.addEventListener("keydown", key);
    return () => {
      clearTimeout(t);
      document.removeEventListener("click", close);
      document.removeEventListener("keydown", key);
    };
  }, [open]);

  // On a phone the card sits above the composer as a panel, rather than
  // floating next to the word. Chasing a popover around a fixed bar at the
  // bottom of a small screen produces exactly the clipped, half-visible box
  // this is meant to avoid; a panel is always fully readable.
  useLayoutEffect(() => {
    const el = cardRef.current;
    if (!el || !open) return;
    el.style.transform = "";

    if (window.innerWidth < 640) {
      const composer = document.querySelector("[data-composer]") as HTMLElement | null;
      const floor = composer ? window.innerHeight - composer.getBoundingClientRect().top : 96;
      el.style.left = "12px";
      el.style.right = "12px";
      el.style.width = "auto";
      el.style.top = "auto";
      el.style.bottom = `${floor + 12}px`;
      return;
    }

    // Roomier screens keep the popover beside the word.
    el.style.right = "auto";
    el.style.bottom = "auto";
    el.style.left = `${open.x}px`;
    el.style.top = `${open.y + 10}px`;

    const margin = 12;
    const r = el.getBoundingClientRect();
    let dx = 0;
    if (r.right > window.innerWidth - margin) dx = window.innerWidth - margin - r.right;
    if (r.left + dx < margin) dx = margin - r.left;
    if (dx) el.style.transform = `translateX(${dx}px)`;

    if (r.bottom > window.innerHeight - margin) {
      el.style.top = `${Math.max(margin, open.y - open.height - 10 - r.height)}px`;
    }
  }, [open]);

  const pieces = segment(text);

  return (
    <>
      {pieces.map((piece, i) =>
        piece.entry ? (
          // A span, not a button: Chrome forces a <button> to inline-block
          // whatever the stylesheet says, and an inline-block inside running
          // text can't share the line box of the words around it. A span flows
          // as text, so the role and key handling are supplied by hand.
          <span
            key={i}
            role="button"
            tabIndex={0}
            className="zo-term"
            aria-label={`What ${piece.entry.title} means`}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                (e.currentTarget as HTMLElement).click();
              }
            }}
            onClick={(e) => {
              e.stopPropagation();
              const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
              setOpen(
                open?.entry.title === piece.entry!.title
                  ? null
                  : { entry: piece.entry!, x: r.left, y: r.bottom, height: r.height },
              );
            }}
          >
            {piece.text}
          </span>
        ) : (
          <span key={i}>{piece.text}</span>
        ),
      )}

      {open && (
        <div
          ref={cardRef}
          className="zo-term-card"
          role="dialog"
          aria-label={open.entry.title}
          onClick={(e) => e.stopPropagation()}
        >
          <p className="zo-term-title">{open.entry.title}</p>
          <p className="zo-term-body">{open.entry.body}</p>
        </div>
      )}
    </>
  );
}
