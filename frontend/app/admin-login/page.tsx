"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setAuth } from "@/lib/api";

export default function AdminLogin() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [autofillBusy, setAutofillBusy] = useState(false);

  async function autofillFounder() {
    setAutofillBusy(true);
    setError("");
    try {
      const res = await api<{ email: string; password: string }>("/api/auth/admin-autofill");
      setEmail(res.email);
      setPassword(res.password);
    } catch {
      setError("Автозаполнение founder доступно только в локальной dev-среде.");
    } finally {
      setAutofillBusy(false);
    }
  }

  async function submit() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const res = await api<{ user: object }>("/api/auth/admin-login", {
        method: "POST",
        timeoutMs: 12000,
        body: JSON.stringify({ email, password }),
      });
      setAuth("", res.user);
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
        <p className="text-xs uppercase tracking-[0.2em] text-indigo-300">Founder access</p>
        <h1 className="text-2xl font-bold mt-2">Вход в админку</h1>
        <p className="text-sm text-zinc-500 mt-2">
          Только CEO/founder аккаунт может управлять провайдерами, моделями и API-ключами.
        </p>
      </div>

      <div className="space-y-4">
        <button
          type="button"
          disabled={busy || autofillBusy}
          onClick={autofillFounder}
          className="w-full border border-zinc-700 rounded-lg py-2 text-sm text-zinc-300 hover:border-indigo-300 hover:text-white disabled:opacity-50"
        >
          {autofillBusy ? "Заполняю founder…" : "Автозаполнить founder"}
        </button>
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
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2"
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
          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2"
        />
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <button
          type="button"
          disabled={busy}
          onClick={submit}
          className="w-full bg-indigo-400 text-zinc-950 font-semibold py-2 rounded-lg hover:bg-indigo-300 disabled:opacity-50"
        >
          {busy ? "Проверяю…" : "Войти как founder"}
        </button>
      </div>
    </div>
  );
}
