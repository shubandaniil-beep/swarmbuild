import type { Phase } from "@/lib/types";
import { Icon } from "@/components/icons";

/** Вертикальный таймлайн фаз: линия соединяет узлы, активная фаза «дышит». */
export default function PhaseTimeline({ phases }: { phases: Phase[] }) {
  return (
    <ol>
      {phases.map((p, i) => {
        const last = i === phases.length - 1;
        return (
          <li key={p.phase_key} className="relative flex items-center gap-3 pb-4 last:pb-0 text-sm">
            {!last && (
              <span aria-hidden
                    className={`absolute left-[9px] top-5 bottom-0 w-px ${
                      p.status === "done" ? "bg-green-900/70" : "bg-zinc-800"}`} />
            )}
            <span className="relative grid h-[19px] w-[19px] shrink-0 place-items-center">
              {p.status === "done" ? (
                <span className="grid h-full w-full place-items-center rounded-full
                                 bg-green-500/15 text-green-400">
                  <Icon name="check" size={11} strokeWidth={2.4} />
                </span>
              ) : p.status === "running" ? (
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400 animate-pulse-dot" />
              ) : p.status === "failed" || p.status === "blocked" ? (
                <span className="grid h-full w-full place-items-center rounded-full
                                 bg-red-500/15 text-red-400">
                  <Icon name="x" size={11} strokeWidth={2.4} />
                </span>
              ) : (
                <span className={`h-2 w-2 rounded-full ${
                  p.status === "skipped" ? "bg-zinc-600" : "bg-zinc-700"}`} />
              )}
            </span>
            <span className={
              p.status === "running" ? "text-amber-300 font-semibold"
              : p.status === "done" ? "text-zinc-200"
              : "text-zinc-500"
            }>
              {p.label || "Этап"}
            </span>
            {p.status === "running" && (
              <span className="ml-auto font-mono text-[11px] text-amber-400/70">running</span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
