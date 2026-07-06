import type { Project } from "@/lib/types";

export default function CreditCard({ project }: { project: Project }) {
  const spent = project.credits_spent ?? 0;
  const estimate = project.credits_estimate ?? 0;
  const remaining = project.credits_remaining ?? null;
  const perUsd = project.credits_per_usd || 100;
  const pct = estimate ? Math.min(100, (spent / estimate) * 100) : 0;
  const fmt = (n: number) => n.toLocaleString("ru-RU");

  return (
    <div className="border border-zinc-800 rounded-xl p-4">
      <div className="flex justify-between text-sm">
        <span className="text-zinc-400">Кредиты проекта</span>
        <span>
          {fmt(spent)}{estimate ? ` / ~${fmt(estimate)}` : ""} credits
        </span>
      </div>
      <div className="mt-2 h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div className="h-full bg-amber-400" style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-2 text-xs text-zinc-500 flex gap-3 flex-wrap">
        <span>потрачено: {fmt(spent)}</span>
        {estimate > 0 && <span>оценка: ~{fmt(estimate)}</span>}
        {estimate > 0 && <span>эквивалент: ~${(estimate / perUsd).toLocaleString("ru-RU")}</span>}
        {remaining !== null && <span>баланс: {fmt(remaining)}</span>}
        <span>{perUsd} credits = $1</span>
        {project.demo_run && <span className="text-amber-300">trial-запуск из стартовых credits</span>}
      </div>
    </div>
  );
}
