"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Stats {
  projects_total: number;
  projects_ready: number;
  projects_partial_ready: number;
  projects_failed: number;
  projects_running: number;
  estimated_spend_usd: number;
  credits_per_usd: number;
  credits_spent: number;
  credits_granted: number;
  outstanding_credits: number;
  credits_spent_usd_value: number;
  gross_margin_usd: number;
  admin_bypass_projects: number;
  client_billed_projects: number;
  client_simulation_projects: number;
  client_zero_credit_projects: number;
  released_zero_credit_projects: number;
  zero_credit_status: string;
  topups_pending: number;
  topups_paid_usd: number;
  users_total: number;
  user_activity_events: number;
  providers_active: number;
  models_active: number;
}

function StatCard({ label, value, tone = "accent" }: {
  label: string;
  value: string | number;
  tone?: "accent" | "green" | "red" | "zinc";
}) {
  const color = tone === "green" ? "text-green-400"
    : tone === "red" ? "text-red-400"
      : tone === "zinc" ? "text-zinc-200" : "text-amber-400";
  return (
    <div className="card p-4">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-sm text-zinc-500">{label}</div>
    </div>
  );
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Stats>("/api/admin/dashboard")
      .then(setStats).catch((e) => setError(String(e)));
  }, []);

  if (error) return <p className="text-red-400">{error}</p>;
  if (!stats) return <p className="text-zinc-500">Загрузка…</p>;

  const fmt = (n: number) => n.toLocaleString("ru-RU");
  const money = (n: number) =>
    `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Founder dashboard</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Экономика, пользователи, активность и состояние AI-пула.
          </p>
        </div>
        <Link href="/admin/topups" className="btn-ghost px-4 py-2 text-sm">
          Top-ups →
        </Link>
      </div>

      <section>
        <p className="kicker mb-3">Экономика credits</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label={`${stats.credits_per_usd} credits = $1`} value={fmt(stats.outstanding_credits)} />
          <StatCard label="credits spent пользователями" value={fmt(stats.credits_spent)} />
          <StatCard label="USD value списанных credits" value={money(stats.credits_spent_usd_value)} tone="green" />
          <StatCard label="gross margin estimate" value={money(stats.gross_margin_usd)} tone={stats.gross_margin_usd >= 0 ? "green" : "red"} />
        </div>
      </section>

      <section>
        <p className="kicker mb-3">Почему списано 0</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="client-billed projects" value={stats.client_billed_projects} tone="green" />
          <StatCard label="admin bypass projects" value={stats.admin_bypass_projects} tone={stats.admin_bypass_projects ? "accent" : "zinc"} />
          <StatCard label="client simulation tests" value={stats.client_simulation_projects} />
          <StatCard label="released client 0 credits" value={stats.released_zero_credit_projects} tone={stats.released_zero_credit_projects ? "red" : "zinc"} />
        </div>
        <p className={stats.zero_credit_status === "billing_error" ? "mt-3 text-sm text-red-300" : "mt-3 text-sm text-zinc-500"}>
          {stats.zero_credit_status === "billing_error"
            ? "Есть релизованный клиентский проект с 0 credits: это billing anomaly, нужно проверить."
            : stats.zero_credit_status === "admin_bypass_only"
              ? "0 credits объясняется founder/admin bypass, клиентские списания не сломаны."
              : "Критичных zero-credit billing anomalies не найдено."}
        </p>
      </section>

      <section>
        <p className="kicker mb-3">Пополнения</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard label="pending top-ups" value={stats.topups_pending} tone={stats.topups_pending ? "accent" : "zinc"} />
          <StatCard label="paid top-ups USD" value={money(stats.topups_paid_usd)} tone="green" />
          <StatCard label="credits granted total" value={fmt(stats.credits_granted)} />
        </div>
      </section>

      <section>
        <p className="kicker mb-3">Операции</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="проектов всего" value={stats.projects_total} />
          <StatCard label="ready" value={stats.projects_ready} tone="green" />
          <StatCard label="partial ready" value={stats.projects_partial_ready} />
          <StatCard label="failed" value={stats.projects_failed} tone={stats.projects_failed ? "red" : "zinc"} />
          <StatCard label="в работе" value={stats.projects_running} />
          <StatCard label="estimated model spend" value={money(stats.estimated_spend_usd)} />
          <StatCard label="пользователей" value={stats.users_total} />
          <StatCard label="user activity events" value={stats.user_activity_events} />
          <StatCard label="active providers" value={stats.providers_active} />
          <StatCard label="active models" value={stats.models_active} />
        </div>
      </section>
    </div>
  );
}
