"use client";

import { useEffect, useRef, useState } from "react";

type Particle = {
  id: number;
  symbol: string;
  x: number;    // % from left of container
  bottom: number; // px from bottom
  delay: number;
  dur: number;
  sz: number;
  drift: number; // px horizontal drift
};

const LOVE_SYMBOLS    = ["♡", "♡", "✦", "✧", "♡", "✦", "♡"];
const MOON_SYMBOLS    = ["🌙", "✦", "✧", "✦", "⟡", "✧", "🌙"];
const CAREER_SYMBOLS  = ["✦", "⟡", "◈", "✧", "✦", "◈", "⟡"];
const DEFAULT_SYMBOLS = ["✦", "✧", "·", "⋆", "✦", "·", "✧"];

function pickSymbols(text: string): string[] {
  const t = text.toLowerCase();
  if (/love|heart|romance|partner|relationship|venus|attract|soulmate|intimacy|affection/.test(t))
    return LOVE_SYMBOLS;
  if (/moon|lunar|chart|natal|planet|saturn|mars|jupiter|rising|ascend|cosmos|celestial|astro/.test(t))
    return MOON_SYMBOLS;
  if (/career|work|success|money|wealth|ambition|achieve|purpose|calling/.test(t))
    return CAREER_SYMBOLS;
  return DEFAULT_SYMBOLS;
}

let nextId = 0;

function spawnParticles(text: string): Particle[] {
  const symbols = pickSymbols(text);
  const count = 7;
  return Array.from({ length: count }, (_, i) => ({
    id: nextId++,
    symbol: symbols[i % symbols.length],
    x: 10 + Math.random() * 80,
    bottom: 60 + Math.random() * 20,
    delay: i * 0.18,
    dur: 2.4 + Math.random() * 1.2,
    sz: 12 + Math.random() * 8,
    drift: (Math.random() - 0.5) * 40,
  }));
}

export default function FloatingParticles({ trigger }: { trigger: string | null }) {
  const [particles, setParticles] = useState<Particle[]>([]);
  const prevTrigger = useRef<string | null>(null);

  useEffect(() => {
    if (!trigger || trigger === prevTrigger.current) return;
    prevTrigger.current = trigger;

    const newParticles = spawnParticles(trigger);
    setParticles((prev) => [...prev, ...newParticles]);

    // Clean up after longest animation finishes
    const maxDur = Math.max(...newParticles.map((p) => p.delay + p.dur)) * 1000 + 200;
    const ids = new Set(newParticles.map((p) => p.id));
    setTimeout(() => {
      setParticles((prev) => prev.filter((p) => !ids.has(p.id)));
    }, maxDur);
  }, [trigger]);

  if (particles.length === 0) return null;

  return (
    <>
      {particles.map((p) => (
        <span
          key={p.id}
          className="particle"
          style={{
            left: `${p.x}%`,
            bottom: p.bottom,
            "--delay": `${p.delay}s`,
            "--dur": `${p.dur}s`,
            "--sz": `${p.sz}px`,
            "--drift": `${p.drift}px`,
          } as React.CSSProperties}
        >
          {p.symbol}
        </span>
      ))}
    </>
  );
}
