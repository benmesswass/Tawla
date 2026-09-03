import Link from "next/link";
import { lalezar } from "@/lib/fonts";
import { currentMarket } from "@/lib/market";
import TawlaLogo from "@/components/brand/TawlaLogo";
import BoutonVisite from "@/components/visite/BoutonVisite";
import TrackedLink from "@/components/TrackedLink";
import TrackedAnchor from "@/components/TrackedAnchor";
import FadeInOnScroll from "@/components/FadeInOnScroll";
import ApercuProduit from "@/components/home/ApercuProduit";
import { INCLUDED, PILOT_RESULTS, TIERS } from "@/lib/offer";
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
          {/* Le qualificatif de cible passe avant le CTA, pas après : un
              petit café doit pouvoir s'auto-exclure avant de cliquer, pas
              après avoir commencé une inscription. La stratégie exclut
              volontairement ce public (CLAUDE.md, ROADMAP.md) — la page ne
              doit pas l'attirer par accident. */}
          <p className="mt-5 inline-block rounded-full bg-white/15 px-4 py-1.5 text-sm font-medium">
            Pour les restaurants et brasseries.
          </p>
          {/* La démo est le premier appel à l'action, avant « créer mon
              compte » : un restaurateur qui découvre Tawla veut le voir
              tourner, pas s'inscrire. Elle ne quitte pas la page — les bulles
              s'ouvrent par-dessus celle qu'il est en train de lire. */}
          <div className="mt-7 flex flex-wrap items-center gap-4">
            <BoutonVisite className="inline-flex items-center rounded-lg bg-white px-5 py-3 font-medium text-[var(--harissa)] shadow-sm transition-colors duration-200 hover:bg-[var(--semoule)]" />
            <p className="text-sm text-white/80">2 minutes, sans inscription.</p>
          </div>
        </div>
      </section>

      <section data-visite="accueil-benefices">
        <div className="max-w-4xl mx-auto px-6 py-14">
          <h2 className={`${lalezar.className} text-2xl sm:text-3xl text-center mb-3`}>Un produit, quatre écrans</h2>
          <p className="text-sm text-[var(--ink-soft)] text-center max-w-xl mx-auto mb-10">
            Le client commande depuis son téléphone. Le serveur, le manager et la cuisine suivent chacun le même
            service, sur l&apos;écran qui leur correspond.
          </p>
          <FadeInOnScroll>
            <ApercuProduit />
          </FadeInOnScroll>
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

      <section id="tarifs" className="bg-[var(--semoule)] border-t border-[var(--line)]">
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
                <TrackedLink
                  href={`/signup?tier=${tier.id}`}
                  event="pricing_cta_clicked"
                  eventProperties={{ tier: tier.id }}
                  className={`mt-auto pt-4 border-t border-[var(--line)] text-center text-sm font-medium transition-colors duration-200 ${
                    tier.recommended
                      ? "text-[var(--harissa)] hover:text-[var(--harissa-dark)]"
                      : "text-[var(--encre)] underline hover:text-[var(--harissa)]"
                  }`}
                >
                  Choisir {tier.name}
                </TrackedLink>
              </div>
            ))}
          </div>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <TrackedLink
              href="/signup"
              event="signup_cta_clicked"
              data-visite="accueil-creer-compte"
              className="inline-flex items-center rounded-lg bg-[var(--harissa)] px-5 py-3 text-white font-medium transition-colors duration-200 hover:bg-[var(--harissa-dark)]"
            >
              Créer mon compte
            </TrackedLink>
            <TrackedAnchor
              href="mailto:contact@tawla.tn?subject=Essai%20Tawla"
              event="trial_requested_email"
              className="inline-flex items-center rounded-lg border border-[var(--line)] px-5 py-3 font-medium text-[var(--encre)] transition-colors duration-200 hover:border-[var(--harissa)] hover:text-[var(--harissa)]"
            >
              Demander un essai
            </TrackedAnchor>
            {/* Le même appel, pour qui a lu la page jusqu'au bout sans
                cliquer en haut. Discret ici : la décision du bas de page,
                c'est « créer mon compte ». */}
            <BoutonVisite className="text-sm underline text-[var(--ink-soft)] transition-colors duration-200 hover:text-[var(--harissa)]" />
            <Link
              href="/login"
              className="text-sm underline text-[var(--ink-soft)] transition-colors duration-200 hover:text-[var(--harissa)]"
            >
              J&apos;ai déjà un compte
            </Link>
          </div>
          <p className="mt-4 text-xs text-[var(--ink-soft)]">
            Pensé pour les restaurants et brasseries — pas pour un petit café d&apos;une seule salle.
          </p>
        </div>
      </section>

      <footer className="max-w-3xl mx-auto px-6 py-8 text-xs text-[var(--ink-soft)]">
        <p>
          Tawla — commande à table par QR code pour les restaurants. Si vous êtes client d&apos;un
          établissement, scannez simplement le QR posé sur votre table.
        </p>
        <Link
          href="/confidentialite"
          className="underline mt-2 inline-block transition-colors duration-200 hover:text-[var(--harissa)]"
        >
          Politique de confidentialité
        </Link>
        <div className="mt-1 flex flex-wrap gap-x-3">
          <Link
            href="/mentions-legales"
            className="underline inline-block transition-colors duration-200 hover:text-[var(--harissa)]"
          >
            Mentions légales
          </Link>
          <Link
            href="/cgu"
            className="underline inline-block transition-colors duration-200 hover:text-[var(--harissa)]"
          >
            CGU
          </Link>
          <Link
            href="/cgv"
            className="underline inline-block transition-colors duration-200 hover:text-[var(--harissa)]"
          >
            CGV
          </Link>
          <Link
            href="/dpa"
            className="underline inline-block transition-colors duration-200 hover:text-[var(--harissa)]"
          >
            DPA
          </Link>
        </div>
      </footer>
    </main>
  );
}
