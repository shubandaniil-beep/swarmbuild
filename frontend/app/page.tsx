import Link from "next/link";
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

const STEPS = [
  { n: "01", title: "Опишите идею", text: "Обычным языком: что нужно сделать, для кого и какой результат вы хотите получить." },
  { n: "02", title: "Система строит маршрут", text: "Платформа сама выбирает формат результата, бюджет и порядок сборки." },
  { n: "03", title: "Проверка до выдачи", text: "Результат проходит внутреннюю проверку: слабые места чинятся до упаковки." },
  { n: "04", title: "Скачайте пакет", text: "Код, документы, план запуска, бизнес-материалы и честные ограничения — одним архивом." },
];

const EXAMPLES = [
  { emoji: "🚿", title: "Автомойка", text: "Сайт + мини-CRM + Telegram-бот + калькулятор услуг", mode: "mixed", budget: "$100" },
  { emoji: "🏥", title: "Клиника", text: "Система записи + CRM + документы", mode: "code", budget: "$100" },
  { emoji: "🎓", title: "Студент", text: "Диплом + структура презентации", mode: "document", budget: "$40" },
  { emoji: "🚀", title: "Стартап", text: "MVP + pitch deck + бизнес-план", mode: "mixed", budget: "$200" },
  { emoji: "🏪", title: "Малый бизнес", text: "Лендинг + приём заявок + автоматизация", mode: "code", budget: "$40" },
  { emoji: "📊", title: "Аналитик", text: "Research report + маркетинг-план", mode: "business", budget: "$20" },
];

const TARIFFS = [
  { name: "Free Test", price: "100 credits", scope: "1 минимальная генерация", desc: "Пробный запуск после регистрации без оплаты" },
  { name: "Fast Build", price: "$20", scope: "быстрый пакет", desc: "Простые code/document проекты" },
  { name: "Small MVP", price: "$40", scope: "базовая сборка", desc: "MVP с проверкой готовности" },
  { name: "Standard MVP", price: "$100", scope: "расширенная сборка", desc: "Код, документы и бизнес-материалы", featured: true },
  { name: "Heavy Build", price: "$200", scope: "максимальный пакет", desc: "Больше глубины, проверок и материалов" },
];

const DELIVERABLES = [
  ["📦", "Рабочий скелет кода", "repo + README + INSTALL + .env.example"],
  ["📐", "План реализации", "цель, логика продукта, ограничения, next steps"],
  ["💼", "Бизнес-пакет", "бизнес-план, pitch-outline, финмодель"],
  ["🔬", "Документы", "research report, презентация, user manual"],
  ["⚠️", "Честные ограничения", "что готово сейчас и что нужно усилить"],
  ["🧾", "Отчёт по бюджету", "сколько бюджета использовано и сколько осталось"],
];

