"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Tariff {
  id: string;
  name: string;
  price_usd: number;
  description: string;
  swarm_size: number;
  max_phases: number;
  model_budget_usd: number;
  compute_budget_usd: number;
  credit_grant: number;
  bonus_percent: number;
  enabled: boolean;
  allowed_project_modes: string[];
  allowed_outputs: string[];
  priority: number;
}

export default function AdminTariffs() {
  const [rows, setRows] = useState<Tariff[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", price_usd: 50, swarm_size: 4,
                                     max_phases: 8, credit_grant: 5000,
                                     bonus_percent: 0, description: "" });

  const load = () =>
    api<Tariff[]>("/api/admin/tariffs").then(setRows).catch((e) => setError(String(e)));
  useEffect(() => { load(); }, []);

  async function toggle(t: Tariff) {
    try {
      await api(`/api/admin/tariffs/${t.id}`, {
        method: "PUT", body: JSON.stringify({ ...t, enabled: !t.enabled }),
      });
      load();
    } catch (e) { setError(String(e)); }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/api/admin/tariffs", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          model_budget_usd: form.price_usd * 0.5,
          compute_budget_usd: form.price_usd * 0.1,
          allowed_project_modes: ["code", "document", "business", "mixed", "auto"],
        }),
      });
      setForm({ ...form, name: "" });
      load();
    } catch (err) { setError(String(err)); }
  }

  const input = "bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm";

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Тарифы</h1>
      {error && <p className="text-red-400 text-sm">{error}</p>}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-zinc-500 border-b border-zinc-800">
            <th className="py-2">Название</th><th>Цена</th><th>Credits</th><th>Bonus</th>
            <th>Рой</th><th>Фаз</th><th>Model $</th><th>Вкл</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => (
            <tr key={t.id} className={`border-b border-zinc-900 ${t.enabled ? "" : "opacity-50"}`}>
              <td className="py-2">{t.name}
                <span className="block text-xs text-zinc-500">{t.description}</span>
              </td>
              <td>${t.price_usd}</td>
              <td className="text-indigo-300">{t.credit_grant.toLocaleString("ru-RU")}</td>
              <td>{t.bonus_percent}%</td>
              <td>{t.swarm_size}</td>
              <td>{t.max_phases}</td>
              <td>${t.model_budget_usd}</td>
              <td>
                <button onClick={() => toggle(t)}
                        className={t.enabled ? "text-green-400" : "text-zinc-500"}>
                  {t.enabled ? "on" : "off"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <form onSubmit={create} className="border border-zinc-800 rounded-xl p-4 space-y-3">
        <h2 className="font-semibold">Добавить тариф</h2>
        <div className="flex flex-wrap gap-2">
          <input required placeholder="Название" className={input}
                 value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input type="number" min="1" className={input + " w-24"} value={form.price_usd}
                 onChange={(e) => setForm({ ...form, price_usd: +e.target.value })} />
          <input type="number" min="2" max="12" className={input + " w-20"}
                 title="swarm size" value={form.swarm_size}
                 onChange={(e) => setForm({ ...form, swarm_size: +e.target.value })} />
          <input type="number" min="3" max="9" className={input + " w-20"}
                 title="max phases" value={form.max_phases}
                 onChange={(e) => setForm({ ...form, max_phases: +e.target.value })} />
          <input type="number" min="100" className={input + " w-28"}
                 title="credit grant" value={form.credit_grant}
                 onChange={(e) => setForm({ ...form, credit_grant: +e.target.value })} />
          <input type="number" min="0" max="100" className={input + " w-24"}
                 title="bonus percent" value={form.bonus_percent}
                 onChange={(e) => setForm({ ...form, bonus_percent: +e.target.value })} />
          <input placeholder="Описание" className={input + " flex-1"}
                 value={form.description}
                 onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <button className="bg-indigo-400 text-zinc-950 font-semibold px-4 py-2 rounded-lg text-sm hover:bg-indigo-300">
            Добавить
          </button>
        </div>
      </form>
    </div>
  );
}
