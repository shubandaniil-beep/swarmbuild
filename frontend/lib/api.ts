const CONFIGURED_API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
type ApiInit = RequestInit & { timeoutMs?: number };

export const API_URL = CONFIGURED_API_URL || "http://127.0.0.1:8000";

function apiUrl(): string {
  if (CONFIGURED_API_URL) return CONFIGURED_API_URL;
  if (typeof window === "undefined") return API_URL;
  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

export function getToken(): string {
  // Auth is cookie-only. Keep this helper for old call sites, but never read
  // bearer tokens from browser storage.
  return "";
}

export function getUser(): {
  id: string;
  email: string;
  role: string;
  token_balance?: number;
  demo_generations_remaining?: number;
  credits_per_usd?: number;
  credit_value_usd?: number;
} | null {
  if (typeof window === "undefined") return null;
  try {
    return JSON.parse(localStorage.getItem("sb_user") || "null");
  } catch {
    return null;
  }
}

export function setAuth(_token: string, user: object) {
  localStorage.removeItem("sb_token");
  localStorage.setItem("sb_user", JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem("sb_token");
  localStorage.removeItem("sb_user");
}

export async function logout() {
  const token = getToken();
  try {
    await fetch(`${apiUrl()}/api/auth/logout`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
  } finally {
    clearAuth();
  }
}

export function downloadUrl(path: string): string {
  return `${apiUrl()}${path}`;
}

async function errorDetail(res: Response): Promise<string> {
  const body = await res.text();
  if (!body) return res.statusText || "request failed";
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed.detail === "string") return parsed.detail;
  } catch {
    // Fall through to the raw body for non-JSON responses.
  }
  return body;
}

function shouldRedirectOnAuthFailure(path: string): boolean {
  const pathname = path.split("?")[0];
  return ![
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/admin-login",
    "/api/auth/admin-autofill",
  ].includes(pathname);
}

export async function api<T>(path: string, init?: ApiInit): Promise<T> {
  const { timeoutMs = 45000, ...requestInit } = init ?? {};
  const controller = typeof AbortController !== "undefined" && !requestInit.signal
    ? new AbortController()
    : null;
  const timeout = controller
    ? window.setTimeout(() => controller.abort(), timeoutMs)
    : null;
  const token = getToken();
  const headers: Record<string, string> = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((requestInit.headers || {}) as Record<string, string>),
  };
  if (requestInit.body && !Object.keys(headers).some((key) => key.toLowerCase() === "content-type")) {
    headers["Content-Type"] = "application/json";
  }
  try {
    const res = await fetch(`${apiUrl()}${path}`, {
      ...requestInit,
      credentials: "include",
      headers,
      cache: "no-store",
      signal: requestInit.signal ?? controller?.signal,
    });
    if ((res.status === 401 || res.status === 403)
        && typeof window !== "undefined"
        && shouldRedirectOnAuthFailure(path)) {
      const adminTarget = location.pathname.startsWith("/admin") || path.startsWith("/api/admin");
      const loginPath = adminTarget ? "/admin-login" : "/login";
      if (location.pathname !== loginPath) {
        clearAuth();
        location.href = loginPath;
      }
      throw new Error("401: требуется вход");
    }
    if (!res.ok) throw new Error(`${res.status}: ${await errorDetail(res)}`);
    return res.json();
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("timeout: сервер не ответил вовремя");
    }
    throw err;
  } finally {
    if (timeout !== null) window.clearTimeout(timeout);
  }
}
