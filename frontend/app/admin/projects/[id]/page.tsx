"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ArtifactInfo, Phase, Project, ProjectEvent } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import PhaseTimeline from "@/components/PhaseTimeline";
import EventLog from "@/components/EventLog";
import ArtifactCard from "@/components/ArtifactCard";
import BudgetCard from "@/components/BudgetCard";
import { PageLoader, SectionHeader, StatCard } from "@/components/ui";

const ACTIVE = ["accepted", "queued", "running", "packaging", "repairing"];

type JsonlEvent = {
  type: string;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

type AdminAgentCall = {
  phase: string;
  model_id: string;
  mandate: string;
  cost_usd: number;
  status: string;
  provider_id?: string;
  provider_type?: string;
  provider_model_name?: string;
  provider_key_mask?: string;
  error_message?: string;
  created_at: string | null;
  output_preview?: string | null;
};

type AdminCommandRun = {
  command: string;
  exit_code: number;
  stdout_path?: string | null;
  stderr_path?: string | null;
  stdout_preview?: string | null;
  stderr_preview?: string | null;
  duration_seconds: number;
  status: string;
  at: string;
  reason?: string | null;
};

type AdminLogs = {
  "events.jsonl": JsonlEvent[];
  "agent-calls.jsonl": Array<Record<string, unknown>>;
  "command-runs.jsonl": AdminCommandRun[];
  agent_calls_db: AdminAgentCall[];
  summary: {
    project_id: string;
    status: string;
    current_phase: string | null;
    events: number;
    agent_calls: number;
    command_runs: number;
  };
};

async function optionalApi<T>(path: string, fallback: T): Promise<T> {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      return await api<T>(path);
    } catch {
      if (attempt === 0) {
        await new Promise((resolve) => setTimeout(resolve, 400));
      }
    }
  }
  return fallback;
}

function clamp(text: string | null | undefined, max = 420) {
  if (!text) return "—";
  const clean = text.trim();
  return clean.length > max ? `${clean.slice(0, max).trimEnd()}…` : clean;
}

