"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import RequireAuth from "@/components/RequireAuth";

const SECTIONS = [
  ["/admin", "Dashboard"],
  ["/admin/projects", "Projects"],
  ["/admin/providers", "AI Runtime"],
  ["/admin/logs", "Logs"],
  ["/admin/users", "Users"],
  ["/admin/topups", "Top-ups"],
  ["/admin/tariffs", "Tariffs"],
  ["/admin/models", "Models"],
  ["/admin/project-types", "Project types"],
  ["/admin/settings", "Settings"],
] as const;

export default function AdminLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <RequireAuth adminOnly>
      <div className="flex gap-8">
        <aside className="w-56 shrink-0">
          <p className="kicker px-3 mb-3">Control room</p>
          <nav className="space-y-0.5 text-sm">
            {SECTIONS.map(([href, label]) => {
              const active = href === "/admin" ? pathname === href : pathname.startsWith(href);
              return (
                <Link key={href} href={href}
                    className={`flex items-center px-3 py-2 rounded-lg transition-all ${
                      active
                        ? "bg-indigo-400/10 text-indigo-300 shadow-[inset_2px_0_0_rgba(99, 102, 241,0.7)]"
                        : "text-zinc-500 hover:text-white hover:bg-zinc-900/60"}`}>
                {label}
              </Link>
              );
            })}
          </nav>
        </aside>
        <div className="flex-1 min-w-0 animate-fade-in-up">{children}</div>
      </div>
    </RequireAuth>
  );
}
