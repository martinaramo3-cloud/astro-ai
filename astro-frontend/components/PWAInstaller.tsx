"use client";

import { useEffect, useState } from "react";

type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

const DISMISS_KEY = "astraea-install-dismissed";

function isStandalone() {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    // iOS Safari reports installed apps here rather than via display-mode.
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

function isIOS() {
  if (typeof navigator === "undefined") return false;
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}

export default function PWAInstaller() {
  const [deferred, setDeferred] = useState<InstallPromptEvent | null>(null);
  const [showIOSHint, setShowIOSHint] = useState(false);

  // Register the service worker.
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    const register = () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        /* offline support is optional — never block the app on it */
      });
    };
    if (document.readyState === "complete") register();
    else {
      window.addEventListener("load", register);
      return () => window.removeEventListener("load", register);
    }
  }, []);

  // Android/desktop: capture the browser's own install prompt.
  useEffect(() => {
    const onPrompt = (e: Event) => {
      e.preventDefault();
      if (localStorage.getItem(DISMISS_KEY)) return;
      setDeferred(e as InstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  // iOS has no install event, so surface the Share-sheet steps instead.
  useEffect(() => {
    if (isStandalone() || !isIOS()) return;
    if (localStorage.getItem(DISMISS_KEY)) return;
    const timer = setTimeout(() => setShowIOSHint(true), 2500);
    return () => clearTimeout(timer);
  }, []);

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, "1");
    setDeferred(null);
    setShowIOSHint(false);
  };

  const install = async () => {
    if (!deferred) return;
    await deferred.prompt();
    await deferred.userChoice;
    setDeferred(null);
  };

  if (isStandalone()) return null;
  if (!deferred && !showIOSHint) return null;

  return (
    <div className="safe-bottom fixed inset-x-3 bottom-3 z-[70] mx-auto max-w-md">
      <div className="glass flex items-center gap-3 rounded-2xl p-3 shadow-2xl">
        <img src="/icon-192.png" alt="" className="h-11 w-11 rounded-xl" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-white">Add Astraea to your home screen</p>
          <p className="mt-0.5 text-xs leading-5 text-white/55">
            {showIOSHint ? (
              <>
                Tap <span aria-hidden="true">&#8593;</span> Share, then{" "}
                <span className="whitespace-nowrap">&ldquo;Add to Home Screen&rdquo;</span>
              </>
            ) : (
              "Open it like an app, full screen."
            )}
          </p>
        </div>
        {deferred && (
          <button
            onClick={install}
            className="shrink-0 rounded-full bg-gradient-to-r from-violet-200 to-white px-4 py-2 text-sm font-semibold text-slate-950"
          >
            Install
          </button>
        )}
        <button
          onClick={dismiss}
          aria-label="Dismiss"
          className="shrink-0 rounded-full border border-white/15 px-2.5 py-2 text-xs text-white/60"
        >
          &#10005;
        </button>
      </div>
    </div>
  );
}
