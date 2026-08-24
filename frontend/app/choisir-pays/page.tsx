import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { lalezar } from "@/lib/fonts";
import TawlaLogo from "@/components/brand/TawlaLogo";
import type { MarketCode } from "@/lib/market";
import { isMarketCode, MARKET_COOKIE, MARKET_LABELS, marketForCountry } from "@/lib/marketSelector";

/**
 * Le hub (F4, `MARCHE_FRANCE.md` §5) — jamais dans le parcours client, qui
 * arrive toujours directement sur le site de SON marché via le QR de sa
 * table. Cette page ne s'adresse qu'à un visiteur arrivé sur l'URL globale
 * sans savoir encore quel marché il cherche.
 *
 * Rendue entièrement côté serveur : les deux options sont de vrais
 * `<a href>` vers `/api/choisir-marche`, qui pose le cookie et redirige —
 * fonctionne sans JavaScript.
 */
export const metadata = {
  title: "Tawla — Choisir votre pays",
};

const MARKET_ORDER: MarketCode[] = ["tn", "fr"];

export default function ChoisirPaysPage() {
  const cookieStore = cookies();
  const existing = cookieStore.get(MARKET_COOKIE)?.value;
  if (isMarketCode(existing)) {
    redirect(`/api/choisir-marche?market=${existing}`);
  }

  // CF-IPCountry (posé par Cloudflare, voir app/core/config.py côté backend)
  // sert UNIQUEMENT à mettre l'option probable en premier — jamais à
  // rediriger automatiquement (§5) : un Tunisien en France, ou l'inverse,
  // serait mal servi par un choix fait à sa place.
  const detectedCountry = headers().get("cf-ipcountry");
  const suggested = marketForCountry(detectedCountry);
  const ordered = suggested ? [suggested, ...MARKET_ORDER.filter((m) => m !== suggested)] : MARKET_ORDER;

  return (
    <main className="min-h-screen flex items-center justify-center bg-[var(--semoule)] p-6">
      <div className="w-full max-w-sm text-center">
        <TawlaLogo size={36} className="mx-auto mb-8" />
        <h1 className={`${lalezar.className} text-2xl text-[var(--encre)] mb-2`}>Où êtes-vous ?</h1>
        <p className="text-sm text-[var(--ink-soft)] mb-8">
          Tawla existe pour deux marchés distincts — choisissez le vôtre.
        </p>
        <div className="flex flex-col gap-3">
          {ordered.map((market) => (
            <a
              key={market}
              href={`/api/choisir-marche?market=${market}`}
              className={`rounded-lg border px-5 py-4 text-left transition-colors ${
                market === suggested
                  ? "border-[var(--harissa)] bg-white ring-1 ring-[var(--harissa)]"
                  : "border-[var(--line)] bg-white"
              }`}
            >
              <span className="font-semibold text-[var(--encre)]">{MARKET_LABELS[market]}</span>
              {market === suggested && (
                <span className="ms-2 text-xs font-semibold uppercase tracking-wide text-[var(--harissa)]">
                  Détecté
                </span>
              )}
            </a>
          ))}
        </div>
      </div>
    </main>
  );
}
