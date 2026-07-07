"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, downloadUrl, getCachedUser } from "@/lib/api";
import type { ArtifactInfo, Phase, Project, ProjectEvent } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import PhaseTimeline from "@/components/PhaseTimeline";
import BudgetCard from "@/components/BudgetCard";
import CreditCard from "@/components/CreditCard";
import EventLog from "@/components/EventLog";
import ArtifactCard from "@/components/ArtifactCard";
import { PageLoader } from "@/components/ui";
import { Icon, IconTile, type IconName } from "@/components/icons";
import RequireAuth from "@/components/RequireAuth";

const ACTIVE = ["accepted", "queued", "running", "packaging", "repairing"];

const NEXT_IMPROVEMENTS = [
  { id: "deploy-guide", title: "Задеплоить проект", action: "Deploy guide", credits: 800, icon: "rocket", detail: "План запуска и понятные шаги публикации" },
  { id: "domain-setup", title: "Подключить домен", action: "Domain setup", credits: 700, icon: "globe", detail: "Адрес сайта и проверки открытия" },
  { id: "telegram-integration", title: "Добавить Telegram-бота", action: "Telegram integration", credits: 2500, icon: "send", detail: "Бот с командами и базовой логикой" },
  { id: "pitch-deck", title: "Сделать pitch deck", action: "Pitch deck", credits: 1200, icon: "presentation", detail: "Структура слайдов для клиента или инвестора" },
  { id: "staff-guide", title: "Сделать инструкцию для сотрудников", action: "Employee instruction", credits: 1200, icon: "clipboardCheck", detail: "Понятный регламент использования результата" },
];

const MODE_LABELS: Record<string, string> = { auto: "авто", code: "код", document: "документы", business: "бизнес-пакет", mixed: "смешанный" };
const TYPE_LABELS: Record<string, string> = {
  auto: "авто-определение", code_project: "кодовый проект", document_project: "документ", business_project: "бизнес-пакет", presentation_project: "презентация", research_project: "исследование", telegram_bot: "Telegram-бот", mini_crm: "мини-CRM", landing_page: "лендинг", web_app: "веб-приложение", dashboard: "дашборд", integration: "интеграция", automation_script: "автоматизация", python_utility: "утилита", saas_mvp: "SaaS MVP", mobile_app_concept: "концепт приложения", education_project: "учебный проект", diploma_or_coursework: "диплом / курсовая", pitch_deck: "pitch deck", marketing_pack: "маркетинг-пакет", custom: "свой формат",
};
const COMPLEXITY_LABELS: Record<string, string> = { low: "лёгкий объём", medium: "средний объём", high: "большой объём" };
const OUTPUT_LABELS: Record<string, string> = {
  mvp: "MVP / файлы проекта", docs: "документация", business_plan: "бизнес-план", pitch_outline: "pitch outline", presentation_structure: "структура презентации", research_report: "исследование", technical_spec: "спецификация", marketing_plan: "маркетинг-план", financial_model: "финмодель", deployment_guide: "инструкция запуска", user_manual: "инструкция пользователя", roadmap: "roadmap", branding_copy: "тексты / брендинг",
};
const STATUS_LABELS: Record<string, string> = {
  accepted: "принят", queued: "в очереди", running: "в работе", packaging: "упаковывается", repairing: "исправление замечаний", needs_internal_repair: "на внутренней доработке", provider_config_error: "AI-модели не настроены", ready: "готов", partial_ready: "готов с ограничениями", failed: "ошибка", needs_topup: "нужно пополнить кредиты", needs_provider: "AI-модели временно недоступны", cancelled: "отменён",
};

function label(map: Record<string, string>, value?: string | null) { if (!value) return "авто"; return map[value] || value.replaceAll("_", " "); }
function friendlyLimitations(text: string) {
  return text.replace(/^# .*\n+/, "").replaceAll("This is an MVP skeleton, not a production system.", "Это MVP-версия, а не полностью продакшн-система.").replaceAll("No authentication and minimal error handling.", "Авторизация и обработка ошибок пока минимальные.").replaceAll("No automated test suite beyond smoke checks.", "Автотесты ограничены базовыми smoke-проверками.").replaceAll("Open issue", "Открытое замечание");
}

async function optionalApi<T>(path: string, fallback: T): Promise<T> {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try { return await api<T>(path); } catch { if (attempt === 0) await new Promise((resolve) => setTimeout(resolve, 500)); }
  }
  return fallback;
}

export default function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <RequireAuth><ProjectContent id={id} /></RequireAuth>;
}

