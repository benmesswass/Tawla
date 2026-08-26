/**
 * Pays probable du visiteur, déduit des en-têtes de géolocalisation posés par
 * la plateforme d'hébergement (France, MARCHE_FRANCE.md Phase F4 §5).
 *
 * Sert **uniquement** à ordonner les options du sélecteur et à les marquer
 * « détecté » — jamais à rediriger automatiquement (§5, tableau
 * « Comportement ») : mauvais pour le référencement, et faux pour un
 * Tunisien en France ou un Français en Tunisie.
 *
 * Deux en-têtes gérés : `CF-IPCountry` (Cloudflare, cité tel quel dans la
 * spec) et `x-vercel-ip-country` (Vercel, l'hébergeur réel du frontend) — le
 * premier présent gagne. Absents des deux → aucune détection, le sélecteur
 * garde son ordre par défaut.
 */
import type { SupportedMarketCode } from "./market";

const COUNTRY_TO_MARKET: Record<string, SupportedMarketCode> = {
  TN: "tn",
  FR: "fr",
};

export function detectMarketFromHeaders(headers: Headers): SupportedMarketCode | null {
  const country = (headers.get("cf-ipcountry") || headers.get("x-vercel-ip-country") || "").toUpperCase();
  return COUNTRY_TO_MARKET[country] ?? null;
}
