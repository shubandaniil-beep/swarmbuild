"use client";

import Link from "next/link";
import { Suspense, use, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { ArtifactInfo } from "@/lib/types";
import ArtifactList from "@/components/ArtifactList";
import RequireAuth from "@/components/RequireAuth";

function ArtifactsInner({ id }: { id: string }) {
  const [artifacts, setArtifacts] = useState<ArtifactInfo[]>([]);
  const openId = useSearchParams().get("open");

  useEffect(() => {
    api<ArtifactInfo[]>(`/api/projects/${id}/artifacts`).then(setArtifacts).catch(() => {});
  }, [id]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">Финальные файлы</h1>
        <Link href={`/projects/${id}`} className="text-sm text-zinc-500 hover:text-white">
          ← к проекту
        </Link>
      </div>
      <ArtifactList projectId={id} artifacts={artifacts} initialOpenId={openId} />
    </div>
  );
}

export default function ArtifactsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <RequireAuth>
      <Suspense fallback={<p className="text-zinc-500">Загрузка…</p>}>
        <ArtifactsInner id={id} />
      </Suspense>
    </RequireAuth>
  );
}
