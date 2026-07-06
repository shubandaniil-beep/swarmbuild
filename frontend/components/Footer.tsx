import Link from "next/link";
import { LogoMark } from "@/components/ui";

export default function Footer() {
  return (
    <footer className="mt-20 border-t border-zinc-900">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10
                      flex flex-col sm:flex-row gap-6 sm:items-center">
        <div>
          <LogoMark size="text-base" />
          <p className="mt-2 text-xs text-zinc-600 max-w-xs leading-relaxed">
            Ротационный рой AI-агентов: идея и бюджет на входе,
            проверенный пакет файлов на выходе.
          </p>
        </div>
        <nav className="sm:ml-auto flex flex-wrap gap-x-6 gap-y-2 text-sm text-zinc-500">
          <Link href="/projects" className="hover:text-amber-300 transition-colors">Проекты</Link>
          <Link href="/new-project" className="hover:text-amber-300 transition-colors">Новый проект</Link>
          <Link href="/settings" className="hover:text-amber-300 transition-colors">Credits</Link>
          <Link href="/login" className="hover:text-amber-300 transition-colors">Вход</Link>
        </nav>
      </div>
      <div className="border-t border-zinc-900/70">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-2
                        text-[11px] font-mono text-zinc-700">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500/70" />
          swarm online
          <span className="ml-auto">© {new Date().getFullYear()} SwarmBuild AI</span>
        </div>
      </div>
    </footer>
  );
}
