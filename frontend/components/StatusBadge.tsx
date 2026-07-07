const STYLE: Record<string, { badge: string; dot: string }> = {
  ready: { badge: "bg-green-950/80 text-green-300 border-green-800/60", dot: "bg-green-400" },
  partial_ready: { badge: "bg-yellow-950/80 text-yellow-300 border-yellow-800/60", dot: "bg-yellow-400" },
  running: { badge: "bg-blue-950/80 text-blue-300 border-blue-800/60", dot: "bg-blue-400 animate-pulse-dot" },
  repairing: { badge: "bg-blue-950/80 text-blue-300 border-blue-800/60", dot: "bg-blue-400 animate-pulse-dot" },
  packaging: { badge: "bg-blue-950/80 text-blue-300 border-blue-800/60", dot: "bg-blue-400 animate-pulse-dot" },
  needs_internal_repair: { badge: "bg-amber-950/80 text-amber-300 border-amber-800/60", dot: "bg-amber-400" },
  provider_config_error: { badge: "bg-red-950/80 text-red-300 border-red-800/60", dot: "bg-red-400" },
  queued: { badge: "bg-zinc-900 text-zinc-400 border-zinc-700/60", dot: "bg-zinc-500 animate-pulse-dot" },
  accepted: { badge: "bg-zinc-900 text-zinc-400 border-zinc-700/60", dot: "bg-zinc-500" },
  failed: { badge: "bg-red-950/80 text-red-300 border-red-800/60", dot: "bg-red-400" },
  blocked: { badge: "bg-red-950/80 text-red-400 border-red-900/60", dot: "bg-red-600" },
  needs_topup: { badge: "bg-amber-950/80 text-amber-300 border-amber-800/60", dot: "bg-amber-400" },
  needs_provider: { badge: "bg-amber-950/80 text-amber-300 border-amber-800/60", dot: "bg-amber-400" },
  cancelled: { badge: "bg-zinc-900 text-zinc-500 border-zinc-800", dot: "bg-zinc-600" },
};

const LABELS: Record<string, string> = {
  accepted: "принят",
  queued: "в очереди",
  running: "в работе",
  repairing: "исправление замечаний",
  packaging: "упаковка",
  needs_internal_repair: "на внутренней доработке",
  provider_config_error: "AI-модели не настроены",
  ready: "готов",
  partial_ready: "частично готов",
  failed: "ошибка",
  blocked: "нужно внимание",
  needs_topup: "нужно пополнить",
  needs_provider: "AI временно недоступен",
  cancelled: "отменён",
};

export function StatusBadge({ status }: { status: string }) {
  const s = STYLE[status] || STYLE.accepted;
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${s.badge}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {LABELS[status] || status}
    </span>
  );
}
