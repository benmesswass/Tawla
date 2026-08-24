import { NextRequest, NextResponse } from "next/server";
import { isMarketCode, MARKET_COOKIE, MARKET_COOKIE_MAX_AGE, siteUrl } from "@/lib/marketSelector";

/**
 * Pose le cookie `tawla-market` et redirige vers le site du marché choisi —
 * seul endroit qui écrit ce cookie (F4, `MARCHE_FRANCE.md` §5). Un `GET`
 * plutôt qu'une action serveur : la page de choix (`app/choisir-pays`) doit
 * fonctionner en `<a href>` réel, sans JavaScript obligatoire.
 *
 * `redirect` (optionnel) : chemin à rouvrir sur le site cible après le choix
 * — utilisé par `?market=fr` posé sur un lien profond, pour ne pas perdre la
 * page d'origine.
 */
export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const market = url.searchParams.get("market");
  const redirectPath = url.searchParams.get("redirect") || "/";

  if (!isMarketCode(market)) {
    return NextResponse.redirect(new URL("/choisir-pays", request.url));
  }

  // Domaine réel pas encore tranché (MARCHE_FRANCE.md Annexe C, C4) : on
  // reste sur CE déploiement plutôt que de rediriger vers une URL vide — le
  // cookie est quand même posé, pour que le choix soit mémorisé le jour où
  // les domaines existent.
  const target = siteUrl(market) ?? new URL(request.url).origin;
  const destination = new URL(redirectPath.startsWith("/") ? redirectPath : "/", target);

  const response = NextResponse.redirect(destination, { status: 302 });
  response.cookies.set(MARKET_COOKIE, market, {
    maxAge: MARKET_COOKIE_MAX_AGE,
    sameSite: "lax",
    httpOnly: true,
    path: "/",
  });
  return response;
}
