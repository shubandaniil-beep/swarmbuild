"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, cacheUser, type SessionUser } from "@/lib/api";

export default function AdminLogin() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const res = await api<{ user: SessionUser }>("/api/auth/admin-login", {
        method: "POST",
        timeoutMs: 12000,
        body: JSON.stringify({ email, password }),
      });
      cacheUser(res.user);
      router.push("/admin/providers");
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/, "") || "Неверный founder email или пароль.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto pt-16">
      <div className="mb-6">
        <p className="kicker">Founder access</p>
        <h1 className="text-2xl font-bold mt-2">Вход в админку</h1>
        <p className="text-sm text-zinc-500 mt-2">
          Только CEO/founder аккаунт может управлять провайдерами, моделями и API-ключами.
        </p>
      </div>

      <div className="space-y-4">
        <input
          suppressHydrationWarning
          name="email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              submit();
            }
          }}
          required
          placeholder="founder email"
          className="input"
        />
        <input
          suppressHydrationWarning
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              submit();
            }
          }}
          required
          minLength={8}
          placeholder="founder password"
          className="input"
        />
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <button
          type="button"
          disabled={busy}
          onClick={submit}
          className="btn-primary w-full py-2.5"
        >
          {busy ? "Проверяю…" : "Войти как founder"}
        </button>
      </div>
    </div>
  );
}
