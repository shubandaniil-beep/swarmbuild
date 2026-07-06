import Link from "next/link";
import { Icon, IconTile, type IconName } from "@/components/icons";
import { SectionHeader } from "@/components/ui";

const TERMINAL_LINES = [
  ["12:00:04", "idea", "Идея принята · цель и формат результата определены"],
  ["12:00:06", "route", "Подобран оптимальный путь сборки"],
  ["12:00:11", "plan", "План проекта готов · лишний объём убран"],
  ["12:00:19", "check", "Риски проверены до сборки результата"],
  ["12:00:27", "build", "Файлы проекта создаются и связываются между собой"],
  ["12:00:33", "review", "Система нашла слабые места и отправила их на исправление"],
  ["12:00:48", "repair", "Недочёты исправлены · инструкции обновлены"],
  ["12:01:15", "package", "Готов финальный пакет: файлы, план, ограничения"],
  ["12:01:21", "ready", "project.zip готов к скачиванию"],
];

const STEPS: { icon: IconName; title: string; text: string }[] = [
  { icon: "penLine", title: "Опишите идею",
    text: "Обычным языком: что нужно сделать, для кого и какой результат вы хотите получить." },
  { icon: "map", title: "Система строит маршрут",
    text: "Платформа сама выбирает формат результата, бюджет и порядок сборки." },
  { icon: "search", title: "Проверка до выдачи",
    text: "Результат проходит внутреннюю проверку: слабые места чинятся до упаковки." },
  { icon: "package", title: "Скачайте пакет",
    text: "Код, документы, план запуска и честные ограничения — одним архивом." },
];

const EXAMPLES: { icon: IconName; title: string; text: string; mode: string; budget: string }[] = [
  { icon: "layers", title: "Автомойка", text: "Сайт + мини-CRM + Telegram-бот + калькулятор услуг", mode: "mixed", budget: "$100" },
  { icon: "code", title: "Клиника", text: "Система записи + CRM + документы", mode: "code", budget: "$100" },
  { icon: "fileText", title: "Студент", text: "Диплом + структура презентации", mode: "document", budget: "$40" },
  { icon: "rocket", title: "Стартап", text: "MVP + pitch deck + бизнес-план", mode: "mixed", budget: "$200" },
  { icon: "bolt", title: "Малый бизнес", text: "Лендинг + приём заявок + автоматизация", mode: "code", budget: "$40" },
  { icon: "trendingUp", title: "Аналитик", text: "Research report + маркетинг-план", mode: "business", budget: "$20" },
];

const TARIFFS = [
  { name: "Free Test", price: "100 cr", scope: "1 минимальная генерация", desc: "Пробный запуск после регистрации без оплаты" },
  { name: "Fast Build", price: "$20", scope: "быстрый пакет", desc: "Простые code/document проекты" },
  { name: "Standard MVP", price: "$100", scope: "расширенная сборка", desc: "Код, документы и бизнес-материалы", featured: true },
  { name: "Heavy Build", price: "$200", scope: "максимальный пакет", desc: "Больше глубины, проверок и материалов" },
];

const DELIVERABLES: [IconName, string, string][] = [
  ["code", "Рабочий скелет кода", "repo + README + INSTALL + .env.example"],
  ["ruler", "План реализации", "цель, логика продукта, ограничения, next steps"],
  ["briefcase", "Бизнес-пакет", "бизнес-план, pitch-outline, финмодель"],
  ["flask", "Документы", "research report, презентация, user manual"],
  ["alertTriangle", "Честные ограничения", "что готово сейчас и что нужно усилить"],
  ["receipt", "Отчёт по бюджету", "сколько использовано и сколько осталось"],
];

const ROTATION_ROLES = ["lead", "critic", "builder", "reviewer", "repairer", "judge", "packager"];

