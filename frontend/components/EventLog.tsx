import type { ProjectEvent } from "@/lib/types";
import { Icon, type IconName } from "@/components/icons";

const EVENT_ICON: Record<string, { name: IconName; cls: string }> = {
  project_accepted: { name: "inbox", cls: "text-amber-300" },
  phase_started: { name: "play", cls: "text-zinc-500" },
  phase_finished: { name: "check", cls: "text-green-400" },
  phase_failed: { name: "x", cls: "text-red-400" },
  issues_created: { name: "alertTriangle", cls: "text-amber-300" },
  issues_repaired: { name: "wrench", cls: "text-green-400" },
  sandbox_run: { name: "flask", cls: "text-zinc-400" },
  audit_completed: { name: "search", cls: "text-zinc-400" },
  release_decision: { name: "scale", cls: "text-amber-300" },
  packaged: { name: "package", cls: "text-green-400" },
  partial_ready: { name: "circleDot", cls: "text-amber-300" },
  provider_blocked: { name: "clock", cls: "text-amber-300" },
  runtime_not_configured: { name: "plug", cls: "text-red-400" },
  worker_interrupted: { name: "plug", cls: "text-red-400" },
  needs_topup: { name: "creditCard", cls: "text-amber-300" },
};

export default function EventLog({ events }: { events: ProjectEvent[] }) {
  return (
    <div className="card p-4 max-h-80 overflow-y-auto log-scroll">
      <ul className="space-y-2 text-sm">
        {events.map((e, i) => {
          const icon = EVENT_ICON[e.type] || { name: "circleDot" as IconName, cls: "text-zinc-600" };
          return (
            <li key={i} className="flex gap-2.5 animate-fade-in-up">
              <span className="text-zinc-600 shrink-0 font-mono text-[11px] pt-0.5 tabular">
                {new Date(e.created_at).toLocaleTimeString("ru-RU", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
              <span className={`shrink-0 pt-0.5 ${icon.cls}`}>
                <Icon name={icon.name} size={14} />
              </span>
              <span className="min-w-0">
                <span className="block text-zinc-300 leading-snug">{e.message}</span>
                {e.metadata && Object.keys(e.metadata).length > 0 && (
                  <span className="mt-0.5 block font-mono text-[10px] leading-relaxed
                                   text-zinc-600 break-words">
                    {JSON.stringify(e.metadata)}
                  </span>
                )}
              </span>
            </li>
          );
        })}
        {events.length === 0 && (
          <li className="text-zinc-600">Работа ещё не началась — событий нет</li>
        )}
      </ul>
    </div>
  );
}
