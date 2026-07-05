"use client";

import { useCallback, useEffect, useState } from "react";
import { api, downloadUrl } from "@/lib/api";
import type { ArtifactInfo } from "@/lib/types";

export default function ArtifactList({
  projectId,
  artifacts,
  initialOpenId,
}: {
  projectId: string;
  artifacts: ArtifactInfo[];
  initialOpenId?: string | null;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");

  const open = useCallback(async (a: ArtifactInfo) => {
    if (a.display_name.endsWith(".zip")) {
      window.location.href = downloadUrl(`/api/projects/${projectId}/download`);
      return;
    }
    setSelected(a.id);
    setContent("Загрузка…");
    try {
      const res = await api<{ content: string }>(
        `/api/projects/${projectId}/artifacts/${a.id}/content`,
      );
      setContent(res.content);
    } catch (e) {
      setContent(String(e));
    }
  }, [projectId]);

  useEffect(() => {
    if (initialOpenId && !selected) {
      const target = artifacts.find((a) => a.id === initialOpenId);
      if (target) open(target);
    }
  }, [initialOpenId, artifacts, selected, open]);

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <ul className="space-y-1 text-sm max-h-[70vh] overflow-y-auto log-scroll">
        {artifacts.map((a) => (
          <li key={a.id}>
            <button
              onClick={() => open(a)}
              className={`text-left w-full px-2 py-1 rounded hover:bg-zinc-900 ${
                selected === a.id ? "text-indigo-300" : "text-zinc-300"
              }`}
            >
              {a.display_name.endsWith(".zip") ? "📦" : "📄"} {a.display_name}
            </button>
          </li>
        ))}
        {artifacts.length === 0 && (
          <li className="text-zinc-600">Финальные файлы ещё готовятся</li>
        )}
      </ul>
      <pre className="card p-4 text-xs whitespace-pre-wrap max-h-[70vh] overflow-y-auto log-scroll">
        {content || "Выберите файл слева"}
      </pre>
    </div>
  );
}
