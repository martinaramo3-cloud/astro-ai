"use client";

import Link from "next/link";
import ZodiMark from "./ZodiMark";
import Wordmark from "./Wordmark";
import { useTheme } from "./ThemeProvider";

/** Shared shell for the terms and privacy pages. */
export default function LegalPage({
  title,
  updated,
  children,
}: {
  title: string;
  updated: string;
  children: React.ReactNode;
}) {
  const { theme } = useTheme();

  return (
    <main
      className="min-h-screen px-6 py-14"
      style={{ background: "var(--sky)" }}
    >
      <div className="mx-auto" style={{ maxWidth: 680 }}>
        <Link href="/" className="mb-10 flex items-center justify-center gap-2">
          <ZodiMark size={38} night={theme === "night"} />
          <Wordmark zSize={34} restSize={20} />
        </Link>

        <p className="micro-label" style={{ letterSpacing: "0.24em" }}>
          Last updated {updated}
        </p>
        <h1
          className="font-display mt-2"
          style={{ fontSize: 42, fontWeight: 300, lineHeight: 1.1 }}
        >
          {title}
        </h1>

        <div className="legal-body font-reading mt-8">{children}</div>

        <p className="mt-14 text-center">
          <Link
            href="/"
            className="micro-label"
            style={{ letterSpacing: "0.2em", color: "var(--gold-deep)" }}
          >
            &larr; Back to Zodi
          </Link>
        </p>
      </div>

      <style jsx global>{`
        .legal-body {
          font-size: 17px;
          line-height: 1.8;
          color: var(--ink-2);
        }
        .legal-body h2 {
          font-family: var(--font-cormorant), Georgia, serif;
          font-size: 26px;
          font-weight: 400;
          color: var(--ink);
          margin: 40px 0 12px;
          line-height: 1.25;
        }
        .legal-body h3 {
          font-size: 15px;
          letter-spacing: 0.14em;
          text-transform: uppercase;
          font-family: var(--font-jost), sans-serif;
          font-weight: 400;
          color: var(--ink-3);
          margin: 28px 0 8px;
        }
        .legal-body p {
          margin: 0 0 16px;
          text-wrap: pretty;
        }
        .legal-body ul {
          margin: 0 0 16px;
          padding-left: 20px;
        }
        .legal-body li {
          margin-bottom: 8px;
        }
        .legal-body strong {
          color: var(--ink);
          font-weight: 500;
        }
        .legal-body a {
          color: var(--gold-deep);
          text-underline-offset: 3px;
        }
        .legal-body .callout {
          background: var(--gold-soft);
          border-radius: 16px;
          padding: 18px 20px;
          margin: 0 0 20px;
        }
        .legal-body .callout p:last-child {
          margin-bottom: 0;
        }
        .legal-body .todo {
          background: var(--sunk);
          border-left: 3px solid var(--gold);
          border-radius: 8px;
          padding: 12px 16px;
          margin: 0 0 20px;
          font-family: var(--font-jost), sans-serif;
          font-size: 14px;
          color: var(--ink-3);
        }
      `}</style>
    </main>
  );
}
