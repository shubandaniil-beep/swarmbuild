"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Topup {
  id: string;
  user_id: string;
  email: string;
  credits: number;
  amount_usd: number;
  provider: string;
  provider_ref: string;
  status: string;
  created_at: string | null;
  paid_at: string | null;
}

export default function AdminTopups() {
  const [rows, setRows] = useState<Topup[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = () =>
    api<Topup[]>("/api/admin/topups").then(setRows).catch((e) => setError(String(e)));

  useEffect(() => { load(); }, []);

  async function approve(row: Topup) {
    const providerRef = window.prompt("Payment reference / Telegram tx id", row.provider_ref || "");
    if (providerRef === null) return;
    setBusy(row.id);
    try {
      await api(`/api/admin/topups/${row.id}/approve`, {
        method: "POST",
        body: JSON.stringify({ provider_ref: providerRef }),
      });
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy("");
    }
  }

  async function cancel(row: Topup) {
    if (!window.confirm("Cancel this top-up request?")) return;
    setBusy(row.id);
    try {
      await api(`/api/admin/topups/${row.id}/cancel`, { method: "POST" });
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Top-ups</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Pending заявки на пополнение. Approve начисляет credits пользователю.
        </p>
      </div>
      {error && <p className="text-red-400 text-sm">{error}</p>}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-zinc-500 border-b border-zinc-800">
              <th className="py-2">Дата</th>
              <th>Email</th>
              <th>Credits</th>
              <th>USD</th>
              <th>Provider</th>
              <th>Status</th>
              <th>Ref</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-zinc-900">
                <td className="py-2 text-zinc-500">
                  {row.created_at ? new Date(row.created_at).toLocaleString("ru-RU") : "—"}
                </td>
                <td>{row.email}</td>
                <td className="text-amber-300">{row.credits.toLocaleString("ru-RU")}</td>
                <td>${row.amount_usd}</td>
                <td>{row.provider}</td>
                <td className={row.status === "paid" ? "text-green-400" : "text-amber-300"}>
                  {row.status}
                </td>
                <td className="text-zinc-500">{row.provider_ref || "—"}</td>
                <td className="space-x-2 whitespace-nowrap">
                  {row.status === "pending" ? (
                    <>
                      <button disabled={busy === row.id}
                              onClick={() => approve(row)}
                              className="text-green-400 hover:text-green-300 disabled:opacity-50">
                        approve
                      </button>
                      <button disabled={busy === row.id}
                              onClick={() => cancel(row)}
                              className="text-red-400 hover:text-red-300 disabled:opacity-50">
                        cancel
                      </button>
                    </>
                  ) : (
                    <span className="text-zinc-600">processed</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
