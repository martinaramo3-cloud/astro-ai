import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Astraea Studio",
  description: "Premium AI astrology readings, chart insights, and a modern cosmic experience.",
};

const navItems = [
  { href: "/", label: "Home" },
  { href: "/content", label: "Method" },
  { href: "/chat", label: "Chat" },
];

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} starfield antialiased`}>
        {/* Ambient background orbs */}
        <div className="orb orb-1" aria-hidden="true" />
        <div className="orb orb-2" aria-hidden="true" />
        <div className="orb orb-3" aria-hidden="true" />
        {/* Floating crescent moon */}
        <div className="moon-decor" aria-hidden="true" />

        <div className="relative min-h-screen">
          <header className="sticky top-0 z-40 border-b border-white/[0.07] bg-slate-950/60 backdrop-blur-2xl">
            <div className="mx-auto flex max-w-6xl items-center justify-between gap-2 px-4 py-3 lg:px-6 lg:py-4">
              <Link href="/" className="flex items-center gap-2 lg:gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full border border-white/15 bg-white/10 text-sm font-semibold lg:h-10 lg:w-10">✦</div>
                <div>
                  <p className="hidden text-[11px] uppercase tracking-[0.32em] text-white/55 sm:block">Premium cosmic insight</p>
                  <p className="text-base font-semibold text-white lg:text-lg">Astraea Studio</p>
                </div>
              </Link>
              <nav className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1 text-sm text-white/80 lg:gap-2">
                {navItems.map((item) => (
                  <Link key={item.href} href={item.href} className="rounded-full px-3 py-2 transition hover:bg-white/10 hover:text-white lg:px-4">
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
