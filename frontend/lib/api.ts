export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

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
    await fetch(`${API_URL}/api/auth/logout`, {
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
  return `${API_URL}${path}`;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((init?.headers || {}) as Record<string, string>),
  };
  if (init?.body && !Object.keys(headers).some((key) => key.toLowerCase() === "content-type")) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers,
    cache: "no-store",
  });
  if ((res.status === 401 || res.status === 403) && typeof window !== "undefined") {
    const adminTarget = location.pathname.startsWith("/admin") || path.startsWith("/api/admin");
    const loginPath = adminTarget ? "/admin-login" : "/login";
    if (location.pathname !== loginPath) {
      clearAuth();
      location.href = loginPath;
    }
    throw new Error("401: требуется вход");
  }
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}
