/**
 * France, MARCHE_FRANCE.md Phase F4 §5 ("robots.txt par marché").
 *
 * Interdit aux robots tout ce qui n'a pas de valeur en recherche (écrans
 * internes, API) — pas une question de confidentialité (déjà protégé par
 * l'authentification), juste éviter d'indexer du contenu qui n'a aucun sens
 * hors contexte pour un visiteur venu de Google.
 */
import type { MetadataRoute } from "next";
import { currentMarket } from "@/lib/market";
import { marketBaseUrl } from "@/lib/marketUrls";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard", "/staff", "/kitchen", "/admin", "/login", "/api/"],
    },
    sitemap: `${marketBaseUrl(currentMarket.code)}/sitemap.xml`,
  };
}
