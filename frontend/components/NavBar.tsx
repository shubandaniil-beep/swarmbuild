"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getUser, logout } from "@/lib/api";
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
    setUser(getUser());
  }, [pathname]);

  return (
    <>
      <nav className="glass sticky top-0 z-50 px-6 py-3.5 flex items-center gap-7">
        <Link href="/"><LogoMark /></Link>
        {user && LINKS.map(([href, label]) => (
            <Link key={href} href={href}
                  className={`text-sm transition-colors ${
                    pathname.startsWith(href)
                      ? "text-indigo-300"
                      : "text-zinc-400 hover:text-white"}`}>
              {label}
            </Link>
          ))}
        <span className="ml-auto flex items-center gap-4 text-sm">
          {user ? (
            <>
              <span className="chip hidden sm:inline-flex">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                {user.email}
              </span>
              <span className="chip chip-indigo hidden md:inline-flex">
                {(user.token_balance ?? 0).toLocaleString("ru-RU")} credits
                <span className="text-zinc-500">
                  ≈ ${((user.token_balance ?? 0) / (user.credits_per_usd || 100)).toLocaleString("ru-RU")}
                </span>
              </span>
              <Link href="/settings" className="text-zinc-500 hover:text-indigo-300 transition-colors">
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
