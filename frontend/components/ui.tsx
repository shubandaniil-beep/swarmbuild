import Link from "next/link";
import type { ReactNode } from "react";

/* Reusable design-system primitives (near-black / indigo identity). */

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
      {sub && <p className="mt-1.5 text-sm text-zinc-500">{sub}</p>}
    </div>
  );
}

export function StatCard({ value, label, accent }: {
  value: ReactNode; label: string; accent?: boolean;
}) {
  return (
    <div className="card card-hover p-5">
      <div className={`text-2xl font-bold tracking-tight ${accent ? "text-indigo-400" : ""}`}>
        {value}
      </div>
      <div className="mt-1 text-xs uppercase tracking-wider text-zinc-500">{label}</div>
    </div>
  );
}

export function EmptyState({ icon, title, text, action }: {
  icon: string; title: string; text?: string;
  action?: { href: string; label: string };
}) {
  return (
    <div className="empty-state">
      <div className="text-4xl mb-3 opacity-80">{icon}</div>
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

export function LogoMark({ size = "text-lg" }: { size?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-bold tracking-tight ${size}`}>
      <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden="true"
           className="shrink-0" fill="none">
        <path d="M7.5 13.5 12 7h8l4.5 6.5-2.2 8.2L16 26l-6.3-4.3-2.2-8.2Z"
              fill="#18181b" stroke="#6366f1" strokeWidth="1.6" />
        <path d="M11.5 12h9M10.5 16h11M12 20h8" stroke="#6366f1"
              strokeWidth="1.2" strokeLinecap="round" opacity=".75" />
        <path d="M17.2 9.8c1.6-2.8 5.5-2.1 6 .5.3 1.8-1.2 3.2-3.3 3.1"
              stroke="#e5e7eb" strokeWidth="1.1" strokeLinecap="round" opacity=".7" />
        <path d="M14.7 15.8c0-1.7 1.4-3 3.1-3h.5c1.7 0 3.1 1.3 3.1 3s-1.4 3-3.1 3h-.5c-1.7 0-3.1-1.3-3.1-3Z"
              fill="#6366f1" />
        <path d="M17 13v5.6M19.2 13.2v5.2" stroke="#18181b" strokeWidth="1" />
        <path d="M14.6 14.2c-1.8-1.6-4.2-.8-4.5 1-.3 1.7 1.3 2.8 3.1 2.5"
              stroke="#e5e7eb" strokeWidth="1.1" strokeLinecap="round" opacity=".7" />
        <circle cx="21.8" cy="15" r=".7" fill="#18181b" />
      </svg>
      Swarm<span className="text-indigo-400">Build</span>
      <span className="text-zinc-600 font-normal ml-1.5 text-xs align-middle">AI</span>
    </span>
  );
}