function ProjectContent({ id }: { id: string }) {
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [phases, setPhases] = useState<Phase[]>([]);
  const [events, setEvents] = useState<ProjectEvent[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactInfo[]>([]);
  const [limitations, setLimitations] = useState("");
  const [error, setError] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let stop = false;
    async function load() {
      try {
        const p = await api<Project>(`/api/projects/${id}`);
        const [ph, ev, ar] = await Promise.all([
          optionalApi<Phase[]>(`/api/projects/${id}/phases`, []),
          optionalApi<ProjectEvent[]>(`/api/projects/${id}/events`, []),
          optionalApi<ArtifactInfo[]>(`/api/projects/${id}/artifacts`, []),
        ]);
        if (stop) return;
        setError("");
        setProject(p);
        setPhases(ph);
        setEvents(ev);
        setArtifacts(ar);
        const lim = ar.find((a) => a.display_name === "limitations.md");
        if (lim && !limitations) {
          api<{ content: string }>(`/api/projects/${id}/artifacts/${lim.id}/content`)
            .then((r) => !stop && setLimitations(r.content))
            .catch(() => {});
        }
        if (ACTIVE.includes(p.status)) setTimeout(load, 2000);
      } catch (e) {
        if (!stop) setError(String(e));
      }
    }
    load();
    return () => { stop = true; };
  }, [id, reloadKey, limitations]);

  async function restartProject() {
    setBusyAction("restart");
    setError("");
    try {
      await api(`/api/projects/${id}/start`, { method: "POST" });
      setProject((p) => (p ? { ...p, status: "queued" } : p));
      setReloadKey((k) => k + 1);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusyAction("");
    }
  }

  async function continueProject(action: string, credits: number, improvementId: string) {
    setBusyAction(improvementId);
    try {
      const res = await api<{ project_id: string }>(`/api/projects/${id}/continue`, {
        method: "POST",
        body: JSON.stringify({ action, budget_credits: credits }),
      });
      await api(`/api/projects/${res.project_id}/start`, { method: "POST" });
      router.push(`/projects/${res.project_id}`);
    } catch (e) {
      setError(String(e));
      setBusyAction("");
    }
  }

  if (error) return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-900 to-black p-4 flex items-center justify-center">
      <div className="max-w-md w-full rounded-xl border border-red-900/30 bg-red-950/20 p-6">
        <h1 className="text-lg font-bold text-red-400 mb-2">⚠️ Ошибка загрузки</h1>
        <p className="text-sm text-red-300/80 mb-4">{error}</p>
        <div className="flex gap-2">
          <button onClick={() => setReloadKey(k => k + 1)} className="flex-1 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-medium transition-colors">Попробовать</button>
          <button onClick={() => router.push('/projects')} className="flex-1 px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-white text-sm font-medium transition-colors">Назад</button>
        </div>
      </div>
    </div>
  );

  if (!project) return <div className="min-h-screen bg-gradient-to-br from-zinc-900 to-black"><PageLoader label="Загружаю проект…" /></div>;

  const done = project.status === "ready" || project.status === "partial_ready";
  const running = ACTIVE.includes(project.status);
  const finals = artifacts.filter((a) => a.artifact_type === "final");
  const spentCredits = (project.credits_spent ?? 0).toLocaleString("ru-RU");
  const summary = done
    ? `Готов финальный пакет: ${finals.length} файлов, потрачено ${spentCredits} credits.` + (project.status === "partial_ready" ? " Результат готов частично — ниже указаны ограничения." : " Проверка готовности пройдена.")
    : running
      ? "Система выполняет текущий этап."
      : `Проект сейчас в статусе: ${STATUS_LABELS[project.status] || project.status}.`;

  const projectTags = [
    `формат: ${label(MODE_LABELS, project.project_mode)}`,
    `результат: ${label(TYPE_LABELS, project.project_type)}`,
    project.requires_codebase ? "включает файлы проекта" : "без кода",
    label(COMPLEXITY_LABELS, project.estimated_complexity),
  ];

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-3xl font-bold tracking-tight">{project.title}</h1>
          <StatusBadge status={project.status} />
          {running && <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse-dot" />}
        </div>
        <div className="mt-2 flex flex-wrap gap-2 text-xs">
          {projectTags.map((t) => (<span key={t} className="px-2 py-1 rounded-full bg-zinc-800/80 text-zinc-400">{t}</span>))}
          {project.requested_outputs?.map((o) => (<span key={o} className="px-2 py-1 rounded-full bg-amber-400/10 text-amber-300">{label(OUTPUT_LABELS, o)}</span>))}
        </div>
        {project.parent_project_id && (<p className="mt-2 text-sm text-zinc-500">↳ доработка проекта <Link className="text-amber-300" href={`/projects/${project.parent_project_id}`}>#{project.parent_project_id.slice(0, 8)}</Link></p>)}
      </div>

      <div className={done ? "card-glow p-5" : "card p-5"}>
        <p className="kicker mb-1">Что произошло</p>
        <p className="text-sm text-zinc-300">{summary}</p>
      </div>

      {project.status === "needs_topup" && (<div className="rounded-xl border border-amber-800/60 bg-amber-950/40 p-4 text-sm text-amber-200">Кредиты закончились до завершения проекта. Собран частичный результат — пополните баланс и запустите доработку, чтобы продолжить.</div>)}

      {project.status === "needs_provider" && (
        <div className="rounded-xl border border-amber-800/60 bg-amber-950/30 p-4 text-sm text-amber-200 space-y-3">
          <p>AI-модели сейчас недоступны: чаще всего это временный лимит запросов у провайдера. Подождите минуту и запустите проект заново — прогресс по завершённым этапам сохраняется.</p>
          <button onClick={restartProject} disabled={!!busyAction} className="btn-primary px-5 py-2 text-sm disabled:opacity-50">{busyAction === "restart" ? "Запускаю..." : "↻ Запустить заново"}</button>
        </div>
      )}

      {project.status === "failed" && (
        <div className="rounded-xl border border-red-900/60 bg-red-950/30 p-4 text-sm text-red-200 space-y-3">
          <p>Проект остановился с ошибкой. Подробности — в журнале ниже. Можно запустить его заново: завершённые этапы не выполняются повторно.</p>
          <button onClick={restartProject} disabled={!!busyAction} className="btn-primary px-5 py-2 text-sm disabled:opacity-50">{busyAction === "restart" ? "Запускаю..." : "↻ Запустить заново"}</button>
        </div>
      )}

      {getCachedUser()?.role === "admin" ? (project.budget && <BudgetCard budget={project.budget} />) : <CreditCard project={project} />}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card p-5">
          <p className="kicker mb-3">Этапы</p>
          <PhaseTimeline phases={phases} />
        </div>
        <div>
          <p className="kicker mb-3">Короткий журнал</p>
          <EventLog events={events} />
        </div>
      </div>

      {finals.length > 0 && (
        <div>
          <p className="kicker mb-1">Что готово</p>
          <h2 className="section-title mb-4">Готовые файлы ({finals.length})</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {finals.map((a) => (<ArtifactCard key={a.id} projectId={id} artifact={a} />))}
          </div>
          <div className="mt-4 flex gap-3 items-center">
            <Link href={`/projects/${id}/artifacts`} className="btn-ghost px-5 py-2 text-sm">Все финальные файлы →</Link>
            {project.downloadable
              ? (<a href={downloadUrl(`/api/projects/${id}/download`)} className="btn-primary px-5 py-2 text-sm"><Icon name="download" size={14} /> project.zip</a>)
              : (<span className="text-xs text-amber-300/90">Итоговый архив станет доступен, когда проект пройдёт проверку готовности.</span>)}
          </div>
        </div>
      )}

      {limitations && (
        <div className="card p-5">
          <p className="kicker mb-2">Известные ограничения</p>
          <pre className="text-xs text-zinc-400 whitespace-pre-wrap leading-relaxed">{friendlyLimitations(limitations)}</pre>
        </div>
      )}

      {done && (
        <div>
          <p className="kicker mb-1">Что можно сделать дальше</p>
          <h2 className="section-title mb-1">Следующие улучшения</h2>
          <p className="text-sm text-zinc-500 mb-4">Каждое действие запускает связанный проект-доработку с тем же контекстом.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {NEXT_IMPROVEMENTS.map((a) => (
              <button key={a.id} onClick={() => continueProject(a.action, a.credits, a.id)} disabled={!!busyAction} className="card p-4 text-left hover:border-amber-400/50 disabled:opacity-50 transition-colors">
                <span className="flex items-start gap-3">
                  <IconTile name={a.icon as IconName} size={32} />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-zinc-100">{busyAction === a.id ? "Запускаю..." : a.title}</span>
                    <span className="mt-1 block text-xs leading-relaxed text-zinc-500">{a.detail}</span>
                  </span>
                </span>
                <span className="mt-3 inline-flex rounded-full border border-amber-400/30 bg-amber-400/10 px-2.5 py-1 text-xs font-medium text-amber-300">{a.credits.toLocaleString("ru-RU")} credits</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
