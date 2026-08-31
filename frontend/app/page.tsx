import Link from "next/link";
import { lalezar } from "@/lib/fonts";
import { currentMarket } from "@/lib/market";
import TawlaLogo from "@/components/brand/TawlaLogo";
import BoutonVisite from "@/components/visite/BoutonVisite";
import { BENEFITS, INCLUDED, PILOT_RESULTS, TIERS } from "@/lib/offer";
import { marketBaseUrl } from "@/lib/marketUrls";

/**
 * Page d'accueil publique (Phase 14.2).
 *
 * S'adresse au patron d'établissement, pas au client final : celui-ci arrive
 * toujours par le QR de sa table et ne passe jamais ici.
 *
 * Ne contient aucun chiffre ni témoignage tant qu'un pilote réel n'en a pas
 * fourni (voir `lib/offer.ts`). Une page de vente qui invente ses résultats
 * détruit la seule chose qu'elle a à vendre.
 */
export const metadata = {
  title: "Tawla — la commande à table, sans commande perdue",
  description:
    "Vos clients commandent depuis leur téléphone, vos serveurs gardent la main, et vous voyez enfin vos chiffres. Installation, formation et QR imprimés inclus.",
  // Deux domaines, même contenu commercial adapté au marché — France,
  // MARCHE_FRANCE.md Phase F4 §5 ("hreflang : fr-TN ↔ fr-FR croisés").
  // Codes de RÉGION, pas de langue différente : les deux marchés servent
  // en français, seul le pays change.
  alternates: {
    canonical: marketBaseUrl(currentMarket.code) + "/",
    languages: {
      "fr-TN": marketBaseUrl("tn") + "/",
      "fr-FR": marketBaseUrl("fr") + "/",
    },
  },
};

