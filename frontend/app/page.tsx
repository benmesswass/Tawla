import Link from "next/link";
import { lalezar } from "@/lib/fonts";
import TawlaLogo from "@/components/brand/TawlaLogo";
import { BENEFITS, INCLUDED, PILOT_RESULTS, PRICE_MONTHLY_DT } from "@/lib/offer";

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
};

export default function HomePage() {
  return (
    <main className="min-h-screen">
      <section className="bg-[var(--harissa)] text-white">
        <div className="max-w-3xl mx-auto px-6 py-14">
          <TawlaLogo size={40} className="mb-8" />
          <h1 className={`${lalezar.className} text-3xl sm:text-4xl leading-tight text-balance`}>
            La commande à table, sans commande perdue
          </h1>
          <p className="mt-4 text-lg text-white/90 max-w-xl">
            Vos clients scannent le QR de leur table et commandent. Vos serveurs gardent la main : rien ne part
            en cuisine sans qu&apos;ils l&apos;aient vérifié à table.
          </p>
          <p className="mt-6 text-sm text-white/80">
            Pour les restaurants et brasseries à partir de 6 tables, en Tunisie.
          </p>
        </div>
      </section>

      <section className="max-w-3xl mx-auto px-6 py-12">
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

      <section className="max-w-3xl mx-auto px-6 py-12">
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
          <h2 className={`${lalezar.className} text-2xl mb-2`}>Un seul prix</h2>
          {PRICE_MONTHLY_DT === null ? (
            <p className="text-[var(--ink-soft)]">
              Un abonnement mensuel unique, service compris, sans commission sur vos commandes. Le tarif vous
              est communiqué au premier rendez-vous.
            </p>
          ) : (
            <p className="text-[var(--ink-soft)]">
              <span className="text-3xl font-semibold text-[var(--encre)] tabular-nums">
                {PRICE_MONTHLY_DT} DT
              </span>{" "}
              par mois, service compris, sans commission sur vos commandes.
            </p>
          )}
          <p className="text-sm text-[var(--ink-soft)] mt-3">
            Aucune commission n&apos;est prélevée sur vos encaissements : vos clients vous règlent
            directement, comme aujourd&apos;hui.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <a
              href="mailto:contact@tawla.tn?subject=Essai%20Tawla"
              className="inline-flex items-center rounded-lg bg-[var(--harissa)] px-5 py-3 text-white font-medium"
            >
              Demander un essai
            </a>
            <Link href="/login" className="text-sm underline text-[var(--ink-soft)]">
              J&apos;ai déjà un compte
            </Link>
          </div>
        </div>
      </section>

      <footer className="max-w-3xl mx-auto px-6 py-8 text-xs text-[var(--ink-soft)]">
        Tawla — commande à table par QR code pour les restaurants tunisiens. Si vous êtes client d&apos;un
        établissement, scannez simplement le QR posé sur votre table.
      </footer>
    </main>
  );
}
