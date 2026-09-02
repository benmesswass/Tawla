"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/auth";
import { lalezar } from "@/lib/fonts";
import { TIER_ACCENTS } from "@/lib/offer";
import type { SubscriptionTier } from "@/lib/api";

/**
 * L'en-tête commun aux quatre écrans de direction.
 *
 * Chaque page portait le sien : les liens changeaient de place (sous le titre
 * ici, à droite ailleurs), une même destination changeait de nom (« Suivi de
 * l'activité » ou « Activité du jour », « Gérer le menu » ou « Menu »), et
 * l'écran d'activité oubliait le rapport d'équipe. Passer d'une page à l'autre
 * donnait l'impression de changer de logiciel — et sur un écran étroit, la
 * rangée alignée à droite débordait, « Se déconnecter » se retrouvant coupé.
 *
 * Un seul composant, donc un seul jeu de libellés et une seule mise en page :
 * l'onglet de la page courante est marqué, jamais cliquable pour rien.
 */
const PAGES = [
  { href: "/dashboard", label: "Carte" },
  { href: "/dashboard/stats", label: "Activité du jour" },
  { href: "/dashboard/preuve", label: "Preuve du pilote" },
  { href: "/dashboard/equipe", label: "Rapport d'équipe" },
  // Le backend autorise un manager à confirmer une commande au même titre
  // qu'un serveur (_WAITER_OR_MANAGER, app/modules/orders/router.py), mais
  // /staff n'était lié depuis nulle part : un manager fraîchement inscrit
  // (self-service, sans serveur dans son équipe) n'avait aucun moyen de
  // découvrir cet écran pour confirmer sa toute première commande (audit
  // pilote, 2026-08-20).
  { href: "/staff", label: "Service en salle" },
] as const;

const TIER_LABELS: Record<string, string> = { essentiel: "Essentiel", pro: "Pro", business: "Business" };

export default function EnteteManager({
  titre,
  sousTitre,
  palier,
}: {
  titre: string;
  sousTitre?: string;
  // Facultatif : seul /dashboard connaît le restaurant courant au moment du
  // rendu de cet en-tête partagé (voir sa docstring) — les trois autres
  // écrans peuvent l'ignorer sans rien casser.
  palier?: SubscriptionTier;
}) {
  const router = useRouter();
  const chemin = usePathname();

  function seDeconnecter() {
    clearToken();
    router.push("/login");
  }

  return (
    <header className="mb-4">
      {/* La navigation au-dessus du titre, et non à côté : elle appartient à
          l'application, le titre à la page. Les inverser faisait sauter le
          titre d'un bord à l'autre d'un écran au suivant. */}
      <nav
        data-visite="dashboard-navigation"
        className="flex items-center gap-x-4 gap-y-1 flex-wrap border-b border-[var(--line)] pb-2 mb-3"
      >
        {PAGES.map((page) => {
          const active = chemin === page.href;
          return (
            <Link
              key={page.href}
              href={page.href}
              aria-current={active ? "page" : undefined}
              className={
                active
                  ? "text-sm font-semibold text-[var(--harissa)]"
                  : "text-sm text-[var(--ink-soft)] hover:text-[var(--encre)] underline"
              }
            >
              {page.label}
            </Link>
          );
        })}
        {palier && (
          // <a> natif, jamais <Link> : depuis /dashboard lui-même, une
          // navigation Next vers la même route ne change que la query string
          // sans remonter la page — l'effet qui lit `?tab=settings` (voir
          // dashboard/page.tsx) ne se redéclenchait alors jamais (retour
          // utilisateur, 2026-09-02 : "ne redirige pas"). Un lien natif force
          // un vrai rechargement, donc l'effet tourne à chaque clic.
          <a
            href="/dashboard?tab=settings#abonnement"
            className="flex items-center gap-1.5 text-sm font-semibold px-3 py-1.5 rounded-full border-2 transition-transform hover:scale-105 ms-auto"
            style={{
              backgroundColor: (TIER_ACCENTS[palier] ?? TIER_ACCENTS.essentiel).fond,
              borderColor: (TIER_ACCENTS[palier] ?? TIER_ACCENTS.essentiel).bord,
              color: (TIER_ACCENTS[palier] ?? TIER_ACCENTS.essentiel).texte,
            }}
          >
            Palier {TIER_LABELS[palier] ?? palier}
            <span aria-hidden="true">→</span>
          </a>
        )}
        <button
          onClick={seDeconnecter}
          className={`text-sm text-[var(--ink-soft)] underline ${palier ? "" : "ms-auto"}`}
        >
          Se déconnecter
        </button>
      </nav>

      <h1 className={`${lalezar.className} text-2xl`}>{titre}</h1>
      {sousTitre && <p className="text-sm text-[var(--ink-soft)] mt-1">{sousTitre}</p>}
    </header>
  );
}
