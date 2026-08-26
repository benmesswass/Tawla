/**
 * URL racine de chaque marché servi par Tawla (France, MARCHE_FRANCE.md
 * Phase F4 §5) — utilisées par le hub (`app/choisir-pays`) et sa route de
 * choix (`app/api/choisir-marche`) pour rediriger vers le bon service.
 *
 * `tawla.tn`/`tawla.fr` sont l'hypothèse de travail du document (citée
 * partout dans MARCHE_FRANCE.md comme exemple concret), pas encore des
 * domaines réservés (🧑, MARCHE_FRANCE.md Phase F4) — d'où les variables
 * d'environnement : la valeur réelle se pose sans toucher au code le jour où
 * Wassim confirme les noms définitifs.
 */
import { SUPPORTED_MARKET_CODES, type SupportedMarketCode } from "./market";

const MARKET_URLS: Record<SupportedMarketCode, string> = {
  tn: process.env.TAWLA_TN_URL || "https://tawla.tn",
  fr: process.env.TAWLA_FR_URL || "https://tawla.fr",
};

export function marketBaseUrl(code: SupportedMarketCode): string {
  return MARKET_URLS[code];
}

export function isSupportedMarketCode(value: string | null): value is SupportedMarketCode {
  return value !== null && (SUPPORTED_MARKET_CODES as readonly string[]).includes(value);
}
