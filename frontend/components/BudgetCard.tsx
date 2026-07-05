import type { BudgetState } from "@/lib/types";

export default function BudgetCard({ budget }: { budget: BudgetState }) {
  const total = budget.user_budget_usd || 1;
  const pct = total ? Math.min(100, (budget.spent_usd / total) * 100) : 0;
  const hasInternalSplit =
    budget.model_budget_usd !== undefined &&
    budget.compute_budget_usd !== undefined &&
    budget.reserve_budget_usd !== undefined;
  return (
    <div className="border border-zinc-800 rounded-xl p-4">
      <div className="flex justify-between text-sm">
        <span className="text-zinc-400">Бюджет</span>
        <span>
          ${budget.spent_usd.toFixed(4)} / ${budget.user_budget_usd}
        </span>
      </div>
      <div className="mt-2 h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div className="h-full bg-indigo-400" style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-2 text-xs text-zinc-500 flex gap-3 flex-wrap">
        {hasInternalSplit ? (
          <>
            <span>AI-модели: ${budget.model_budget_usd}</span>
            <span>сборка: ${budget.compute_budget_usd}</span>
            <span>страховой резерв: ${budget.reserve_budget_usd}</span>
            {budget.saving_mode && <span className="text-yellow-400">экономный режим</span>}
          </>
        ) : (
          <>
            <span>остаток: ${budget.remaining_usd.toFixed(4)}</span>
            <span>статус: {budget.status}</span>
          </>
        )}
      </div>
    </div>
  );
}
