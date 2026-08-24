/**
 * Sélecteur de pays (F4, `MARCHE_FRANCE.md` §5) — hub qui redirige vers le
 * bon déploiement de marché. Partagé entre `app/choisir-pays/page.tsx`
 * (l'écran de choix), `app/api/choisir-marche/route.ts` (pose le cookie et
 * redirige) et `components/marche/BandeauAutreMarche.tsx` (le bandeau
 * discret sur les sites de marché).
 *
 * Règle qui prime sur tout le reste : le parcours client (`/menu/[qrToken]`)
 * ne passe JAMAIS par ce sélecteur — aucun de ces fichiers n'est importé
 * depuis ce dossier. Voir le commentaire en tête de
 * `app/menu/[qrToken]/page.tsx`.
 */
import type { MarketCode } from "@/lib/market";

export const MARKET_COOKIE = "tawla-market";
export const MARKET_COOKIE_MAX_AGE = 60 * 60 * 24 * 365; // 1 an

export function isMarketCode(value: string | null | undefined): value is MarketCode {
  return value === "tn" || value === "fr";
}

/**
 * URL du site d'UN marché donné, depuis les variables d'environnement
 * partagées par les trois déploiements (hub + les deux marchés). `null` tant
 * que le domaine réel n'est pas tranché (MARCHE_FRANCE.md Annexe C, C4) —
 * les appelants doivent dégrader silencieusement (rester sur place) plutôt
 * que rediriger vers une URL vide.
 */
export function siteUrl(market: MarketCode): string | null {
  const raw = market === "tn" ? process.env.NEXT_PUBLIC_TN_SITE_URL : process.env.NEXT_PUBLIC_FR_SITE_URL;
  return raw && raw.trim() ? raw.trim().replace(/\/+$/, "") : null;
}

/**
 * Déduit le marché probable depuis l'en-tête `CF-IPCountry` posé par
 * Cloudflare (voir `S-2a`, `app/core/config.py` côté backend, même en-tête).
 * Sert UNIQUEMENT à ordonner les options ou à afficher le bandeau — jamais à
 * rediriger automatiquement (§5) : un Tunisien en France ou un Français en
 * Tunisie serait mal servi par une redirection silencieuse.
 */
export function marketForCountry(countryCode: string | null): MarketCode | null {
  if (!countryCode) return null;
  if (countryCode === "TN") return "tn";
  if (countryCode === "FR") return "fr";
  return null;
}

export const MARKET_LABELS: Record<MarketCode, string> = {
  tn: "Tunisie",
  fr: "France",
};
