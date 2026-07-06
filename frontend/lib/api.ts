/**
 * Единый API-клиент.
 *
 * Аутентификация — только HttpOnly-cookie (`sb_session`), поэтому клиент
 * не хранит и не передаёт токены. В localStorage лежит только кэш профиля
 * для мгновенного рендера шапки; источником истины остаётся /api/auth/me.
 */

const CONFIGURED_API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

export const API_URL = CONFIGURED_API_URL || "http://127.0.0.1:8000";

type ApiInit = RequestInit & { timeoutMs?: number };

export interface SessionUser {
  id: string;
  email: string;
  role: string;
  token_balance?: number;
  demo_generations_remaining?: number;
  credits_per_usd?: number;
  credit_value_usd?: number;
}

const USER_CACHE_KEY = "sb_user";

function apiUrl(): string {
  if (CONFIGURED_API_URL) return CONFIGURED_API_URL;
  if (typeof window === "undefined") return API_URL;
  // dev-режим: фронт и бэк на одном хосте, разные порты
  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

/** Кэш профиля — только для отображения (имя, роль, баланс в шапке). */
export function getCachedUser(): SessionUser | null {
  if (typeof window === "undefined") return null;
  try {
    return JSON.parse(localStorage.getItem(USER_CACHE_KEY) || "null");
  } catch {
    return null;
  }
}

export function cacheUser(user: SessionUser | Partial<SessionUser>) {
  const merged = { ...getCachedUser(), ...user };
  localStorage.setItem(USER_CACHE_KEY, JSON.stringify(merged));
}

export function clearAuth() {
  localStorage.removeItem(USER_CACHE_KEY);
}

export async function logout() {
  try {
    await fetch(`${apiUrl()}/api/auth/logout`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
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
    // не-JSON ответ — вернём тело как есть
  }
  return body;
}

function shouldRedirectOnAuthFailure(path: string): boolean {
  const pathname = path.split("?")[0];
  return ![
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/admin-login",
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
  const headers: Record<string, string> = {
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