function timeLabel(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function routeLabel(call: AdminAgentCall) {
  const provider = call.provider_type || "provider";
  const model = call.provider_model_name || call.model_id.slice(0, 8);
  const key = call.provider_key_mask ? ` · key ${call.provider_key_mask}` : "";
  return `${provider} · ${model}${key}`;
}

export default function AdminProjectMonitor({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <MonitorContent id={id} />;
}

function MonitorContent({ id }: { id: string }) {
  const [project, setProject] = useState<Project | null>(null);
  const [phases, setPhases] = useState<Phase[]>([]);
  const [events, setEvents] = useState<ProjectEvent[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactInfo[]>([]);
  const [logs, setLogs] = useState<AdminLogs | null>(null);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState("");

  useEffect(() => {
    let stop = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function load() {
      try {
        const p = await api<Project>(`/api/projects/${id}`);
        const [ph, ev, ar, lg] = await Promise.all([
          optionalApi<Phase[]>(`/api/projects/${id}/phases`, []),
          optionalApi<ProjectEvent[]>(`/api/projects/${id}/events`, []),
          optionalApi<ArtifactInfo[]>(`/api/projects/${id}/artifacts`, []),
          api<AdminLogs>(`/api/admin/projects/${id}/logs?limit=60`),
        ]);

        if (stop) return;
        setProject(p);
        setPhases(ph);
        setEvents(ev);
        setArtifacts(ar);
        setLogs(lg);
        setUpdatedAt(new Date().toLocaleTimeString("ru-RU", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }));
        setError("");

        if (ACTIVE.includes(p.status)) {
          timer = setTimeout(load, 2000);
        }
      } catch (e) {
        if (!stop) {
          setError(String(e));
          timer = setTimeout(load, 3000);
        }
      }
    }

    load();
    return () => {
      stop = true;
      if (timer) clearTimeout(timer);
    };
  }, [id]);

  if (error && !project) return <p className="text-red-400">{error}</p>;
  if (!project) return <PageLoader label="Загружаю монитор проекта…" />;

  const calls = logs?.agent_calls_db ?? [];
  const commandRuns = logs?.["command-runs.jsonl"] ?? [];
  const latestEvent = events[events.length - 1];
  const latestCall = calls[0];
  const latestCommand = commandRuns[commandRuns.length - 1];
  const finals = artifacts.filter((a) => a.artifact_type === "final");
  const isLive = ACTIVE.includes(project.status);

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-3xl font-bold tracking-tight">{project.title}</h1>
            <StatusBadge status={project.status} />
            {isLive && (
              <span className="inline-flex items-center gap-2 text-xs text-amber-300">
                <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse-dot" />
                live
              </span>
            )}
          </div>
          <p className="mt-2 text-sm text-zinc-500">
            Admin monitor · {project.project_type} / {project.project_mode} · этап{" "}
            {project.current_phase || "—"}
          </p>
          <p className="mt-1 text-xs text-zinc-600">
            Обновлено {updatedAt || "—"}{logs?.summary ? ` · событий ${logs.summary.events}, вызовов ${logs.summary.agent_calls}, команд ${logs.summary.command_runs}` : ""}
          </p>
        </div>
        <div className="flex gap-2">
          <Link href={`/projects/${id}`} className="btn-ghost px-4 py-2 text-sm">
            Public view
          </Link>
          <Link href="/admin/projects" className="btn-ghost px-4 py-2 text-sm">
            Back to list
          </Link>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard value={project.current_phase || "—"} label="Текущий этап" accent />
        <StatCard value={calls.length.toString()} label="Вызовы модели" />
        <StatCard value={commandRuns.length.toString()} label="Команды" />
        <StatCard value={`$${project.budget_usd.toFixed(2)}`} label="Бюджет" />
        <StatCard value={project.billing_mode || "client"} label="Billing mode" />
        <StatCard value={project.zero_credit_reason || "—"} label="0-credit reason" />
      </div>

      {project.budget && <BudgetCard budget={project.budget} />}

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <section className="card p-5">
            <SectionHeader
              kicker="Progress"
              title="Этапы проекта"
              sub="Показывает, где сейчас находится сборка и что уже завершилось."
            />
            <PhaseTimeline phases={phases} />
          </section>

          <section>
            <SectionHeader
              kicker="Stream"
              title="Живая лента"
              sub="События проекта обновляются по мере выполнения."
            />
            <EventLog events={events} />
          </section>
        </div>

        <div className="space-y-6">
          <section className="card p-5">
            <SectionHeader
              kicker="Model output"
              title="Последний ответ модели"
              sub="Показываю безопасный срез вывода, без внутренних рассуждений."
            />
            {latestCall ? (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2 text-xs text-zinc-500">
                  <span>{routeLabel(latestCall)}</span>
                  <span>phase: {latestCall.phase}</span>
                  <span>status: {latestCall.status}</span>
                  <span>${latestCall.cost_usd.toFixed(5)}</span>
                  <span>{timeLabel(latestCall.created_at)}</span>
                </div>
                {latestCall.error_message && (
                  <pre className="whitespace-pre-wrap rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-200">
                    {latestCall.error_message}
                  </pre>
                )}
                <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3">
                  <p className="text-[11px] uppercase tracking-wider text-zinc-600">Mandate</p>
                  <p className="mt-1 text-sm text-zinc-300">{latestCall.mandate}</p>
                </div>
                <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3">
                  <p className="text-[11px] uppercase tracking-wider text-zinc-600">Output</p>
                  <pre className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-zinc-300 max-h-56 overflow-y-auto">
                    {clamp(latestCall.output_preview, 800)}
                  </pre>
                </div>
              </div>
            ) : (
              <p className="text-sm text-zinc-500">Пока нет вызовов модели.</p>
            )}
          </section>

          <section className="card p-5">
            <SectionHeader
              kicker="Command line"
              title="Последняя команда"
              sub="Показываю выполненные команды и короткий срез stdout / stderr."
            />
            {latestCommand ? (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2 text-xs text-zinc-500">
                  <span>{timeLabel(latestCommand.at)}</span>
                  <span>status: {latestCommand.status}</span>
                  <span>exit: {latestCommand.exit_code}</span>
                  <span>{latestCommand.duration_seconds.toFixed(2)}s</span>
                </div>
                <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3">
                  <p className="text-[11px] uppercase tracking-wider text-zinc-600">Command</p>
                  <p className="mt-1 font-mono text-xs text-zinc-300 whitespace-pre-wrap">
                    {latestCommand.command}
                  </p>
                </div>
                <div className="grid gap-3">
                  <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3">
                    <p className="text-[11px] uppercase tracking-wider text-zinc-600">stdout</p>
                    <pre className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-zinc-300 max-h-40 overflow-y-auto">
                      {clamp(latestCommand.stdout_preview, 600)}
                    </pre>
                  </div>
                  <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3">
                    <p className="text-[11px] uppercase tracking-wider text-zinc-600">stderr</p>
                    <pre className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-zinc-300 max-h-40 overflow-y-auto">
                      {clamp(latestCommand.stderr_preview, 600)}
                    </pre>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-zinc-500">Пока нет командных запусков.</p>
            )}
          </section>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="card p-5">
          <SectionHeader
            kicker="Recent"
            title="Последние вызовы модели"
            sub="Видно, какой мандат дал системе каждый вызов и чем он закончился."
          />
          <div className="space-y-3">
            {calls.slice(0, 6).map((call, index) => (
              <div key={`${call.created_at || index}-${call.model_id}-${index}`} className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3">
                <div className="flex flex-wrap gap-2 text-[11px] text-zinc-500">
                  <span>{timeLabel(call.created_at)}</span>
                  <span>phase: {call.phase}</span>
                  <span>{routeLabel(call)}</span>
                  <span>status: {call.status}</span>
                  <span>${call.cost_usd.toFixed(5)}</span>
                </div>
                <p className="mt-2 text-sm text-zinc-300">{call.mandate}</p>
                {call.error_message && (
                  <p className="mt-2 text-xs text-red-300">{call.error_message}</p>
                )}
                <pre className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-zinc-500 max-h-32 overflow-y-auto">
                  {clamp(call.output_preview, 500)}
                </pre>
              </div>
            ))}
            {calls.length === 0 && <p className="text-sm text-zinc-500">Вызовов ещё нет.</p>}
          </div>
        </section>

        <section className="card p-5">
          <SectionHeader
            kicker="Recent"
            title="Последние команды"
            sub="Полезно, когда нужно быстро понять, что реально делала сборка."
          />
          <div className="space-y-3">
            {commandRuns.slice(-6).map((run, index) => (
              <div key={`${run.at}-${index}`} className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3">
                <div className="flex flex-wrap gap-2 text-[11px] text-zinc-500">
                  <span>{timeLabel(run.at)}</span>
                  <span>status: {run.status}</span>
                  <span>exit: {run.exit_code}</span>
                  <span>{run.duration_seconds.toFixed(2)}s</span>
                </div>
                <p className="mt-2 font-mono text-xs text-zinc-300 whitespace-pre-wrap">
                  {run.command}
                </p>
                <div className="mt-2 grid gap-2">
                  <pre className="whitespace-pre-wrap text-xs leading-relaxed text-zinc-500 max-h-24 overflow-y-auto">
                    {clamp(run.stdout_preview, 360)}
                  </pre>
                  <pre className="whitespace-pre-wrap text-xs leading-relaxed text-zinc-500 max-h-24 overflow-y-auto">
                    {clamp(run.stderr_preview, 360)}
                  </pre>
                </div>
              </div>
            ))}
            {commandRuns.length === 0 && <p className="text-sm text-zinc-500">Командных запусков ещё нет.</p>}
          </div>
        </section>
      </div>

      {latestEvent && (
        <section className="card p-5">
          <SectionHeader
            kicker="Signal"
            title="Последний сигнал"
            sub="Короткая сводка по последнему событию проекта."
          />
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3">
            <div className="flex flex-wrap gap-2 text-xs text-zinc-500">
              <span>{timeLabel(latestEvent.created_at)}</span>
              <span>{latestEvent.type}</span>
            </div>
            <p className="mt-2 text-sm text-zinc-300">{latestEvent.message}</p>
          </div>
        </section>
      )}

      {finals.length > 0 && (
        <section>
          <SectionHeader
            kicker="Artifacts"
            title="Файлы проекта"
            sub="Финальные артефакты, которые уже можно открыть или скачать."
          />
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {finals.map((artifact) => (
              <ArtifactCard key={artifact.id} projectId={id} artifact={artifact} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
