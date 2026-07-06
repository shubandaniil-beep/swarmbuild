"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

interface LogRow {
  project_id: string;
  phase: string;
  model_id: string;
  mandate: string;
  cost_usd: number;
  status: string;
  provider_type: string;
  provider_model_name: string;
  provider_key_mask: string;
  error_message: string;
  created_at: string | null;
}

interface UserActivityRow {
  id: string;
  email: string;
  action: string;
  project_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
}

export default function AdminLogs() {
  const [rows, setRows] = useState<LogRow[]>([]);
  const [activity, setActivity] = useState<UserActivityRow[]>([]);
  const [error, setError] = useState("");
  const [projectId, setProjectId] = useState("");
  const [status, setStatus] = useState("");

  const load = useCallback(() => {
    const params = new URLSearchParams();
    if (projectId) params.set("project_id", projectId);
    if (status) params.set("status", status);
    Promise.all([
      api<LogRow[]>(`/api/admin/logs?${params}`).then(setRows),
      api<UserActivityRow[]>(`/api/admin/user-activity?${projectId ? `project_id=${encodeURIComponent(projectId)}` : ""}`)
        .then(setActivity),
    ]).catch((e) => setError(String(e)));
  }, [projectId, status]);

  useEffect(() => { load(); }, [load]);

  const input = "bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Logs</h1>
      {error && <p className="text-red-400 text-sm">{error}</p>}
      <div className="flex gap-2">
        <input placeholder="project_id" className={input + " flex-1"}
               value={projectId} onChange={(e) => setProjectId(e.target.value)} />
        <select className={input} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">любой статус</option>
          <option value="success">success</option>
          <option value="provider_error">provider_error</option>
          <option value="failover">failover</option>
        </select>
        <button onClick={load}
                className="border border-zinc-700 px-4 py-2 rounded-lg text-sm hover:border-amber-400">
          Обновить
        </button>
      </div>
      <h2 className="font-semibold">User activity</h2>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-zinc-500 border-b border-zinc-800">
            <th className="py-2">Время</th><th>User</th><th>Action</th>
            <th>Project</th><th>Metadata</th>
          </tr>
        </thead>
        <tbody>
          {activity.map((r) => (
            <tr key={r.id} className="border-b border-zinc-900">
              <td className="py-1 text-zinc-500">
                {r.created_at ? new Date(r.created_at).toLocaleTimeString("ru-RU") : "—"}
              </td>
              <td className="text-zinc-400">{r.email || "—"}</td>
              <td className="text-amber-300">{r.action}</td>
              <td>{r.project_id ? r.project_id.slice(0, 8) : "—"}</td>
              <td className="text-zinc-500">{JSON.stringify(r.metadata)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="font-semibold">Agent call logs</h2>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-zinc-500 border-b border-zinc-800">
            <th className="py-2">Время</th><th>Проект</th><th>Фаза</th>
            <th>Provider</th><th>Мандат</th><th>$</th><th>Статус</th><th>Ошибка</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-zinc-900">
              <td className="py-1 text-zinc-500">
                {r.created_at ? new Date(r.created_at).toLocaleTimeString("ru-RU") : "—"}
              </td>
              <td className="text-zinc-400">{r.project_id.slice(0, 8)}</td>
              <td>{r.phase}</td>
              <td className="text-zinc-400">
                {(r.provider_type || "provider")} / {(r.provider_model_name || r.model_id).slice(0, 32)}
                {r.provider_key_mask ? <span className="block text-zinc-600">{r.provider_key_mask}</span> : null}
              </td>
              <td className="text-amber-300">{r.mandate}</td>
              <td>${r.cost_usd.toFixed(5)}</td>
              <td className={r.status === "success" ? "text-green-400" : r.status === "provider_error" ? "text-red-400" : "text-yellow-400"}>
                {r.status}
              </td>
              <td className="max-w-64 truncate text-red-300" title={r.error_message}>{r.error_message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
