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
        <div className="relative min-h-screen">
          <header className="sticky top-0 z-40 border-b border-white/10 bg-slate-950/50 backdrop-blur-xl">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
              <Link href="/" className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/10 text-sm font-semibold">✦</div>
                <div>
                  <p className="text-[11px] uppercase tracking-[0.32em] text-white/55">Premium cosmic insight</p>
                  <p className="text-lg font-semibold text-white">Astraea Studio</p>
                </div>
              </Link>
              <nav className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 p-1 text-sm text-white/80">
                {navItems.map((item) => (
                  <Link key={item.href} href={item.href} className="rounded-full px-4 py-2 transition hover:bg-white/10 hover:text-white">
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
