const PRODUCTION_BACKEND = "https://ai-horoscope-api.onrender.com";
const PUBLIC_API_BASE = process.env.NEXT_PUBLIC_API_URL?.trim();
const PRIVATE_BACKEND_URL = process.env.BACKEND_URL?.trim();

function normalize(url: string) {
  return url.replace(/\/$/, "");
}

function isLocal() {
  return typeof window !== "undefined" && window.location.hostname === "localhost";
}

export function getBrowserApiBase() {
  if (PUBLIC_API_BASE && !PUBLIC_API_BASE.startsWith("/")) {
    return normalize(PUBLIC_API_BASE);
  }
  if (isLocal()) return "/api";
  return PRODUCTION_BACKEND;
}

export function getServerBackendBase() {
  if (PRIVATE_BACKEND_URL) return normalize(PRIVATE_BACKEND_URL);
  if (PUBLIC_API_BASE && !PUBLIC_API_BASE.startsWith("/")) {
    return normalize(PUBLIC_API_BASE);
  }
  return PRODUCTION_BACKEND;
}
