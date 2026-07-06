"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface PType {
  id: string;
  key: string;
  display_name: string;
  description: string;
  enabled: boolean;
  requires_codebase: boolean;
  default_outputs: string[];
  recommended_budget_min: number;
  recommended_budget_max: number;
}

export default function AdminProjectTypes() {
  const [rows, setRows] = useState<PType[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ key: "", display_name: "", requires_codebase: true });

  const load = () =>
    api<PType[]>("/api/admin/project-types").then(setRows).catch((e) => setError(String(e)));
  useEffect(() => { load(); }, []);

  async function patch(t: PType, changes: Partial<PType>) {
    try {
      await api(`/api/admin/project-types/${t.id}`, {
        method: "PUT", body: JSON.stringify({ ...t, ...changes }),
      });
      load();
    } catch (e) { setError(String(e)); }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/api/admin/project-types", {
        method: "POST",
        body: JSON.stringify({ ...form, default_outputs: ["docs"] }),
      });
      setForm({ key: "", display_name: "", requires_codebase: true });
      load();
    } catch (err) { setError(String(err)); }
  }

  const input = "bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm";

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Типы проектов</h1>
      {error && <p className="text-red-400 text-sm">{error}</p>}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-zinc-500 border-b border-zinc-800">
            <th className="py-2">Key</th><th>Название</th><th>Кодовая база</th>
            <th>Outputs</th><th>Вкл</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => (
            <tr key={t.id} className={`border-b border-zinc-900 ${t.enabled ? "" : "opacity-50"}`}>
              <td className="py-2 text-zinc-400">{t.key}</td>
              <td>{t.display_name}</td>
              <td>
                <button onClick={() => patch(t, { requires_codebase: !t.requires_codebase })}
                        className={t.requires_codebase ? "text-amber-300" : "text-zinc-500"}>
                  {t.requires_codebase ? "code" : "no-code"}
                </button>
              </td>
              <td className="text-zinc-400">{t.default_outputs.join(", ")}</td>
              <td>
                <button onClick={() => patch(t, { enabled: !t.enabled })}
                        className={t.enabled ? "text-green-400" : "text-zinc-500"}>
                  {t.enabled ? "on" : "off"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <form onSubmit={create} className="border border-zinc-800 rounded-xl p-4 space-y-3">
        <h2 className="font-semibold">Добавить тип</h2>
        <div className="flex flex-wrap gap-2">
          <input required placeholder="key (snake_case)" className={input}
                 value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} />
          <input required placeholder="Display name" className={input}
                 value={form.display_name}
                 onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.requires_codebase}
                   onChange={(e) => setForm({ ...form, requires_codebase: e.target.checked })} />
            requires codebase
          </label>
          <button className="bg-amber-400 text-zinc-950 font-semibold px-4 py-2 rounded-lg text-sm hover:bg-amber-300">
            Добавить
          </button>
        </div>
      </form>
    </div>
  );
}
