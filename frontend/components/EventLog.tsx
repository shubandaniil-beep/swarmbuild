import type { ProjectEvent } from "@/lib/types";

const ICON: Record<string, string> = {
  project_accepted: "📥",
  phase_started: "▶️",
  phase_finished: "✅",
  phase_failed: "❌",
  issues_created: "⚠️",
  issues_repaired: "🔧",
  sandbox_run: "🧪",
  audit_completed: "🔍",
  release_decision: "⚖️",
  packaged: "📦",
  partial_ready: "🟡",
};

export default function EventLog({ events }: { events: ProjectEvent[] }) {
  return (
    <div className="card p-4 max-h-80 overflow-y-auto log-scroll">
      <ul className="space-y-1.5 text-sm">
        {events.map((e, i) => (
          <li key={i} className="flex gap-2 animate-fade-in-up">
            <span className="text-zinc-600 shrink-0 font-mono text-xs pt-0.5">
              {new Date(e.created_at).toLocaleTimeString("ru-RU", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
            <span className="shrink-0 text-xs pt-0.5">{ICON[e.type] || "·"}</span>
            <span className="min-w-0">
              <span className="block text-zinc-300">{e.message}</span>
              {e.metadata && Object.keys(e.metadata).length > 0 && (
                <span className="mt-0.5 block text-[11px] leading-relaxed text-zinc-600 break-words">
                  {JSON.stringify(e.metadata)}
                </span>
              )}
            </span>
          </li>
        ))}
        {events.length === 0 && (
          <li className="text-zinc-600">Работа ещё не началась — событий нет</li>
        )}
      </ul>
    </div>
  );
}
