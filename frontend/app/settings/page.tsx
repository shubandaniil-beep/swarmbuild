"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, cacheUser, getCachedUser } from "@/lib/api";

interface BillingPack {
  id: string;
  label: string;
  credits: number;
  amount_usd: number;
  best_for: string;
  display: string;
}

interface BillingSummary {
  token_balance: number;
  demo_generations_remaining: number;
  credits_per_usd: number;
  credit_value_usd: number;
  packs: BillingPack[];
  pay_code: string;
  payment_bot_url: string;
  payment_note: string;
}

interface Topup {
  id: string;
  credits: number;
  amount_usd: number;
  provider: string;
  status: string;
  payment_url: string;
  created_at: string | null;
}

export default function Settings() {
  const [role, setRole] = useState<string | null>(null);
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [topups, setTopups] = useState<Topup[]>([]);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  async function load() {
    const [s, t] = await Promise.all([
      api<BillingSummary>("/api/billing/summary"),
      api<Topup[]>("/api/billing/topups"),
    ]);
    setSummary(s);
    setTopups(t);
    cacheUser({
      token_balance: s.token_balance,
      demo_generations_remaining: s.demo_generations_remaining,
      credits_per_usd: s.credits_per_usd,
    });
  }

  useEffect(() => {
    setRole(getCachedUser()?.role ?? null);
    load().catch((e) => setError(String(e)));
  }, []);

  async function copyCode() {
    if (!summary?.pay_code) return;
    try {
      await navigator.clipboard.writeText(summary.pay_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard может быть недоступен — код всё равно виден на экране */
    }
  }

  if (error && !summary) return <p className="text-red-400">{error}</p>;
  if (!summary) return <p className="text-zinc-500">Загрузка…</p>;

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="kicker mb-2">Баланс</p>
          <h1 className="text-2xl font-bold">Credits и пополнение</h1>
          <p className="mt-2 text-sm text-zinc-500">
            {summary.credits_per_usd} credits = $1. Баланс нужен для запуска проектов и доработок.
          </p>
        </div>
        {role === "admin" && (
          <Link href="/admin" className="btn-ghost px-4 py-2 text-sm">админ-панель →</Link>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card p-5">
          <div className="text-3xl font-bold text-amber-400">
            {summary.token_balance.toLocaleString("ru-RU")}
          </div>
          <div className="text-sm text-zinc-500">credits на балансе</div>
        </div>
        <div className="card p-5">
          <div className="text-3xl font-bold text-amber-400">
            ${(summary.token_balance / summary.credits_per_usd).toLocaleString("ru-RU")}
          </div>
          <div className="text-sm text-zinc-500">примерный $-эквивалент</div>
        </div>
        <div className="card p-5">
          <div className="text-3xl font-bold text-amber-400">
            {summary.demo_generations_remaining}
          </div>
          <div className="text-sm text-zinc-500">trial-запусков осталось</div>
        </div>
      </div>

      <section className="card p-5">
        <p className="kicker mb-2">Ваш код оплаты</p>
        <p className="text-sm text-zinc-500 mb-3">
          Отправьте этот код боту оплаты один раз, чтобы привязать Telegram к аккаунту.
          После этого оплаты звёздами будут начисляться в credits автоматически. Код
          постоянный — второй раз вводить не нужно.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-mono text-3xl tracking-[0.35em] text-amber-400 select-all">
            {summary.pay_code || "——————"}
          </span>
          <button onClick={copyCode} className="btn-ghost px-4 py-2 text-sm">
            {copied ? "Скопировано ✓" : "Скопировать"}
          </button>
          {summary.payment_bot_url && (
            <a href={summary.payment_bot_url} target="_blank" rel="noreferrer"
               className="btn-primary px-4 py-2 text-sm">
              Открыть бота оплаты →
            </a>
          )}
        </div>
        {error && summary && <p className="mt-3 text-sm text-red-400">{error}</p>}
      </section>

      <section>
        <p className="kicker mb-3">Пакеты пополнения</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {summary.packs.map((pack) => (
            <div key={pack.id} className="card p-4">
              <span className="block text-sm font-semibold">{pack.label}</span>
              <span className="mt-2 block text-2xl font-bold text-amber-400">
                {pack.credits.toLocaleString("ru-RU")}
              </span>
              <span className="block text-xs text-zinc-500">credits = ${pack.amount_usd}</span>
              <span className="mt-3 block text-xs text-zinc-500">{pack.best_for}</span>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-zinc-500">{summary.payment_note}</p>
      </section>

      <section>
        <p className="kicker mb-3">История пополнений</p>
        {topups.length === 0 ? (
          <p className="text-sm text-zinc-500">Заявок пока нет.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-zinc-500 border-b border-zinc-800">
                  <th className="py-2">Дата</th>
                  <th>Credits</th>
                  <th>Сумма</th>
                  <th>Провайдер</th>
                  <th>Статус</th>
                  <th>Оплата</th>
                </tr>
              </thead>
              <tbody>
                {topups.map((t) => (
                  <tr key={t.id} className="border-b border-zinc-900">
                    <td className="py-2 text-zinc-500">
                      {t.created_at ? new Date(t.created_at).toLocaleString("ru-RU") : "—"}
                    </td>
                    <td>{t.credits.toLocaleString("ru-RU")}</td>
                    <td>${t.amount_usd}</td>
                    <td>{t.provider}</td>
                    <td className={t.status === "paid" ? "text-green-400" : "text-amber-300"}>
                      {t.status}
                    </td>
                    <td>
                      {t.payment_url ? (
                        <a href={t.payment_url} className="text-amber-300">открыть</a>
                      ) : (
                        <span className="text-zinc-600">ручная проверка</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
