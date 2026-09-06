"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Zodi read aloud, using the device's own voice.
 *
 * Free, instant, and nothing leaves the phone. iOS has two habits worth
 * knowing: the voice list arrives asynchronously, and Safari cuts an utterance
 * off after roughly fifteen seconds — so a long answer is spoken as a queue of
 * sentences rather than one block.
 */

/** Apple's better English voices, best first; everything else falls back. */
const PREFERRED = ["samantha", "serena", "karen", "moira", "tessa", "zoe", "google uk english female"];

function pickVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  const english = voices.filter((v) => /^en\b/i.test(v.lang));
  if (!english.length) return voices[0] ?? null;
  for (const name of PREFERRED) {
    const match = english.find((v) => v.name.toLowerCase().includes(name));
    if (match) return match;
  }
  // A local voice sounds better and doesn't need the network.
  return english.find((v) => v.localService) ?? english[0];
}

/** Split into speakable chunks, so Safari's cut-off never lands mid-thought. */
function toChunks(text: string): string[] {
  const sentences = text
    .replace(/\s+/g, " ")
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);

  const chunks: string[] = [];
  let current = "";
  for (const sentence of sentences) {
    if (current && (current + " " + sentence).length > 180) {
      chunks.push(current);
      current = sentence;
    } else {
      current = current ? `${current} ${sentence}` : sentence;
    }
  }
  if (current) chunks.push(current);
  return chunks;
}

export function useSpeechOutput() {
  const [supported, setSupported] = useState(false);
  const [speakingId, setSpeakingId] = useState<number | null>(null);
  const voiceRef = useRef<SpeechSynthesisVoice | null>(null);
  const cancelledRef = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    setSupported(true);

    const load = () => {
      const voices = window.speechSynthesis.getVoices();
      if (voices.length) voiceRef.current = pickVoice(voices);
    };
    load();                                    // often empty on the first call
    window.speechSynthesis.addEventListener("voiceschanged", load);
    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", load);
      window.speechSynthesis.cancel();
    };
  }, []);

  const stop = useCallback(() => {
    cancelledRef.current = true;
    window.speechSynthesis?.cancel();
    setSpeakingId(null);
  }, []);

  const speak = useCallback(
    (id: number, text: string) => {
      const synth = window.speechSynthesis;
      if (!synth) return;

      if (speakingId === id) {
        stop();
        return;
      }

      // Always cancel first: a queue left over from a previous answer will
      // otherwise play underneath this one, and on iOS a stale queue can wedge
      // synthesis entirely.
      synth.cancel();
      cancelledRef.current = false;
      setSpeakingId(id);

      const chunks = toChunks(text);
      chunks.forEach((chunk, index) => {
        const utterance = new SpeechSynthesisUtterance(chunk);
        if (voiceRef.current) utterance.voice = voiceRef.current;
        utterance.rate = 0.97;   // a shade under default: this is meant to land, not rush
        utterance.pitch = 1;
        if (index === chunks.length - 1) {
          utterance.onend = () => {
            if (!cancelledRef.current) setSpeakingId(null);
          };
        }
        utterance.onerror = () => setSpeakingId(null);
        synth.speak(utterance);
      });
    },
    [speakingId, stop],
  );

  return { supported, speakingId, speak, stop };
}
