"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Dictation via the browser's own speech recognition.
 *
 * Runs in the browser, costs nothing per use, and never sends audio to us.
 *
 * Every failure used to be swallowed — `onerror` just stopped listening — so a
 * blocked microphone, a dropped network and an unsupported browser all looked
 * identical: a button that does nothing. Each one now says what happened and
 * what to do about it, because "it doesn't work" is not a bug report anyone can
 * act on, including me.
 */

const REASONS: Record<string, string> = {
  "not-allowed":
    "Microphone access is blocked. Allow it for this site in your browser settings, then tap again.",
  "service-not-allowed":
    "Your browser blocked dictation. Allow microphone access for this site and try again.",
  "audio-capture":
    "No microphone found. Check that one is connected and not in use by another app.",
  network:
    "Dictation needs a connection and couldn't reach the speech service. Check your network.",
  "no-speech": "I didn't catch anything — tap and speak a little closer to the mic.",
  aborted: "",   // the user stopped it; not an error worth reporting
};

export function useSpeechInput(onText: (text: string) => void) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");
  const recognitionRef = useRef<any>(null);

  // Keep the latest callback without restarting recognition on every render.
  const onTextRef = useRef(onText);
  useEffect(() => {
    onTextRef.current = onText;
  }, [onText]);

  useEffect(() => {
    const Recognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Recognition) return;

    setSupported(true);
    const recognition = new Recognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    // A locale the speech service doesn't serve fails outright, and most people
    // ask their questions in English regardless of what their phone is set to.
    const locale = navigator.language || "en-US";
    recognition.lang = /^en\b/i.test(locale) ? locale : "en-US";

    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results)
        .map((result: any) => result[0].transcript)
        .join(" ")
        .trim();
      if (transcript) {
        setError("");
        onTextRef.current(transcript);
      }
    };
    recognition.onerror = (event: any) => {
      const code = event?.error ?? "";
      setError(REASONS[code] ?? `Dictation stopped (${code || "unknown"}). Try again.`);
      setListening(false);
    };
    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    return () => {
      try {
        recognition.abort();
      } catch {
        /* already stopped */
      }
    };
  }, []);

  const toggle = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition) {
      setError("This browser can't do dictation. Chrome or Safari can — or just type it.");
      return;
    }

    if (listening) {
      recognition.stop();
      setListening(false);
      return;
    }

    setError("");
    try {
      recognition.start();
      setListening(true);
    } catch {
      // Starting twice throws; treat it as already running.
      setListening(true);
    }
  }, [listening]);

  return { supported, listening, error, toggle, dismissError: () => setError("") };
}
