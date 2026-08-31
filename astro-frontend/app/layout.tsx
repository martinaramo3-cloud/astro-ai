import type { Metadata, Viewport } from "next";
import { Cormorant_Garamond, EB_Garamond, Jost } from "next/font/google";
import "./globals.css";
import PWAInstaller from "../components/PWAInstaller";
import ThemeProvider from "../components/ThemeProvider";

const cormorant = Cormorant_Garamond({
  variable: "--font-cormorant",
  subsets: ["latin"],
  weight: ["300", "400"],
});
const ebGaramond = EB_Garamond({
  variable: "--font-eb-garamond",
  subsets: ["latin"],
  weight: ["400", "500"],
  style: ["normal", "italic"],
});
const jost = Jost({
  variable: "--font-jost",
  subsets: ["latin"],
  weight: ["300", "400", "500"],
});

export const metadata: Metadata = {
  title: "Zodi",
  description: "The sky, in plain language. Astrology readings grounded in your real birth chart.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    title: "Zodi",
    statusBarStyle: "black-translucent",
  },
  icons: {
    icon: [
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
  },
  other: {
    // Next emits the modern `mobile-web-app-capable`; older iOS still needs
    // the Apple-prefixed tag to launch full screen from the home screen.
    "apple-mobile-web-app-capable": "yes",
  },
};

export const viewport: Viewport = {
  themeColor: "#FBF6EC",
  // Fill the screen behind the notch; safe-area padding keeps chrome clear.
  viewportFit: "cover",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-theme="day">
      <body
        className={`${cormorant.variable} ${ebGaramond.variable} ${jost.variable} antialiased`}
      >
        <ThemeProvider>
          <PWAInstaller />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
