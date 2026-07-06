"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";

interface Row {
  project_id: string;
  title: string;
  user_email: string | null;
  status: string;
  budget_usd: number;
  project_type: string;
  project_mode: string;
  current_phase: string | null;
  created_at: string | null;
}

export default function AdminProjects() {
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");

  const load = () =>
    api<Row[]>("/api/admin/projects").then(setRows).catch((e) => setError(String(e)));
  useEffect(() => { load(); }, []);

  async function act(id: string, path: string, body?: object) {
    try {
      await api(`/api/admin/projects/${id}${path}`, {
        method: path === "" ? "DELETE" : "POST",
        body: body ? JSON.stringify(body) : undefined,
      });
      load();
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Все проекты</h1>
      {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-zinc-500 border-b border-zinc-800">
            <th className="py-2">Title</th><th>User</th><th>Status</th><th>$</th>
            <th>Type / mode</th><th>Phase</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.project_id} className="border-b border-zinc-900 align-top">
              <td className="py-2">
                <div className="flex flex-col gap-1">
                  <Link href={`/admin/projects/${r.project_id}`} className="hover:text-amber-300">
                    {r.title}
                  </Link>
                  <div className="flex gap-3 text-xs text-zinc-500">
                    <Link href={`/projects/${r.project_id}`} className="hover:text-amber-300">
                      public
                    </Link>
                  </div>
                </div>
              </td>
              <td className="text-zinc-400">{r.user_email || "—"}</td>
              <td><StatusBadge status={r.status} /></td>
              <td>${r.budget_usd}</td>
              <td className="text-zinc-400">{r.project_type} / {r.project_mode}</td>
              <td className="text-zinc-400">{r.current_phase || "—"}</td>
              <td className="space-x-2 whitespace-nowrap">
                <button onClick={() => act(r.project_id, "/rerun-phase")}
                        className="text-zinc-300 hover:text-white">rerun</button>
                <button onClick={() => act(r.project_id, "/force-package")}
                        className="text-zinc-300 hover:text-white">package</button>
                <button onClick={() => act(r.project_id, "/status", { status: "ready" })}
                        className="text-green-400 hover:text-green-300">ready</button>
                <button onClick={() => act(r.project_id, "/status", { status: "failed" })}
                        className="text-red-400 hover:text-red-300">fail</button>
                <button onClick={() => act(r.project_id, "")}
                        className="text-zinc-500 hover:text-red-400">delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
