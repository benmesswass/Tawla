"use client";

import { useCallback, useEffect, useState } from "react";
import { fr, type Dictionary } from "./fr";
import { ar } from "./ar";

const STORAGE_KEY = "resto-qr-menu:locale";

const DICTIONARIES: Record<string, Dictionary> = { fr, ar };

// Local au parcours client uniquement (page /menu/[qrToken]) — pas de
// cookie/serveur, la préférence est stockée dans le navigateur du client
// qui a scanné le QR, jamais partagée avec le staff.
export function useLocale(): { t: Dictionary; locale: string; toggleLocale: () => void } {
  const [locale, setLocale] = useState<string>("fr");

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved && DICTIONARIES[saved]) setLocale(saved);
  }, []);

  const toggleLocale = useCallback(() => {
    setLocale((prev) => {
      const next = prev === "fr" ? "ar" : "fr";
      window.localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
  }, []);

  return { t: DICTIONARIES[locale], locale, toggleLocale };
}
