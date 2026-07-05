"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface ModelRow {
  id: string;
  display_name: string;
  provider_id: string;
  model_name: string;
  enabled: boolean;
  cost_level: string;
  input_price_per_1m: number;
  output_price_per_1m: number;
  max_context_tokens: number;
  max_output_tokens: number;
  supports_tools: boolean;
  supports_json: boolean;
  supports_vision: boolean;
  supports_code: boolean;
  priority: number;
  notes: string;
}

interface Provider { id: string; name: string; provider_type: string; }

export default function AdminModels() {
  const [rows, setRows] = useState<ModelRow[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    display_name: "", provider_id: "", model_name: "",
    cost_level: "medium", input_price_per_1m: 1, output_price_per_1m: 2,
  });

  const load = () => Promise.all([
    api<ModelRow[]>("/api/admin/models").then(setRows),
    api<Provider[]>("/api/admin/providers").then(setProviders),
  ]).catch((e) => setError(String(e)));
  useEffect(() => { load(); }, []);

  async function toggle(m: ModelRow) {
    try {
      await api(`/api/admin/models/${m.id}`, {
        method: "PUT", body: JSON.stringify({ ...m, enabled: !m.enabled }),
      });
      load();
    } catch (e) { setError(String(e)); }
  }

  async function remove(id: string) {
    try {
      await api(`/api/admin/models/${id}`, { method: "DELETE" });
      load();
    } catch (e) { setError(String(e)); }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/api/admin/models", { method: "POST", body: JSON.stringify(form) });
      setForm({ ...form, display_name: "", model_name: "" });
      load();
    } catch (err) { setError(String(err)); }
  }

  const pname = (id: string) => providers.find((p) => p.id === id)?.name || "?";
  const input = "bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm";

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Model Registry</h1>
      <p className="text-sm text-zinc-500">
        Любая активная модель может получить любой мандат — lead / critic / builder /
        reviewer / repairer / judge / packager. Ротация обязательна.
      </p>
      {error && <p className="text-red-400 text-sm">{error}</p>}

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-zinc-500 border-b border-zinc-800">
            <th className="py-2">Модель</th><th>Провайдер</th><th>model_name</th>
            <th>Cost</th><th>$in/$out за 1M</th><th>Код</th><th>Вкл</th><th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((m) => (
            <tr key={m.id} className={`border-b border-zinc-900 ${m.enabled ? "" : "opacity-50"}`}>
              <td className="py-2">{m.display_name}</td>
              <td className="text-zinc-400">{pname(m.provider_id)}</td>
              <td className="text-zinc-400">{m.model_name}</td>
              <td>{m.cost_level}</td>
              <td>${m.input_price_per_1m} / ${m.output_price_per_1m}</td>
              <td>{m.supports_code ? "✅" : "—"}</td>
              <td>
                <button onClick={() => toggle(m)}
                        className={m.enabled ? "text-green-400" : "text-zinc-500"}>
                  {m.enabled ? "on" : "off"}
                </button>
              </td>
              <td>
                <button onClick={() => remove(m.id)}
                        className="text-zinc-500 hover:text-red-400">✕</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <form onSubmit={create} className="border border-zinc-800 rounded-xl p-4 space-y-3">
        <h2 className="font-semibold">Добавить модель</h2>
        <div className="flex flex-wrap gap-2">
          <input required placeholder="Display name" className={input}
                 value={form.display_name}
                 onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
          <select required className={input} value={form.provider_id}
                  onChange={(e) => setForm({ ...form, provider_id: e.target.value })}>
            <option value="">— провайдер —</option>
            {providers.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <input required placeholder="model_name" className={input}
                 value={form.model_name}
                 onChange={(e) => setForm({ ...form, model_name: e.target.value })} />
          <select className={input} value={form.cost_level}
                  onChange={(e) => setForm({ ...form, cost_level: e.target.value })}>
            {["free", "low", "medium", "high"].map((c) => <option key={c}>{c}</option>)}
          </select>
          <input type="number" step="0.01" placeholder="$/1M in" className={input + " w-24"}
                 value={form.input_price_per_1m}
                 onChange={(e) => setForm({ ...form, input_price_per_1m: +e.target.value })} />
          <input type="number" step="0.01" placeholder="$/1M out" className={input + " w-24"}
                 value={form.output_price_per_1m}
                 onChange={(e) => setForm({ ...form, output_price_per_1m: +e.target.value })} />
          <button className="bg-indigo-400 text-zinc-950 font-semibold px-4 py-2 rounded-lg text-sm hover:bg-indigo-300">
            Добавить
          </button>
        </div>
      </form>
    </div>
  );
}
