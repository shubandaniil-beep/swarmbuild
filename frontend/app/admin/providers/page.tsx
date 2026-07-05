"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

interface Provider {
  id: string;
  name: string;
  provider_type: string;
  base_url: string;
  api_key_mask: string;
  has_key: boolean;
  key_count: number;
  active_keys: number;
  errored_keys: number;
  total_key_uses: number;
  enabled: boolean;
  priority: number;
  status: string;
  last_tested_at: string | null;
  last_error: string;
  notes: string;
}

interface ProviderKey {
  id: string;
  label: string;
  api_key_mask: string;
  enabled: boolean;
  status: string;
  use_count: number;
  last_used_at: string | null;
  last_error: string;
}

interface RuntimeState {
  enable_real_model_calls: boolean;
  enable_mock_mode: boolean;
  allow_mock_fallback: boolean;
  execution_mode: string;
  usable_real_keys: number;
  enabled_real_models: number;
  real_providers_ready: number;
  recent_provider_errors: Array<{
    project_id: string;
    provider_type: string;
    provider_model_name: string;
    provider_key_mask: string;
    error_message: string;
    created_at: string | null;
  }>;
}

interface TestResult {
  ok: boolean;
  key_mask?: string;
  model_name: string;
  tested_keys: Array<{ key_mask: string; ok: boolean; error?: string }>;
}

type ProviderWithTest = Provider & { test?: TestResult };

const TYPES = [
  "openai",
  "anthropic",
  "gemini",
  "deepseek",
  "qwen",
  "groq",
  "openrouter",
  "custom_openai",
  "mock",
];

const INPUT = "bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm outline-none focus:border-indigo-400";

function statusTone(status: string) {
  if (status === "active") return "text-green-300 bg-green-400/10 border-green-500/30";
  if (status === "error") return "text-red-300 bg-red-400/10 border-red-500/30";
  return "text-zinc-400 bg-zinc-900 border-zinc-800";
}

