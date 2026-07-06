"use client";

import Link from "next/link";
import { downloadUrl } from "@/lib/api";
import type { ArtifactInfo } from "@/lib/types";
import { Icon, IconTile, type IconName } from "@/components/icons";

const META: Record<string, { icon: IconName; desc: string }> = {
  "project.zip": { icon: "package", desc: "Полный архив проекта: файлы, проверки и документы" },
  "README.md": { icon: "bookOpen", desc: "Что внутри и с чего начать" },
  "INSTALL.md": { icon: "wrench", desc: "Пошаговая установка" },
  "business-plan.md": { icon: "briefcase", desc: "Бизнес-план: проблема, решение, монетизация" },
  "pitch-deck-outline.md": { icon: "mic", desc: "Структура питча для инвесторов" },
  "presentation-structure.md": { icon: "presentation", desc: "Скелет презентации по слайдам" },
  "research-report.md": { icon: "flask", desc: "Исследовательский отчёт" },
  "marketing-plan.md": { icon: "megaphone", desc: "Каналы, позиционирование, KPI" },
  "financial-model-draft.md": { icon: "trendingUp", desc: "Драфт финансовой модели" },
  "deployment-guide.md": { icon: "rocket", desc: "Как задеплоить проект" },
  "user-manual.md": { icon: "bookOpen", desc: "Руководство пользователя" },
  "roadmap.md": { icon: "map", desc: "План развития по кварталам" },
  "limitations.md": { icon: "alertTriangle", desc: "Честный список ограничений" },
  "next-steps.md": { icon: "arrowRight", desc: "Рекомендуемые следующие шаги" },
  "cost-report.json": { icon: "receipt", desc: "Публичная сводка использования бюджета" },
  "main-document.md": { icon: "fileText", desc: "Основной документ проекта" },
  "technical-spec-final.md": { icon: "ruler", desc: "Техническая спецификация" },
  "branding-copy.md": { icon: "penLine", desc: "Брендинг и тексты" },
  "security-report.md": { icon: "shield", desc: "Отчёт проверки безопасности" },
};

export default function ArtifactCard({
  projectId,
  artifact,
}: {
  projectId: string;
  artifact: ArtifactInfo;
}) {
  const meta = META[artifact.display_name]
    || { icon: "fileText" as IconName, desc: artifact.path };
  const isZip = artifact.display_name.endsWith(".zip");
  const href = isZip
    ? downloadUrl(`/api/projects/${projectId}/download`)
    : downloadUrl(`/api/projects/${projectId}/artifacts/${artifact.id}/download`);

  return (
    <div className="card card-hover p-4 flex flex-col">
      <div className="flex items-center gap-3">
        <IconTile name={meta.icon} />
        <span className="font-semibold text-sm truncate font-mono">{artifact.display_name}</span>
      </div>
      <p className="text-xs text-zinc-500 mt-2.5 flex-1 leading-relaxed">{meta.desc}</p>
      <div className="flex gap-2 mt-3 text-xs">
        {!isZip && (
          <Link href={`/projects/${projectId}/artifacts?open=${artifact.id}`}
                className="btn-ghost px-3 py-1.5 flex-1 text-center">
            Открыть
          </Link>
        )}
        <a href={href}
           className={`px-3 py-1.5 flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg ${
             isZip ? "btn-primary" : "btn-ghost"}`}>
          <Icon name="download" size={13} />
          Скачать
        </a>
      </div>
    </div>
  );
}
