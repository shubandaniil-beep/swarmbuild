"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, cacheUser } from "@/lib/api";

interface Quote {
  credits_estimate: number;
  credits_min: number;
  credits_max: number;
  token_balance: number;
  surcharge_risk: "low" | "medium" | "high";
  credits_per_usd: number;
  usd_equivalent: number;
  demo_eligible?: boolean;
}

interface PersonalityMode {
  key: string;
  display_name: string;
  hint: string;
}

const BUDGETS = [
  { label: "Trial · 100 credits", value: 1 },
  { label: "Fast Build · 2 000", value: 20 },
  { label: "Small MVP · 4 400", value: 40 },
  { label: "Standard MVP · 12 000", value: 100 },
  { label: "Heavy Build · 26 000", value: 200 },
];

const RISK_LABEL: Record<string, { text: string; cls: string }> = {
  low: { text: "низкий", cls: "text-green-400" },
  medium: { text: "средний", cls: "text-amber-300" },
  high: { text: "высокий", cls: "text-red-400" },
};

const MODES = [
  { key: "auto", label: "Auto-detect", hint: "система сама решает" },
  { key: "code", label: "Code project", hint: "код, repo, README, install guide" },
  { key: "document", label: "Document project", hint: "диплом, исследование, стратегия — без кода" },
  { key: "business", label: "Business package", hint: "бизнес-план, pitch, финмодель" },
  { key: "mixed", label: "Mixed project", hint: "код + документы + презентация" },
];

const OUTPUTS = [
  ["mvp", "MVP / codebase"],
  ["docs", "Документация"],
  ["business_plan", "Бизнес-план"],
  ["pitch_outline", "Pitch outline"],
  ["presentation_structure", "Структура презентации"],
  ["research_report", "Research report"],
  ["technical_spec", "Тех. спецификация"],
  ["marketing_plan", "Маркетинг-план"],
  ["financial_model", "Финмодель (драфт)"],
  ["deployment_guide", "Deployment guide"],
  ["user_manual", "User manual"],
  ["roadmap", "Roadmap"],
  ["branding_copy", "Брендинг / тексты"],
] as const;

const TYPES = [
  ["auto", "Авто-определение"],
  ["code_project", "Code project"],
  ["document_project", "Document project"],
  ["business_project", "Business project"],
  ["presentation_project", "Presentation"],
  ["research_project", "Research"],
  ["telegram_bot", "Telegram-бот"],
  ["mini_crm", "Мини-CRM"],
  ["landing_page", "Landing page"],
  ["web_app", "Web app"],
  ["dashboard", "Dashboard"],
  ["integration", "Integration"],
  ["automation_script", "Automation script"],
  ["python_utility", "Python-утилита"],
  ["saas_mvp", "SaaS MVP"],
  ["mobile_app_concept", "Mobile app concept"],
  ["education_project", "Education project"],
  ["diploma_or_coursework", "Диплом / курсовая"],
  ["pitch_deck", "Pitch deck"],
  ["marketing_pack", "Marketing pack"],
  ["custom", "Custom"],
] as const;

