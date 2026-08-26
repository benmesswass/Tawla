/**
 * Choix du marché depuis le hub (France, MARCHE_FRANCE.md Phase F4 §5).
 *
 * Route dédiée plutôt qu'un Server Action : le hub doit fonctionner sans
 * JavaScript (spec §5, « en `<a href>` réels ») — un lien `<a href="/api/
 * choisir-marche?market=fr">` est un vrai lien, une redirection HTTP peut
 * poser un cookie, un Server Action non.
 *
 * `?market=` sert aussi de mécanisme de force générique (spec §5, ligne
 * « ?market=fr dans l'URL ») : appelable directement, pas seulement depuis
 * les liens du hub — utile pour les liens de campagne et les tests.
 */
import { NextRequest, NextResponse } from "next/server";
import { isSupportedMarketCode, marketBaseUrl } from "@/lib/marketUrls";

const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365; // 1 an, spec §5

export function GET(request: NextRequest) {
  const market = request.nextUrl.searchParams.get("market");
  if (!isSupportedMarketCode(market)) {
    return NextResponse.json({ error: "unknown market code" }, { status: 400 });
  }

  const response = NextResponse.redirect(marketBaseUrl(market), 302);
  response.cookies.set("tawla-market", market, {
    maxAge: COOKIE_MAX_AGE_SECONDS,
    sameSite: "lax",
    path: "/",
  });
  return response;
}
