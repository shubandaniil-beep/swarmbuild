"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api, cacheUser, clearAuth, type SessionUser } from "@/lib/api";
import { PageLoader } from "@/components/ui";

export default function RequireAuth({
  children,
  adminOnly = false,
}: {
  children: ReactNode;
  adminOnly?: boolean;
}) {
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    let alive = true;
    api<SessionUser>("/api/auth/me")
      .then((user) => {
        if (!alive) return;
        cacheUser(user);
        if (adminOnly && user.role !== "admin") {
          location.href = "/admin-login";
          return;
        }
        setAllowed(true);
      })
      .catch(() => {
        if (!alive) return;
        clearAuth();
        location.href = adminOnly ? "/admin-login" : "/login";
      });
    return () => { alive = false; };
  }, [adminOnly]);

  if (!allowed) return <PageLoader label="Проверяю доступ…" />;
  return <>{children}</>;
}
