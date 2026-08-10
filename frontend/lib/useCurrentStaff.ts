"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Staff, StaffRole } from "@/lib/api";
import { clearToken, getToken } from "@/lib/auth";

/**
 * Garde d'accès pour les écrans staff/cuisine/manager : redirige vers
 * /login si pas de token (ou token invalide/expiré), et vers /login si le
 * rôle ne correspond pas à la page (ex: un serveur qui tape /dashboard
 * directement dans l'URL).
 */
export function useCurrentStaff(allowedRoles?: StaffRole[]): { staff: Staff | null; loading: boolean } {
  const router = useRouter();
  const [staff, setStaff] = useState<Staff | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    if (!getToken()) {
      router.replace("/login");
      return;
    }

    api
      .me()
      .then((current) => {
        if (cancelled) return;
        if (allowedRoles && !allowedRoles.includes(current.role)) {
          router.replace("/login");
          return;
        }
        setStaff(current);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        clearToken();
        router.replace("/login");
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { staff, loading };
}
