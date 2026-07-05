"use client";

import Link from "next/link";
import { downloadUrl } from "@/lib/api";
import type { ArtifactInfo } from "@/lib/types";

const META: Record<string, { icon: string; desc: string }> = {
  "project.zip": { icon: "📦", desc: "Полный архив проекта: файлы, проверки и документы" },
  "README.md": { icon: "📘", desc: "Что внутри и с чего начать" },
  "INSTALL.md": { icon: "🛠", desc: "Пошаговая установка" },
  "business-plan.md": { icon: "💼", desc: "Бизнес-план: проблема, решение, монетизация" },
  "pitch-deck-outline.md": { icon: "🎤", desc: "Структура питча для инвесторов" },
  "presentation-structure.md": { icon: "🖥", desc: "Скелет презентации по слайдам" },
  "research-report.md": { icon: "🔬", desc: "Исследовательский отчёт" },
  "marketing-plan.md": { icon: "📣", desc: "Каналы, позиционирование, KPI" },
  "financial-model-draft.md": { icon: "📈", desc: "Драфт финансовой модели" },
  "deployment-guide.md": { icon: "🚀", desc: "Как задеплоить проект" },
  "user-manual.md": { icon: "📖", desc: "Руководство пользователя" },
  "roadmap.md": { icon: "🗺", desc: "План развития по кварталам" },
  "limitations.md": { icon: "⚠️", desc: "Честный список ограничений" },
  "next-steps.md": { icon: "👣", desc: "Рекомендуемые следующие шаги" },
  "cost-report.json": { icon: "🧾", desc: "Публичная сводка использования бюджета" },
  "main-document.md": { icon: "📄", desc: "Основной документ проекта" },
  "technical-spec-final.md": { icon: "📐", desc: "Техническая спецификация" },
  "branding-copy.md": { icon: "✨", desc: "Брендинг и тексты" },
};

export default function ArtifactCard({
  projectId,
  artifact,
}: {
  projectId: string;
  artifact: ArtifactInfo;
}) {
  const meta = META[artifact.display_name] || { icon: "📄", desc: artifact.path };
  const isZip = artifact.display_name.endsWith(".zip");
  const href = isZip
    ? downloadUrl(`/api/projects/${projectId}/download`)
    : downloadUrl(`/api/projects/${projectId}/artifacts/${artifact.id}/download`);

  return (
    <div className="card p-4 flex flex-col">
      <div className="flex items-center gap-2">
        <span className="text-xl">{meta.icon}</span>
        <span className="font-medium text-sm truncate">{artifact.display_name}</span>
      </div>
      <p className="text-xs text-zinc-500 mt-2 flex-1 leading-relaxed">{meta.desc}</p>
      <div className="flex gap-2 mt-3 text-xs">
        {!isZip && (
            <Link href={`/projects/${projectId}/artifacts?open=${artifact.id}`}
                className="btn-ghost px-3 py-1.5 flex-1 text-center">
            Открыть
          </Link>
        )}
        <a href={href}
           className={`px-3 py-1.5 flex-1 text-center rounded-lg ${
             isZip ? "btn-primary" : "btn-ghost"}`}>
          Скачать
        </a>
      </div>
    </div>
  );
}
