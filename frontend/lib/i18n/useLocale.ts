"use client";

import { useCallback, useEffect, useState } from "react";
import { fr, type Dictionary } from "./fr";
import { ar } from "./ar";
import { en } from "./en";
import { currentMarket } from "@/lib/market";

const STORAGE_KEY = "resto-qr-menu:locale";

const ALL_DICTIONARIES: Record<string, Dictionary> = { fr, ar, en };

// Local au parcours client uniquement (page /menu/[qrToken]) — pas de
// cookie/serveur, la préférence est stockée dans le navigateur du client
// qui a scanné le QR, jamais partagée avec le staff.
//
// Les langues disponibles suivent le marché (`currentMarket().languages`,
// voir MARCHE_FRANCE.md §3.2 F5-A9) — fr/ar en Tunisie, fr/en en France.
// Toujours exactement deux langues aujourd'hui dans les deux marchés, donc
// un simple bouton "basculer" reste suffisant ; le jour où un marché en
// proposerait trois, ce sera un vrai sélecteur à faire, pas un patch ici.
export function useLocale(): { t: Dictionary; locale: string; toggleLocale: () => void } {
  const { languages } = currentMarket();
  const defaultLocale = languages[0] ?? "fr";
  const [locale, setLocale] = useState<string>(defaultLocale);

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved && languages.includes(saved)) setLocale(saved);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `languages` est figé pour tout le déploiement (une seule lecture au montage suffit)
  }, []);

  // `<html lang>` est rendu côté serveur, où la langue du client n'est pas
  // encore connue : sans cette synchronisation il restait `fr` pendant tout un
  // parcours en arabe, et un lecteur d'écran prononçait l'arabe avec les
  // règles du français.
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const toggleLocale = useCallback(() => {
    setLocale((prev) => {
      const currentIndex = languages.indexOf(prev);
      const next = languages[(currentIndex + 1) % languages.length] ?? defaultLocale;
      window.localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { t: ALL_DICTIONARIES[locale] ?? fr, locale, toggleLocale };
}
