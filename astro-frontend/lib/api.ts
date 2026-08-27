const PRODUCTION_BACKEND = "https://ai-horoscope-api.onrender.com";
const PUBLIC_API_BASE = process.env.NEXT_PUBLIC_API_URL?.trim();
const PRIVATE_BACKEND_URL = process.env.BACKEND_URL?.trim();

function normalize(url: string) {
  return url.replace(/\/$/, "");
}

function isLocal() {
  return typeof window !== "undefined" &&
    (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");
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

/* ─── Auth ─── */

const TOKEN_KEY = "token";
const USER_KEY = "user";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

/** Persist the signed-in user, keeping the token separate from profile data. */
export function saveAuth(payload: Record<string, unknown> & { token?: string }) {
  if (typeof window === "undefined") return;
  const { token, ...user } = payload;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

/**
 * fetch() against the API with the bearer token attached.
 *
 * A 401 means the session is gone (expired, logged out elsewhere, or predates
 * tokens entirely), so we clear local state and send the user to sign in.
 */
export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${getBrowserApiBase()}${path}`, { ...options, headers });

  if (response.status === 401 && typeof window !== "undefined") {
    clearAuth();
    if (window.location.pathname !== "/") window.location.href = "/";
  }
  return response;
}
