"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Settings = Record<string, string | number | boolean>;

const SELECT_OPTIONS: Record<string, string[]> = {
  execution_mode: ["swarm", "single_agent"],
};

export default function AdminSettings() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api<Settings>("/api/admin/settings").then(setSettings).catch((e) => setError(String(e)));
  }, []);

  async function save() {
    if (!settings) return;
    setSaved(false);
    try {
      setSettings(await api<Settings>("/api/admin/settings", {
        method: "PUT", body: JSON.stringify(settings),
      }));
      setSaved(true);
    } catch (e) { setError(String(e)); }
  }

  if (error) return <p className="text-red-400">{error}</p>;
  if (!settings) return <p className="text-zinc-500">Загрузка…</p>;

  return (
    <div className="space-y-6 max-w-xl">
      <h1 className="text-2xl font-bold">System Settings</h1>
      <div className="space-y-3">
        {Object.entries(settings).map(([key, value]) => (
          <label key={key} className="flex items-center gap-3 text-sm">
            <span className="w-64 text-zinc-400">{key}</span>
            {SELECT_OPTIONS[key] ? (
              <select
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5"
                value={String(value)}
                onChange={(e) => setSettings({ ...settings, [key]: e.target.value })}
              >
                {SELECT_OPTIONS[key].map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            ) : typeof value === "boolean" ? (
              <input type="checkbox" checked={value}
                     onChange={(e) => setSettings({ ...settings, [key]: e.target.checked })} />
            ) : (
              <input
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5"
                value={String(value)}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    [key]: typeof value === "number"
                      ? +e.target.value || 0
                      : e.target.value,
                  })} />
            )}
          </label>
        ))}
      </div>
      <button onClick={save}
              className="bg-indigo-400 text-zinc-950 font-semibold px-6 py-2 rounded-lg hover:bg-indigo-300">
        Сохранить
      </button>
      {saved && <span className="ml-3 text-green-400 text-sm">Сохранено ✓</span>}
    </div>
  );
}
