"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Row {
  id: string;
  email: string;
  role: string;
  disabled: boolean;
  created_at: string | null;
  projects_count: number;
  total_budget_usd: number;
  token_balance: number;
  lifetime_tokens_spent: number;
  demo_generations_remaining: number;
}

export default function AdminUsers() {
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");

  const load = () =>
    api<Row[]>("/api/admin/users").then(setRows).catch((e) => setError(String(e)));
  useEffect(() => { load(); }, []);

  async function act(id: string, path: string, body: object) {
    try {
      await api(`/api/admin/users/${id}${path}`, {
        method: "POST", body: JSON.stringify(body),
      });
      load();
    } catch (e) { setError(String(e)); }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Пользователи</h1>
      {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-zinc-500 border-b border-zinc-800">
            <th className="py-2">Email</th><th>Role</th><th>Projects</th>
            <th>Credits</th><th>Spent</th><th>Demo</th><th>Создан</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((u) => (
            <tr key={u.id} className={`border-b border-zinc-900 ${u.disabled ? "opacity-50" : ""}`}>
              <td className="py-2">{u.email}</td>
              <td className={u.role === "admin" ? "text-amber-300" : ""}>{u.role}</td>
              <td>{u.projects_count}</td>
              <td className="text-amber-300">{u.token_balance.toLocaleString("ru-RU")}</td>
              <td>{u.lifetime_tokens_spent.toLocaleString("ru-RU")}</td>
              <td>{u.demo_generations_remaining}</td>
              <td className="text-zinc-500">
                {u.created_at ? new Date(u.created_at).toLocaleDateString("ru-RU") : "—"}
              </td>
              <td className="space-x-2 whitespace-nowrap">
                <button onClick={() => act(u.id, "/role",
                          { role: u.role === "admin" ? "user" : "admin" })}
                        className="text-zinc-300 hover:text-white">
                  {u.role === "admin" ? "→ user" : "→ admin"}
                </button>
                <button onClick={() => act(u.id, "/disable", { disabled: !u.disabled })}
                        className="text-red-400 hover:text-red-300">
                  {u.disabled ? "enable" : "disable"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
