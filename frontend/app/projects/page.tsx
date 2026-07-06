"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, downloadUrl } from "@/lib/api";
import { Icon, IconTile, type IconName } from "@/components/icons";
import type { Project } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState, PageLoader, StatCard } from "@/components/ui";
import RequireAuth from "@/components/RequireAuth";

const FILTERS = [
  { key: "all", label: "Все" },
  { key: "ready", label: "Готовые" },
  { key: "partial_ready", label: "Частично готовые" },
  { key: "running", label: "В работе" },
  { key: "failed", label: "С ошибкой" },
  { key: "mode:code", label: "Код" },
  { key: "mode:document", label: "Документы" },
  { key: "mode:business", label: "Бизнес" },
  { key: "mode:mixed", label: "Смешанные" },
] as const;

const MODE_ICON: Record<string, IconName> = {
  code: "code", document: "fileText", business: "briefcase", mixed: "layers", auto: "sparkles",
};

const MODE_LABEL: Record<string, string> = {
  code: "код",
  document: "документы",
  business: "бизнес",
  mixed: "смешанный",
  auto: "авто",
};

export default function Projects() {
  return (
    <RequireAuth>
      <ProjectsContent />
    </RequireAuth>
  );
}

function ProjectsContent() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");

  useEffect(() => {
    api<Project[]>("/api/projects").then(setProjects).catch((e) => setError(String(e)));
  }, []);

  if (error) return <p className="text-red-400">{error}</p>;
  if (!projects) return <PageLoader label="Загружаю ваши проекты…" />;

  const ready = projects.filter((p) => p.status === "ready").length;
  const running = projects.filter((p) =>
    ["running", "queued", "packaging", "accepted", "repairing"].includes(p.status)).length;
  const spentCredits = projects.reduce((s, p) => s + (p.credits_spent || 0), 0);

  const shown = projects.filter((p) => {
    if (filter === "all") return true;
    if (filter.startsWith("mode:")) return p.project_mode === filter.slice(5);
    if (filter === "running")
      return ["running", "queued", "packaging", "accepted", "repairing"].includes(p.status);
    return p.status === filter;
  });

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <div>
          <p className="kicker mb-1">Личный кабинет</p>
          <h1 className="text-3xl font-bold tracking-tight">Проекты</h1>
        </div>
        <Link href="/new-project" className="btn-primary ml-auto px-5 py-2.5 text-sm">
          + Новый проект
        </Link>
      </div>

      {projects.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard value={projects.length} label="всего проектов" />
          <StatCard value={ready} label="готово" accent />
          <StatCard value={running || "—"} label="в работе" />
          <StatCard value={spentCredits.toLocaleString("ru-RU")} label="credits использовано" />
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button key={f.key} onClick={() => setFilter(f.key)}
                  className={`text-xs px-3.5 py-1.5 rounded-full border transition-all ${
                    filter === f.key
                      ? "border-amber-400/70 text-amber-300 bg-amber-400/10"
                      : "border-zinc-800 text-zinc-500 hover:text-zinc-300 hover:border-zinc-600"}`}>
            {f.label}
          </button>
        ))}
      </div>

      {projects.length === 0 ? (
        <EmptyState icon="hexagon" title="Первая задача ещё не создана"
                    text="Опишите идею, выберите бюджет — система соберёт проект и упакует результат в архив."
                    action={{ href: "/new-project", label: "Создать первый проект →" }} />
      ) : shown.length === 0 ? (
        <EmptyState icon="search" title="Ничего не найдено"
                    text="Под этот фильтр не попал ни один проект." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {shown.map((p) => (
            <div key={p.project_id} className="card card-hover p-5 flex flex-col">
              <div className="flex items-center gap-2.5">
                <IconTile name={MODE_ICON[p.project_mode] || "sparkles"} size={30} />
                <Link href={`/projects/${p.project_id}`}
                      className="font-semibold truncate hover:text-amber-300 transition-colors">
                  {p.title}
                </Link>
                <span className="ml-auto shrink-0"><StatusBadge status={p.status} /></span>
              </div>
              <p className="mt-2 text-sm text-zinc-500 line-clamp-2 leading-relaxed flex-1">
                {p.brief}
              </p>
              <div className="mt-4 flex items-center gap-2 text-xs flex-wrap">
                <span className="chip chip-accent">${p.budget_usd}</span>
                <span className="chip">{MODE_LABEL[p.project_mode] || p.project_mode}</span>
                <span className="ml-auto flex gap-2">
                  <Link href={`/projects/${p.project_id}`}
                        className="btn-ghost px-3 py-1.5">Открыть</Link>
                  {p.downloadable && (
                    <a href={downloadUrl(`/api/projects/${p.project_id}/download`)}
                       className="btn-ghost px-3 py-1.5"><Icon name="download" size={13} /> ZIP</a>
                  )}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
