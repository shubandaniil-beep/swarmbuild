"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, cacheUser, type SessionUser } from "@/lib/api";
import { getDeviceFingerprint } from "@/lib/fingerprint";
import { LogoMark } from "@/components/ui";

export default function Login() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const fingerprint = mode === "register" ? await getDeviceFingerprint() : undefined;
      const res = await api<{ user: SessionUser }>(`/api/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify({ email, password, fingerprint }),
      });
      cacheUser(res.user);
      router.push("/projects");
    } catch (err) {
      setError(String(err).replace(/^Error:\s*/, ""));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative pt-14 -mx-6 px-6">
      <div className="absolute inset-0 grid-bg pointer-events-none" />
      <div className="relative max-w-sm mx-auto">
        <div className="text-center mb-8 animate-fade-in-up">
          <LogoMark size="text-2xl" />
          <p className="mt-3 text-sm text-zinc-500">
            Зарегистрируйтесь и запустите один минимальный trial-проект из стартовых credits.
          </p>
        </div>
        <div className="card p-7 animate-fade-in-up delay-1">
          <div className="flex rounded-xl bg-zinc-900/80 p-1 mb-6 text-sm">
            {(["login", "register"] as const).map((m) => (
              <button key={m} type="button" onClick={() => setMode(m)}
                      className={`flex-1 py-2 rounded-lg transition-all ${
                        mode === m
                          ? "bg-amber-400 text-zinc-950 font-semibold"
                          : "text-zinc-400 hover:text-white"}`}>
                {m === "login" ? "Вход" : "Регистрация"}
              </button>
            ))}
          </div>
          <div className="space-y-4">
            <input
              suppressHydrationWarning
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  submit();
                }
              }}
              required
              placeholder="email"
              className="input"
            />
            <input
              suppressHydrationWarning
              name="password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
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
              placeholder="пароль (мин. 8 символов)"
              className="input"
            />
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <button type="button" disabled={busy} onClick={submit} className="btn-primary w-full py-2.5">
              {busy ? "Подключаюсь…" : mode === "login" ? "Войти" : "Создать аккаунт"}
            </button>
          </div>
        </div>
        <p className="text-center text-xs text-zinc-600 mt-5 animate-fade-in-up delay-2">
          100 credits = $1. Trial тратит стартовые credits и показывает реальную сборку.
        </p>
      </div>
    </div>
  );
}