export default function Home() {
  return (
    <div className="space-y-28 pb-20">
      {/* ===== Hero ===== */}
      <section className="relative pt-16 -mx-6 px-6">
        <div className="absolute inset-0 grid-bg pointer-events-none" />
        <div className="relative grid lg:grid-cols-2 gap-12 items-center max-w-5xl mx-auto">
          <div>
            <p className="kicker mb-4 animate-fade-in-up">AI Project Factory</p>
            <h1 className="text-6xl sm:text-7xl font-black leading-[0.98] tracking-tighter animate-fade-in-up delay-1">
              Одна идея.
              <br />
              <span className="hero-gradient-text">Готовый проект.</span>
            </h1>
            <p className="mt-7 text-zinc-300 text-lg leading-relaxed max-w-md animate-fade-in-up delay-2">
              Вы описываете задачу простыми словами. Платформа сама собирает
              маршрут сборки, проверяет результат и отдаёт готовый пакет файлов под ваш бюджет.
            </p>
            <div className="mt-10 flex flex-wrap gap-3 animate-fade-in-up delay-3">
              <Link href="/login" className="btn-primary px-10 py-4 text-lg">
                Попробовать бесплатно →
              </Link>
              <Link href="/login" className="btn-ghost px-8 py-4 text-lg">
                Войти
              </Link>
            </div>
            <p className="mt-5 text-xs text-zinc-600 animate-fade-in-up delay-3">
              100 credits = $1. После регистрации доступен один минимальный demo-запуск.
            </p>
          </div>

          {/* live factory preview */}
          <div className="terminal animate-fade-in-up delay-2" aria-hidden>
            <div className="terminal-bar">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-400/70" />
              <span className="w-2.5 h-2.5 rounded-full bg-green-500/70" />
              <span className="ml-3 text-zinc-500">factory — car-wash-suite</span>
              <span className="ml-auto flex items-center gap-1.5 text-indigo-300">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse-dot" />
                running
              </span>
            </div>
            <div className="h-64 overflow-hidden px-4 py-3 relative">
              <div className="animate-ticker space-y-1.5">
                {[...TERMINAL_LINES, ...TERMINAL_LINES].map(([t, tag, msg], i) => (
                  <div key={i} className="flex gap-2 whitespace-nowrap">
                    <span className="text-zinc-700">{t}</span>
                    <span className="text-indigo-400/80">[{tag}]</span>
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
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {STEPS.map((s, i) => (
            <div key={s.n} className="card card-hover p-6 relative overflow-hidden">
              <div className="absolute -top-5 -right-1 text-8xl font-black text-indigo-500/15 select-none tracking-tighter">
                {s.n}
              </div>
              <div className="relative">
                <div className="h-1.5 rounded-full bg-indigo-400 mb-5"
                     style={{ width: `${1.5 + i * 0.75}rem`, opacity: 0.5 + i * 0.16 }} />
                <h3 className="text-lg font-bold tracking-tight">{s.title}</h3>
                <p className="mt-2 text-sm text-zinc-400 leading-relaxed">{s.text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ===== Why routing ===== */}
      <section className="card-glow p-10">
        <p className="kicker mb-2">Наш профиль</p>
        <h2 className="section-title mb-5">Собственная AI-маршрутизация</h2>
        <div className="grid md:grid-cols-2 gap-8 text-[15px] text-zinc-300 leading-relaxed">
          <p>
            Обычный AI-чат отвечает один раз и оставляет вам разбираться, что с этим
            делать дальше. SwarmBuild превращает идею в набор файлов, инструкций и
            следующих шагов.
          </p>
          <p>
            Внутри работает закрытый алгоритм маршрутизации моделей. Мы не раскрываем
            его механику, но именно он помогает собрать, проверить и упаковать результат
            в понятный клиенту проектный пакет.
          </p>
        </div>
        <div className="mt-7 flex flex-wrap gap-2">
          {["маршрут", "пакет", "проверка", "бюджет", "готовность"].map((m) => (
            <span key={m} className="chip chip-indigo font-mono">{m}</span>
          ))}
        </div>
      </section>

      {/* ===== Examples ===== */}
      <section>
        <SectionHeader kicker="Примеры проектов" title="Не только код"
                       sub="Code, document, business и mixed режимы — платформа адаптирует итоговый пакет под задачу." />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {EXAMPLES.map((e) => (
            <div key={e.title} className="card card-hover p-5">
              <div className="text-3xl">{e.emoji}</div>
              <div className="mt-3 text-base font-bold tracking-tight">{e.title}</div>
              <p className="text-sm text-zinc-400 mt-1 leading-relaxed">{e.text}</p>
              <div className="mt-4 flex gap-2">
                <span className="chip font-mono">{e.mode}</span>
                <span className="chip chip-indigo">{e.budget}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ===== Tariffs ===== */}
      <section>
        <SectionHeader kicker="Тарифы" title="Бюджет определяет глубину сборки"
                       sub="Больше бюджет — глубже проработка, больше проверок и полнее итоговый пакет." />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 items-stretch">
          {TARIFFS.map((t) => (
            <div key={t.name}
                 className={`${t.featured
                   ? "card-glow lg:scale-[1.04] lg:z-10 shadow-2xl"
                   : "card card-hover"} p-6 flex flex-col`}>
              {t.featured && <span className="chip chip-indigo self-start mb-3">★ популярный</span>}
              <div className="font-bold tracking-tight">{t.name}</div>
              <div className={`${t.featured ? "text-5xl" : "text-4xl"} font-black text-indigo-400 mt-2 tracking-tighter`}>{t.price}</div>
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
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {DELIVERABLES.map(([icon, title, text]) => (
            <div key={title} className="card card-hover p-5 flex gap-4">
              <span className="text-3xl shrink-0">{icon}</span>
              <div>
                <div className="font-bold text-[15px] tracking-tight">{title}</div>
                <p className="text-xs text-zinc-500 mt-1 leading-relaxed">{text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ===== CTA ===== */}
      <section className="relative text-center card-glow px-8 py-16 overflow-hidden">
        <div className="absolute inset-0 grid-bg pointer-events-none" />
        <div className="relative">
          <h2 className="text-4xl sm:text-5xl font-black tracking-tighter">
            Вы отправляете идею.
            <br />
            <span className="hero-gradient-text">Фабрика собирает пакет.</span>
          </h2>
          <Link href="/login" className="btn-primary inline-flex mt-9 px-10 py-4 text-lg">
            Зарегистрироваться и попробовать →
          </Link>
        </div>
      </section>
    </div>
  );
}