function MagicStart() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function go() {
    if (prompt.trim().length < 10) {
      setError("Опишите идею хотя бы одним предложением.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await api<{ project_id: string; token_balance?: number }>(
        "/api/projects/instant",
        { method: "POST", body: JSON.stringify({ prompt }) },
      );
      if (typeof res.token_balance === "number") {
        cacheUser({ token_balance: res.token_balance });
      }
      router.push(`/projects/${res.project_id}`);
    } catch (err) {
      setError(String(err));
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border border-amber-400/30 bg-amber-400/5 p-6 shadow-[0_0_40px_rgba(245,158,11,0.08)]">
      <p className="kicker mb-1">Проект под ключ</p>
      <h2 className="text-xl font-semibold">Опишите идею — остальное сделаем мы</h2>
      <p className="mt-1 text-sm text-zinc-500">
        Система сама выберет тип проекта, пакет и маршрут сборки, проверит результат
        и отдаст готовый архив. Ничего настраивать не нужно.
      </p>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={4}
        className="input mt-4"
        placeholder="Например: нужен Telegram-бот для записи клиентов автомойки с калькулятором стоимости…"
      />
      {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
      <button
        type="button"
        onClick={go}
        disabled={busy}
        className="btn-primary w-full sm:w-auto px-10 py-4 mt-4 text-base"
      >
        {busy ? "Запускаю сборку…" : "✨ Создать проект под ключ"}
      </button>
    </div>
  );
}

export default function ProjectForm() {
  const router = useRouter();
  const [advanced, setAdvanced] = useState(false);
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [goal, setGoal] = useState("");
  const [budget, setBudget] = useState(5);
  const [custom, setCustom] = useState("");
  const [mode, setMode] = useState("auto");
  const [outputs, setOutputs] = useState<string[]>(["mvp", "docs"]);
  const [ptype, setPtype] = useState("auto");
  const [personality, setPersonality] = useState("balanced");
  const [personalityModes, setPersonalityModes] = useState<PersonalityMode[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [quote, setQuote] = useState<Quote | null>(null);

  const effectiveBudget = custom ? parseFloat(custom) : budget;

  useEffect(() => {
    api<PersonalityMode[]>("/api/projects/personality-modes")
      .then(setPersonalityModes).catch(() => setPersonalityModes([]));
  }, []);

  useEffect(() => {
    if (!effectiveBudget || effectiveBudget <= 0) { setQuote(null); return; }
    let alive = true;
    api<Quote>("/api/projects/estimate", {
      method: "POST", body: JSON.stringify({ budget_usd: effectiveBudget }),
    }).then((q) => { if (alive) setQuote(q); }).catch(() => { if (alive) setQuote(null); });
    return () => { alive = false; };
  }, [effectiveBudget]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await api<{ project_id: string; token_balance?: number }>("/api/projects", {
        method: "POST",
        body: JSON.stringify({
          title,
          brief,
          budget_usd: custom ? parseFloat(custom) : budget,
          requested_outputs: outputs,
          project_type: ptype,
          project_mode: mode,
          personality_mode: personality,
          technical_level: "non_technical",
          user_goal: goal,
        }),
      });
      if (typeof res.token_balance === "number") {
        cacheUser({ token_balance: res.token_balance });
      }
      await api(`/api/projects/${res.project_id}/start`, { method: "POST" });
      router.push(`/projects/${res.project_id}`);
    } catch (err) {
      setError(String(err));
      setBusy(false);
    }
  }

  const input = "input";

  if (!advanced) {
    return (
      <div className="space-y-6">
        <MagicStart />
        <button
          type="button"
          onClick={() => setAdvanced(true)}
          className="text-sm text-zinc-500 hover:text-zinc-300 underline underline-offset-4"
        >
          Настроить вручную (тип, бюджет, результаты)
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-6">
      <button
        type="button"
        onClick={() => setAdvanced(false)}
        className="text-sm text-zinc-500 hover:text-zinc-300 underline underline-offset-4"
      >
        ← Вернуться к режиму «под ключ»
      </button>
      <div>
        <label className="block text-sm text-zinc-400 mb-1">Название проекта</label>
        <input value={title} onChange={(e) => setTitle(e.target.value)} required
               className={input} placeholder="Car Wash CRM" />
      </div>

      <div>
        <label className="block text-sm text-zinc-400 mb-1">Описание / бриф</label>
        <textarea value={brief} onChange={(e) => setBrief(e.target.value)} required rows={5}
                  className={input}
                  placeholder="Нужен сайт, CRM, Telegram-бот и калькулятор для автомойки…" />
      </div>

      <div>
        <label className="block text-sm text-zinc-400 mb-1">Что должно получиться в идеале</label>
        <input value={goal} onChange={(e) => setGoal(e.target.value)} className={input}
               placeholder="Например: получить готовый пакет, который можно показать клиенту или инвестору" />
      </div>

      <div>
        <label className="block text-sm text-zinc-400 mb-2">Режим проекта</label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {MODES.map((m) => (
            <button key={m.key} type="button" onClick={() => setMode(m.key)}
                    className={`text-left px-4 py-3 rounded-xl border transition-all duration-200 ${
                      mode === m.key
                        ? "border-amber-400/70 bg-amber-400/5 shadow-[0_0_16px_rgba(245,158,11,0.12)]"
                        : "border-zinc-800 hover:border-zinc-600 bg-zinc-900/30"}`}>
              <span className={`font-medium text-sm ${mode === m.key ? "text-amber-300" : ""}`}>
                {m.label}
              </span>
              <span className="block text-xs text-zinc-500 mt-0.5">{m.hint}</span>
            </button>
          ))}
        </div>
      </div>

      {personalityModes.length > 0 && (
        <div>
          <label className="block text-sm text-zinc-400 mb-2">
            Стиль сборки <span className="text-zinc-600">(влияет на решения роя)</span>
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {personalityModes.map((m) => (
              <button key={m.key} type="button" onClick={() => setPersonality(m.key)}
                      className={`text-left px-4 py-3 rounded-xl border transition-all duration-200 ${
                        personality === m.key
                          ? "border-amber-400/70 bg-amber-400/5 shadow-[0_0_16px_rgba(245,158,11,0.12)]"
                          : "border-zinc-800 hover:border-zinc-600 bg-zinc-900/30"}`}>
                <span className={`font-medium text-sm ${personality === m.key ? "text-amber-300" : ""}`}>
                  {m.display_name}
                </span>
                <span className="block text-xs text-zinc-500 mt-0.5">{m.hint}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div>
        <label className="block text-sm text-zinc-400 mb-2">Бюджет</label>
        <div className="flex flex-wrap gap-2">
          {BUDGETS.map((b) => (
            <button key={b.value} type="button"
                    onClick={() => { setBudget(b.value); setCustom(""); }}
                    className={`px-4 py-2.5 rounded-xl border text-sm transition-all duration-200 ${
                      !custom && budget === b.value
                        ? "border-amber-400/70 text-amber-300 bg-amber-400/5 shadow-[0_0_16px_rgba(245,158,11,0.12)]"
                        : "border-zinc-800 text-zinc-300 hover:border-zinc-600 bg-zinc-900/30"}`}>
              {b.label}
            </button>
          ))}
          <input value={custom} onChange={(e) => setCustom(e.target.value)}
                 placeholder="Custom $" type="number" min="1"
                 className="input w-28" />
        </div>
      </div>

      <div>
        <label className="block text-sm text-zinc-400 mb-2">Желаемые результаты</label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {OUTPUTS.map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={outputs.includes(key)}
                     onChange={(e) =>
                       setOutputs(e.target.checked
                         ? [...outputs, key]
                         : outputs.filter((x) => x !== key))} />
              {label}
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm text-zinc-400 mb-1">Тип проекта</label>
        <select value={ptype} onChange={(e) => setPtype(e.target.value)}
                className="input w-auto">
          {TYPES.map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
      </div>

      {quote && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 text-sm space-y-1.5">
          <div className="flex justify-between">
            <span className="text-zinc-400">Оценка проекта</span>
            <span className="font-medium">
              {quote.credits_min.toLocaleString("ru-RU")}–{quote.credits_max.toLocaleString("ru-RU")} credits
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-400">Эквивалент</span>
            <span>${quote.usd_equivalent.toLocaleString("ru-RU")} · {quote.credits_per_usd} credits = $1</span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-400">Ваш баланс</span>
            <span>{quote.token_balance.toLocaleString("ru-RU")} credits</span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-400">Вероятность доплаты</span>
            <span className={RISK_LABEL[quote.surcharge_risk]?.cls}>
              {RISK_LABEL[quote.surcharge_risk]?.text ?? quote.surcharge_risk}
            </span>
          </div>
          {quote.demo_eligible && (
            <p className="text-xs text-amber-300 pt-1">
              Trial-запуск доступен: минимальный проект будет списывать стартовые credits по фазам.
            </p>
          )}
          {quote.surcharge_risk === "high" && (
            <p className="text-xs text-zinc-500 pt-1">
              Баланса может не хватить на весь проект — сборка остановится и попросит пополнение.
            </p>
          )}
        </div>
      )}

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <button disabled={busy} className="btn-primary px-9 py-3.5">
        {busy ? "Запускаю проект…" : "Создать и запустить →"}
      </button>
    </form>
  );
}
