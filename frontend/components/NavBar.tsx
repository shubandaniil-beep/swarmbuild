"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getCachedUser, logout } from "@/lib/api";
import { LogoMark } from "@/components/ui";

const LINKS = [
  ["/projects", "Проекты"],
  ["/new-project", "Новый проект"],
] as const;

export default function NavBar() {
  const [user, setUser] = useState<{
    email: string;
    role: string;
    token_balance?: number;
    credits_per_usd?: number;
  } | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    setUser(getCachedUser());
  }, [pathname]);

  return (
    <>
      <nav className="glass sticky top-0 z-50 px-4 sm:px-6 py-3 sm:py-3.5
                      flex flex-wrap items-center gap-x-4 gap-y-2 sm:gap-x-7">
        <Link href="/" className="shrink-0"><LogoMark /></Link>
        {user && LINKS.map(([href, label]) => (
            <Link key={href} href={href}
                  className={`text-sm whitespace-nowrap transition-colors ${
                    pathname.startsWith(href)
                      ? "text-amber-300"
                      : "text-zinc-400 hover:text-white"}`}>
              {label}
            </Link>
          ))}
        <span className="ml-auto flex items-center gap-3 sm:gap-4 text-sm">
          {user ? (
            <>
              <span className="chip hidden lg:inline-flex max-w-52">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 shrink-0" />
                <span className="truncate">{user.email}</span>
              </span>
              <span className="chip chip-accent hidden md:inline-flex whitespace-nowrap">
                {(user.token_balance ?? 0).toLocaleString("ru-RU")} credits
                <span className="text-zinc-500">
                  ≈ ${((user.token_balance ?? 0) / (user.credits_per_usd || 100)).toLocaleString("ru-RU")}
                </span>
              </span>
              <Link href="/settings"
                    className="text-zinc-500 hover:text-amber-300 whitespace-nowrap transition-colors">
                Пополнить
              </Link>
              <button onClick={async () => { await logout(); location.href = "/"; }}
                      className="text-zinc-500 hover:text-white transition-colors">
                Выйти
              </button>
            </>
          ) : (
            <Link href="/login" className="btn-ghost px-4 py-1.5 text-sm">Войти</Link>
          )}
        </span>
      </nav>
      {user?.role === "admin" && (
        <Link href="/admin/providers"
              title="Founder console"
              aria-label="Founder console"
              className="fixed bottom-3 left-3 z-50 w-2 h-2 rounded-full bg-zinc-800/60 hover:bg-zinc-600 transition-colors" />
      )}
    </>
  );
}
