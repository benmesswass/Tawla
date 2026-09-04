"use client";

import { useCallback, useEffect, useState } from "react";
import { fr, type Dictionary } from "./fr";
import { ar } from "./ar";
import { en } from "./en";
import { currentMarket } from "@/lib/market";

const STORAGE_KEY = "resto-qr-menu:locale";

const DICTIONARIES: Record<string, Dictionary> = { fr, ar, en };

// Langues RÉELLEMENT proposées par CE déploiement — jamais les trois en dur :
// `Market.languages` (Tunisie : fr/ar, France : fr/en, F5/A9) est la seule
// source de vérité, même principe que `currentMarket` pour la devise ou le
// fuseau ailleurs dans le code. Sans ce filtre, le marché français
// proposerait encore la derja tunisienne au bascule, alors qu'aucun client
// français ne l'a jamais demandée.
export const AVAILABLE_LOCALES: readonly string[] = currentMarket.languages;

// Prochaine langue dans le cycle — exportée pour que les composants qui ont
// besoin de la CONNAÎTRE À L'AVANCE (ex: l'attribut `lang` du bouton lui-même,
// voir confidentialite/page.tsx) ne dupliquent pas cette logique en dur
// (bug réel avant A9 : `locale === "fr" ? "ar" : "fr"` codé en dur dans le
// composant, resterait faux sur un marché fr/en).
export function nextLocaleOf(locale: string, locales: readonly string[] = AVAILABLE_LOCALES): string {
  const index = locales.indexOf(locale);
  return locales[(index + 1) % locales.length];
}

// Nom affiché sur le bouton de bascule, dans SA PROPRE langue ("English",
// "عربي") — dérivé de `nextLocaleOf`, jamais recalculé séparément : avant
// A9bis, chaque dictionnaire (fr.ts/en.ts/ar.ts) portait son propre
// `localeSwitchLabel` codé en dur (`currentMarket.languages.includes("en") ?
// "English" : "عربي"` côté fr.ts), une duplication qui ne resterait juste
// que pour exactement les paires de langues déjà vues.
const LOCALE_NAMES: Record<string, string> = { fr: "Français", en: "English", ar: "عربي" };

export function localeSwitchLabel(locale: string, locales: readonly string[] = AVAILABLE_LOCALES): string {
  const next = nextLocaleOf(locale, locales);
  return LOCALE_NAMES[next] ?? next;
}

// Local au parcours client uniquement (page /menu/[qrToken]) — pas de
// cookie/serveur, la préférence est stockée dans le navigateur du client
// qui a scanné le QR, jamais partagée avec le staff.
export function useLocale(): { t: Dictionary; locale: string; toggleLocale: () => void } {
  const [locale, setLocale] = useState<string>(AVAILABLE_LOCALES[0]);

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved && AVAILABLE_LOCALES.includes(saved)) setLocale(saved);
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
      const next = nextLocaleOf(prev);
      window.localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
  }, []);

  return { t: DICTIONARIES[locale], locale, toggleLocale };
}