export default function HomePage() {
  return (
    <main className="min-h-screen">
      <section className="bg-[var(--harissa)] text-white">
        <div className="max-w-3xl mx-auto px-6 py-14" data-visite="accueil-promesse">
          <TawlaLogo size={40} className="mb-8" inverse />
          <h1 className={`${lalezar.className} text-3xl sm:text-4xl leading-tight text-balance`}>
            La commande à table, sans commande perdue
          </h1>
          <p className="mt-4 text-lg text-white/90 max-w-xl">
            Vos clients scannent le QR de leur table et commandent. Vos serveurs gardent la main : rien ne part
            en cuisine sans qu&apos;ils l&apos;aient vérifié à table.
          </p>
          {/* La démo est le premier appel à l'action, avant « créer mon
              compte » : un restaurateur qui découvre Tawla veut le voir
              tourner, pas s'inscrire. Elle ne quitte pas la page — les bulles
              s'ouvrent par-dessus celle qu'il est en train de lire. */}
          <div className="mt-7 flex flex-wrap items-center gap-4">
            <BoutonVisite className="inline-flex items-center rounded-lg bg-white px-5 py-3 font-medium text-[var(--harissa)] shadow-sm" />
            <p className="text-sm text-white/80">2 minutes, sans inscription.</p>
          </div>
        </div>
      </section>

      <section className="max-w-3xl mx-auto px-6 py-12" data-visite="accueil-benefices">
        <div className="grid gap-6 sm:grid-cols-3">
          {BENEFITS.map((benefit) => (
            <div key={benefit.title}>
              <h2 className="font-semibold mb-1">{benefit.title}</h2>
              <p className="text-sm text-[var(--ink-soft)]">{benefit.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {PILOT_RESULTS.length > 0 && (
        <section className="bg-[var(--semoule)] border-y border-[var(--line)]">
          <div className="max-w-3xl mx-auto px-6 py-10">
            <h2 className={`${lalezar.className} text-2xl mb-5`}>Mesuré chez eux</h2>
            <div className="grid gap-6 sm:grid-cols-3">
              {PILOT_RESULTS.map((result) => (
                <div key={`${result.establishment}-${result.metric}`}>
                  <p className="text-2xl font-semibold tabular-nums">{result.value}</p>
                  <p className="text-sm">{result.metric}</p>
                  <p className="text-xs text-[var(--ink-soft)] mt-1">{result.establishment}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="max-w-3xl mx-auto px-6 py-12" data-visite="accueil-inclus">
        <h2 className={`${lalezar.className} text-2xl mb-2`}>Tout est inclus</h2>
        <p className="text-sm text-[var(--ink-soft)] mb-6 max-w-xl">
          Vous n&apos;avez ni carte à saisir, ni QR à imprimer, ni logiciel à apprendre seul. On s&apos;installe
          chez vous, on forme votre équipe, et on reste joignable.
        </p>
        <div className="grid gap-6 sm:grid-cols-2">
          {INCLUDED.map((item) => (
            <div key={item.title} className="border-l-2 border-[var(--harissa)] pl-4">
              <h3 className="font-semibold mb-1">{item.title}</h3>
              <p className="text-sm text-[var(--ink-soft)]">{item.detail}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-[var(--semoule)] border-t border-[var(--line)]">
        <div className="max-w-3xl mx-auto px-6 py-12">
          <h2 className={`${lalezar.className} text-2xl mb-2`}>Trois paliers, un seul abonnement</h2>
          <p className="text-sm text-[var(--ink-soft)] mb-8 max-w-xl">
            Sans commission sur vos commandes, quel que soit le palier : vos clients vous règlent directement,
            comme aujourd&apos;hui.
          </p>

          <div className="grid gap-6 sm:grid-cols-3">
            {TIERS.map((tier) => (
              <div
                key={tier.id}
                data-visite={`tarif-${tier.id}`}
                className={`flex flex-col rounded-lg border p-5 bg-white ${
                  tier.recommended ? "border-[var(--harissa)] ring-1 ring-[var(--harissa)]" : "border-[var(--line)]"
                }`}
              >
                {tier.recommended && (
                  <p className="text-xs font-semibold text-[var(--harissa)] mb-2 uppercase tracking-wide">
                    Recommandé
                  </p>
                )}
                <h3 className="font-semibold text-lg">{tier.name}</h3>
                <p className="text-xs text-[var(--ink-soft)] mb-3">{tier.tagline}</p>
                <p className="mb-4">
                  <span className="text-2xl font-semibold text-[var(--encre)] tabular-nums">
                    {tier.priceDT} {currentMarket.currency.symbol}
                  </span>
                  <span className="text-sm text-[var(--ink-soft)]"> / mois</span>
                </p>
                <ul className="text-sm text-[var(--ink-soft)] space-y-1.5">
                  {tier.features.map((feature) => (
                    <li key={feature}>• {feature}</li>
                  ))}
                </ul>
                <Link
                  href={`/signup?tier=${tier.id}`}
                  className={`mt-auto pt-4 border-t border-[var(--line)] text-center text-sm font-medium ${
                    tier.recommended ? "text-[var(--harissa)]" : "text-[var(--encre)] underline"
                  }`}
                >
                  Choisir {tier.name}
                </Link>
              </div>
            ))}
          </div>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              href="/signup"
              data-visite="accueil-creer-compte"
              className="inline-flex items-center rounded-lg bg-[var(--harissa)] px-5 py-3 text-white font-medium"
            >
              Créer mon compte
            </Link>
            <a
              href="mailto:contact@tawla.tn?subject=Essai%20Tawla"
              className="inline-flex items-center rounded-lg border border-[var(--line)] px-5 py-3 font-medium text-[var(--encre)]"
            >
              Demander un essai
            </a>
            {/* Le même appel, pour qui a lu la page jusqu'au bout sans
                cliquer en haut. Discret ici : la décision du bas de page,
                c'est « créer mon compte ». */}
            <BoutonVisite className="text-sm underline text-[var(--ink-soft)]" />
            <Link href="/login" className="text-sm underline text-[var(--ink-soft)]">
              J&apos;ai déjà un compte
            </Link>
          </div>
        </div>
      </section>

      <footer className="max-w-3xl mx-auto px-6 py-8 text-xs text-[var(--ink-soft)]">
        <p>
          Tawla — commande à table par QR code pour les restaurants. Si vous êtes client d&apos;un
          établissement, scannez simplement le QR posé sur votre table.
        </p>
        <Link href="/confidentialite" className="underline mt-2 inline-block">
          Politique de confidentialité
        </Link>
      </footer>
    </main>
  );
}
