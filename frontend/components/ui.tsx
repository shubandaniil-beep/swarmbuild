import Link from "next/link";
import type { ReactNode } from "react";
import { Icon, type IconName } from "@/components/icons";

/* Примитивы дизайн-системы: графит + янтарный акцент, Manrope + JetBrains Mono. */

export function Kicker({ children }: { children: ReactNode }) {
  return <p className="kicker mb-2">{children}</p>;
}

export function SectionHeader({ kicker, title, sub }: {
  kicker?: string; title: string; sub?: string;
}) {
  return (
    <div className="mb-6">
      {kicker && <p className="kicker mb-2">{kicker}</p>}
      <h2 className="section-title">{title}</h2>
      {sub && <p className="mt-1.5 text-sm text-zinc-500 max-w-xl">{sub}</p>}
    </div>
  );
}

export function StatCard({ value, label, accent }: {
  value: ReactNode; label: string; accent?: boolean;
}) {
  return (
    <div className="card card-hover p-5">
      <div className={`text-2xl font-bold tracking-tight tabular ${accent ? "text-amber-400" : ""}`}>
        {value}
      </div>
      <div className="mt-1 text-xs uppercase tracking-wider text-zinc-500">{label}</div>
    </div>
  );
}

export function EmptyState({ icon, title, text, action }: {
  icon: IconName; title: string; text?: string;
  action?: { href: string; label: string };
}) {
  return (
    <div className="empty-state">
      <span className="grid h-14 w-14 place-items-center rounded-2xl border border-zinc-800
                       bg-zinc-900/60 text-zinc-500 mb-4">
        <Icon name={icon} size={26} strokeWidth={1.5} />
      </span>
      <h3 className="font-semibold text-lg">{title}</h3>
      {text && <p className="mt-1.5 text-sm text-zinc-500 max-w-sm">{text}</p>}
      {action && (
        <Link href={action.href} className="btn-primary px-6 py-2.5 text-sm mt-6">
          {action.label}
        </Link>
      )}
    </div>
  );
}

export function PageLoader({ label = "Загрузка…" }: { label?: string }) {
  return (
    <div className="space-y-3 pt-4">
      <div className="skeleton h-8 w-1/3" />
      <div className="skeleton h-24 w-full" />
      <div className="skeleton h-24 w-full" />
      <p className="text-xs text-zinc-600 pt-1">{label}</p>
    </div>
  );
}

/** Фирменный знак: гексагон-улей, внутри три узла роя, связанные в контур. */
export function LogoMark({ size = "text-lg" }: { size?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 font-bold tracking-tight ${size}`}>
      <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden fill="none" className="shrink-0">
        <path d="M16 3 27 9.5v13L16 29 5 22.5v-13L16 3Z"
              stroke="#f59e0b" strokeWidth="1.8" strokeLinejoin="round" />
        <path d="M16 11.2 20.2 19H11.8L16 11.2Z"
              stroke="#f59e0b" strokeWidth="1.2" strokeLinejoin="round" opacity=".45" />
        <circle cx="16" cy="10.6" r="2" fill="#fbbf24" />
        <circle cx="11.4" cy="19.4" r="2" fill="#f59e0b" />
        <circle cx="20.6" cy="19.4" r="2" fill="#f59e0b" />
      </svg>
      <span>
        swarm<span className="text-amber-400">build</span>
      </span>
    </span>
  );
}
