import type { Phase } from "@/lib/types";

const DOT: Record<string, string> = {
  done: "bg-green-400",
  running: "bg-indigo-400 animate-pulse-dot",
  failed: "bg-red-500",
  skipped: "bg-zinc-600",
  pending: "bg-zinc-700",
  blocked: "bg-red-800",
};

export default function PhaseTimeline({ phases }: { phases: Phase[] }) {
  return (
    <ol className="relative">
      {phases.map((p, i) => (
        <li key={p.phase_key} className="flex items-center gap-3 py-1.5 text-sm">
          <span className="relative flex flex-col items-center">
            <span className={`w-2.5 h-2.5 rounded-full ${DOT[p.status] || DOT.pending}`} />
            {i < phases.length - 1 && (
              <span className="absolute top-3 w-px h-5 bg-zinc-800" />
            )}
          </span>
          <span className={
            p.status === "running" ? "text-indigo-300 font-medium"
            : p.status === "done" ? "text-zinc-200"
            : "text-zinc-500"
          }>
            {p.label || "Этап"}
          </span>
          <span className="ml-auto text-xs text-zinc-600">
            {p.status === "running" ? "выполняется…" : ""}
          </span>
        </li>
      ))}
    </ol>
  );
}
