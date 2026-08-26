/**
 * Pays détecté pour CE visiteur (France, MARCHE_FRANCE.md Phase F4 §5),
 * consommé côté client par `BandeauAutreMarche`.
 *
 * Route dédiée plutôt qu'un appel direct à `headers()` dans le composant :
 * `headers()`/`cookies()` dans l'arbre de rendu d'une page force TOUT le
 * site à sortir du rendu statique (le composant est monté depuis le layout
 * racine). Isoler la lecture dans une route API garde `/`, `/confidentialite`
 * etc. statiques — seule cette route, minuscule et déjà dynamique par
 * nature, paie le coût.
 */
import { NextRequest, NextResponse } from "next/server";
import { detectMarketFromHeaders } from "@/lib/geoMarket";
import { marketBaseUrl } from "@/lib/marketUrls";

export function GET(request: NextRequest) {
  const market = detectMarketFromHeaders(request.headers);
  return NextResponse.json({ market, url: market ? marketBaseUrl(market) : null });
}
