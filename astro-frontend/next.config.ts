import type { NextConfig } from "next";

const publicApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
const backendUrl = (process.env.BACKEND_URL || (publicApiUrl && !publicApiUrl.startsWith("/") ? publicApiUrl : undefined) || "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