export default function Home() {
  return (
    <div className="space-y-24 sm:space-y-28 pb-8">
      {/* ===== Hero ===== */}
      <section className="relative pt-14 sm:pt-16 -mx-4 sm:-mx-6 px-4 sm:px-6">
        <div className="absolute inset-0 grid-bg pointer-events-none" />
        <div className="relative grid grid-cols-1 lg:grid-cols-2 gap-12 items-center max-w-5xl mx-auto">
          <div>
            <p className="kicker mb-4 flex items-center gap-2 animate-fade-in-up">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse-dot" />
              Rotating Swarm · AI Project Factory
            </p>
            <h1 className="text-5xl sm:text-7xl font-extrabold leading-[0.98] tracking-tighter animate-fade-in-up delay-1">
              Одна идея.
              <br />
              <span className="hero-gradient-text">Готовый проект.</span>
            </h1>
            <p className="mt-7 text-zinc-300 text-lg leading-relaxed max-w-md animate-fade-in-up delay-2">
              Вы описываете задачу простыми словами. Рой AI-агентов собирает
              маршрут, проверяет результат и отдаёт пакет файлов под ваш бюджет.
            </p>
            <div className="mt-10 flex flex-wrap gap-3 animate-fade-in-up delay-3">
              <Link href="/login" className="btn-primary px-8 sm:px-10 py-4 text-lg">
                Попробовать бесплатно
                <Icon name="arrowRight" size={18} />
              </Link>
              <Link href="/login" className="btn-ghost px-8 py-4 text-lg">
                Войти
              </Link>
            </div>
            <p className="mt-5 font-mono text-[11px] text-zinc-600 animate-fade-in-up delay-3">
              100 credits = $1 · стартовый баланс покрывает один trial-запуск
            </p>
          </div>

          {/* живой лог фабрики */}
          <div className="terminal animate-fade-in-up delay-2" aria-hidden>
            <div className="terminal-bar">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400/70" />
              <span className="w-2.5 h-2.5 rounded-full bg-green-500/70" />
              <span className="ml-3 text-zinc-500">factory — car-wash-suite</span>
              <span className="ml-auto flex items-center gap-1.5 text-amber-300">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse-dot" />
                running
              </span>
            </div>
            <div className="h-64 overflow-hidden px-4 py-3 relative">
              <div className="animate-ticker space-y-1.5">
                {[...TERMINAL_LINES, ...TERMINAL_LINES].map(([t, tag, msg], i) => (
                  <div key={i} className="flex gap-2 whitespace-nowrap">
                    <span className="text-zinc-700">{t}</span>
                    <span className="text-amber-400/80">[{tag}]</span>
                    <span className="text-zinc-400">{msg}</span>
                  </div>
                ))}
              </div>
              <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-zinc-950 to-transparent" />
            </div>
          </div>
        </div>
      </section>

      {/* ===== How it works ===== */}
      <section>
        <SectionHeader kicker="Как это работает"
                       title="Одна кнопка вместо недели переписок" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {STEPS.map((s, i) => (
            <div key={s.title} className="card card-hover p-6 relative overflow-hidden">
              <div className="absolute -top-4 -right-1 font-mono text-7xl font-bold
                              text-amber-500/10 select-none">
                {String(i + 1).padStart(2, "0")}
              </div>
              <div className="relative">
                <IconTile name={s.icon} size={38} />
                <h3 className="mt-4 text-lg font-bold tracking-tight">{s.title}</h3>
                <p className="mt-2 text-sm text-zinc-400 leading-relaxed">{s.text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ===== Rotation — the actual mechanism ===== */}
      <section className="card-glow p-8 sm:p-10">
        <p className="kicker mb-2">Механика</p>
        <h2 className="section-title mb-5">Рой, который меняется ролями</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-[15px] text-zinc-300 leading-relaxed">
          <p>
            Обычный AI-чат отвечает один раз и оставляет вам разбираться с
            результатом. Здесь над проектом работает команда агентов, и ни один
            не остаётся судьёй собственной работы: автор кода на следующей фазе
            становится критиком, критик — сборщиком.
          </p>
          <p>
            Каждая фаза заканчивается проверкой выхода: ревью, ремонт слабых
            мест, финальный аудит. Что не дотянуло до планки — честно попадает
            в limitations.md, а не прячется за красивой обложкой.
          </p>
        </div>
        <div className="mt-7 flex flex-wrap items-center gap-2 font-mono text-xs">
          {ROTATION_ROLES.map((r, i) => (
            <span key={r} className="flex items-center gap-2">
              <span className="chip chip-accent">{r}</span>
              {i < ROTATION_ROLES.length - 1 && (
                <Icon name="arrowRight" size={12} className="text-zinc-700" />
              )}
            </span>
          ))}
        </div>
      </section>

      {/* ===== Examples ===== */}
      <section>
        <SectionHeader kicker="Примеры проектов" title="Не только код"
                       sub="Code, document, business и mixed режимы — платформа адаптирует итоговый пакет под задачу." />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {EXAMPLES.map((e) => (
            <div key={e.title} className="card card-hover p-5">
              <IconTile name={e.icon} />
              <div className="mt-3 text-base font-bold tracking-tight">{e.title}</div>
              <p className="text-sm text-zinc-400 mt-1 leading-relaxed">{e.text}</p>
              <div className="mt-4 flex gap-2 font-mono">
                <span className="chip">{e.mode}</span>
                <span className="chip chip-accent">{e.budget}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ===== Tariffs ===== */}
      <section>
        <SectionHeader kicker="Тарифы" title="Бюджет определяет глубину сборки"
                       sub="Больше бюджет — глубже проработка, больше проверок и полнее итоговый пакет." />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-stretch">
          {TARIFFS.map((t) => (
            <div key={t.name}
                 className={`${t.featured
                   ? "card-glow lg:scale-[1.04] lg:z-10 shadow-2xl"
                   : "card card-hover"} p-6 flex flex-col`}>
              {t.featured && <span className="chip chip-accent self-start mb-3">популярный</span>}
              <div className="font-bold tracking-tight">{t.name}</div>
              <div className={`${t.featured ? "text-5xl" : "text-4xl"}
                               font-extrabold text-amber-400 mt-2 tracking-tighter tabular`}>
                {t.price}
              </div>
              <div className="text-xs text-zinc-500 mt-1.5 font-mono">{t.scope}</div>
              <p className="text-sm text-zinc-400 mt-3 flex-1 leading-relaxed">{t.desc}</p>
              <Link href="/login"
                    className={`${t.featured ? "btn-primary" : "btn-ghost"} text-center text-sm px-4 py-2.5 mt-5`}>
                Выбрать
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* ===== Deliverables ===== */}
      <section>
        <SectionHeader kicker="Что вы получаете" title="Пакет, а не переписку" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {DELIVERABLES.map(([icon, title, text]) => (
            <div key={title} className="card card-hover p-5 flex gap-4">
              <IconTile name={icon} />
              <div>
                <div className="font-bold text-[15px] tracking-tight">{title}</div>
                <p className="text-xs text-zinc-500 mt-1 leading-relaxed">{text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ===== CTA ===== */}
      <section className="relative text-center card-glow px-6 sm:px-8 py-14 sm:py-16 overflow-hidden">
        <div className="absolute inset-0 grid-bg pointer-events-none" />
        <div className="relative">
          <h2 className="text-4xl sm:text-5xl font-extrabold tracking-tighter">
            Вы отправляете идею.
            <br />
            <span className="hero-gradient-text">Фабрика собирает пакет.</span>
          </h2>
          <Link href="/login" className="btn-primary inline-flex mt-9 px-10 py-4 text-lg">
            Зарегистрироваться
            <Icon name="arrowRight" size={18} />
          </Link>
        </div>
      </section>
    </div>
  );
}