function timeLabel(value: string | null) {
  if (!value) return "never";
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AdminProviders() {
  const [rows, setRows] = useState<Provider[]>([]);
  const [runtime, setRuntime] = useState<RuntimeState | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [openPool, setOpenPool] = useState<string | null>(null);
  const [keys, setKeys] = useState<Record<string, ProviderKey[]>>({});
  const [bulk, setBulk] = useState<Record<string, string>>({});
  const [tests, setTests] = useState<Record<string, TestResult>>({});
  const [form, setForm] = useState({
    name: "",
    provider_type: "openrouter",
    base_url: "https://openrouter.ai/api/v1",
    api_key: "",
  });

  async function load() {
    try {
      const [providers, state] = await Promise.all([
        api<Provider[]>("/api/admin/providers"),
        api<RuntimeState>("/api/admin/runtime"),
      ]);
      setRows(providers);
      setRuntime(state);
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => { load(); }, []);

  const realRows = useMemo(() => rows.filter((p) => p.provider_type !== "mock"), [rows]);
  const selected = rows.find((p) => p.id === openPool) || null;

  async function loadKeys(id: string) {
    try {
      const ks = await api<ProviderKey[]>(`/api/admin/providers/${id}/keys`);
      setKeys((prev) => ({ ...prev, [id]: ks }));
    } catch (e) {
      setError(String(e));
    }
  }

  function togglePool(id: string) {
    const next = openPool === id ? null : id;
    setOpenPool(next);
    if (next) loadKeys(next);
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/api/admin/providers", { method: "POST", body: JSON.stringify(form) });
      setMessage("Провайдер добавлен.");
      setForm({ name: "", provider_type: "openrouter", base_url: "https://openrouter.ai/api/v1", api_key: "" });
      await load();
    } catch (err) {
      setError(String(err));
    }
  }

  async function update(p: Provider, patch: Partial<Provider> & { api_key?: string }) {
    try {
      await api(`/api/admin/providers/${p.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: p.name,
          provider_type: p.provider_type,
          base_url: p.base_url,
          enabled: p.enabled,
          priority: p.priority,
          notes: p.notes,
          api_key: "",
          ...patch,
        }),
      });
      await load();
      if (openPool === p.id) await loadKeys(p.id);
    } catch (err) {
      setError(String(err));
    }
  }

  async function addKeys(id: string) {
    const raw = bulk[id] || "";
    if (!raw.trim()) return;
    try {
      const res = await api<{ added: number }>(`/api/admin/providers/${id}/keys`, {
        method: "POST",
        body: JSON.stringify({ keys: raw }),
      });
      setBulk((prev) => ({ ...prev, [id]: "" }));
      setMessage(res.added ? `Добавлено ключей: ${res.added}` : "Новых ключей не найдено.");
      await Promise.all([loadKeys(id), load()]);
    } catch (err) {
      setError(String(err));
    }
  }

  async function toggleKey(pid: string, kid: string) {
    try {
      await api(`/api/admin/providers/${pid}/keys/${kid}/toggle`, { method: "POST" });
      await Promise.all([loadKeys(pid), load()]);
    } catch (err) {
      setError(String(err));
    }
  }

  async function deleteKey(pid: string, kid: string) {
    try {
      await api(`/api/admin/providers/${pid}/keys/${kid}`, { method: "DELETE" });
      await Promise.all([loadKeys(pid), load()]);
    } catch (err) {
      setError(String(err));
    }
  }

  async function testProvider(id: string) {
    try {
      setMessage("Проверяю ключи провайдера...");
      const res = await api<ProviderWithTest>(`/api/admin/providers/${id}/test`, { method: "POST" });
      if (res.test) setTests((prev) => ({ ...prev, [id]: res.test as TestResult }));
      setMessage(res.test?.ok ? "Тест прошел, реальный API ответил." : "Тест не прошел, смотрите ошибку ключа.");
      await Promise.all([load(), loadKeys(id)]);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <p className="kicker">AI Runtime</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Провайдеры и API-ключи</h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-500">
          Здесь видно, какие реальные модели доступны, какие ключи usable, сколько запросов прошло и почему вызов мог упасть.
        </p>
      </div>

      {(error || message) && (
        <div className={`rounded-lg border px-4 py-3 text-sm ${
          error ? "border-red-500/30 bg-red-500/10 text-red-300" : "border-indigo-500/30 bg-indigo-500/10 text-indigo-200"
        }`}>
          {error || message}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-5">
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wider text-zinc-600">Real calls</p>
          <p className="mt-2 text-2xl font-semibold">{runtime?.enable_real_model_calls ? "On" : "Off"}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wider text-zinc-600">Execution</p>
          <p className="mt-2 text-2xl font-semibold">
            {runtime?.execution_mode === "single_agent" ? "Single" : "Swarm"}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wider text-zinc-600">Usable keys</p>
          <p className="mt-2 text-2xl font-semibold">{runtime?.usable_real_keys ?? 0}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wider text-zinc-600">Real models</p>
          <p className="mt-2 text-2xl font-semibold">{runtime?.enabled_real_models ?? 0}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs uppercase tracking-wider text-zinc-600">Mock fallback</p>
          <p className="mt-2 text-2xl font-semibold">{runtime?.allow_mock_fallback ? "On" : "Off"}</p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <section className="space-y-3">
          {realRows.map((p) => {
            const test = tests[p.id];
            return (
              <div key={p.id} className="card p-5">
                <div className="flex flex-wrap items-start gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-lg font-semibold">{p.name}</h2>
                      <span className={`rounded-full border px-2 py-0.5 text-xs ${statusTone(p.status)}`}>
                        {p.status}
                      </span>
                      <span className="rounded-full border border-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
                        {p.provider_type}
                      </span>
                    </div>
                    <p className="mt-1 break-all text-xs text-zinc-600">{p.base_url || "default adapter URL"}</p>
                  </div>
                  <div className="ml-auto flex flex-wrap gap-2">
                    <button onClick={() => testProvider(p.id)} className="btn-ghost px-3 py-2 text-sm">
                      Test API
                    </button>
                    <button
                      onClick={() => update(p, { enabled: !p.enabled })}
                      className={`rounded-lg border px-3 py-2 text-sm ${
                        p.enabled ? "border-green-500/30 text-green-300" : "border-zinc-800 text-zinc-500"
                      }`}
                    >
                      {p.enabled ? "Enabled" : "Disabled"}
                    </button>
                    <button onClick={() => togglePool(p.id)} className="btn-ghost px-3 py-2 text-sm">
                      Keys
                    </button>
                  </div>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-4">
                  <Metric label="Usable" value={`${p.active_keys}/${p.key_count}`} />
                  <Metric label="Errors" value={String(p.errored_keys)} />
                  <Metric label="Requests" value={String(p.total_key_uses)} />
                  <Metric label="Last test" value={timeLabel(p.last_tested_at)} />
                </div>

                {p.last_error && (
                  <pre className="mt-3 whitespace-pre-wrap rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-200">
                    {p.last_error}
                  </pre>
                )}

                {test && (
                  <div className="mt-3 rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                    <div className="flex flex-wrap gap-2 text-xs text-zinc-500">
                      <span>test: {test.ok ? "ok" : "failed"}</span>
                      <span>model: {test.model_name}</span>
                      {test.key_mask && <span>key: {test.key_mask}</span>}
                    </div>
                    {test.tested_keys.some((k) => !k.ok) && (
                      <div className="mt-2 space-y-1">
                        {test.tested_keys.filter((k) => !k.ok).map((k) => (
                          <p key={`${k.key_mask}-${k.error}`} className="text-xs text-red-300">
                            {k.key_mask}: {k.error}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {openPool === p.id && (
                  <KeyPool
                    provider={p}
                    keys={keys[p.id] || []}
                    bulk={bulk[p.id] || ""}
                    setBulk={(value) => setBulk((prev) => ({ ...prev, [p.id]: value }))}
                    addKeys={() => addKeys(p.id)}
                    toggleKey={(kid) => toggleKey(p.id, kid)}
                    deleteKey={(kid) => deleteKey(p.id, kid)}
                  />
                )}
              </div>
            );
          })}
          {realRows.length === 0 && (
            <div className="card p-5 text-sm text-zinc-500">Реальные провайдеры не настроены.</div>
          )}
        </section>

        <aside className="space-y-4">
          <form onSubmit={create} className="card p-5 space-y-3">
            <h2 className="font-semibold">Добавить провайдера</h2>
            <input required placeholder="Название" className={`${INPUT} w-full`}
                   value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <select className={`${INPUT} w-full`} value={form.provider_type}
                    onChange={(e) => setForm({ ...form, provider_type: e.target.value })}>
              {TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
            <input placeholder="Base URL" className={`${INPUT} w-full`}
                   value={form.base_url}
                   onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
            <input type="password" placeholder="API key" className={`${INPUT} w-full`}
                   value={form.api_key}
                   onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
            <button className="w-full rounded-lg bg-indigo-400 px-4 py-2 text-sm font-semibold text-zinc-950 hover:bg-indigo-300">
              Добавить
            </button>
          </form>

          <div className="card p-5">
            <h2 className="font-semibold">Runtime errors</h2>
            <div className="mt-3 space-y-3">
              {(runtime?.recent_provider_errors || []).map((row) => (
                <div key={`${row.project_id}-${row.created_at}`} className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                  <div className="flex flex-wrap gap-2 text-xs text-zinc-500">
                    <span>{row.provider_type || "provider"}</span>
                    <span>{row.provider_model_name || "model"}</span>
                    {row.provider_key_mask && <span>{row.provider_key_mask}</span>}
                  </div>
                  <p className="mt-2 text-xs text-red-300">{row.error_message || "unknown error"}</p>
                </div>
              ))}
              {(runtime?.recent_provider_errors || []).length === 0 && (
                <p className="text-sm text-zinc-500">Последних provider errors нет.</p>
              )}
            </div>
          </div>

          {selected && (
            <div className="card p-5">
              <h2 className="font-semibold">Выбранный провайдер</h2>
              <p className="mt-2 text-sm text-zinc-500">
                {selected.name}: {selected.active_keys} usable keys, {selected.total_key_uses} запросов.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
      <p className="text-[11px] uppercase tracking-wider text-zinc-600">{label}</p>
      <p className="mt-1 text-sm font-medium text-zinc-200">{value}</p>
    </div>
  );
}

function KeyPool({
  provider,
  keys,
  bulk,
  setBulk,
  addKeys,
  toggleKey,
  deleteKey,
}: {
  provider: Provider;
  keys: ProviderKey[];
  bulk: string;
  setBulk: (value: string) => void;
  addKeys: () => void;
  toggleKey: (id: string) => void;
  deleteKey: (id: string) => void;
}) {
  return (
    <div className="mt-4 border-t border-zinc-800 pt-4">
      <div className="space-y-2">
        {keys.map((k) => (
          <div key={k.id} className="grid gap-2 rounded-lg border border-zinc-800 bg-zinc-950/60 p-3 md:grid-cols-[1fr_auto]">
            <div className="min-w-0">
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="font-mono text-zinc-300">{k.api_key_mask}</span>
                <span className={`rounded-full border px-2 py-0.5 ${statusTone(k.status)}`}>{k.status}</span>
                <span className="text-zinc-500">uses: {k.use_count}</span>
                <span className="text-zinc-500">last: {timeLabel(k.last_used_at)}</span>
              </div>
              {k.last_error && <p className="mt-2 text-xs text-red-300">{k.last_error}</p>}
            </div>
            <div className="flex gap-2">
              <button onClick={() => toggleKey(k.id)}
                      className={`rounded-lg border px-3 py-1 text-xs ${
                        k.enabled ? "border-green-500/30 text-green-300" : "border-zinc-800 text-zinc-500"
                      }`}>
                {k.enabled ? "On" : "Off"}
              </button>
              <button onClick={() => deleteKey(k.id)}
                      className="rounded-lg border border-red-500/30 px-3 py-1 text-xs text-red-300">
                Delete
              </button>
            </div>
          </div>
        ))}
        {keys.length === 0 && (
          <p className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3 text-sm text-zinc-500">
            У {provider.name} пока нет ключей.
          </p>
        )}
      </div>

      <div className="mt-3 space-y-2">
        <textarea
          rows={4}
          className={`${INPUT} w-full font-mono`}
          placeholder="Вставьте ключи по одному на строку или через запятую."
          value={bulk}
          onChange={(e) => setBulk(e.target.value)}
        />
        <button
          onClick={addKeys}
          disabled={!bulk.trim()}
          className="rounded-lg bg-indigo-400 px-4 py-2 text-sm font-semibold text-zinc-950 hover:bg-indigo-300 disabled:opacity-40"
        >
          Добавить ключи
        </button>
      </div>
    </div>
  );
}
