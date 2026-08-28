import { DashboardStats } from "@/lib/api";
import { formatMoney } from "@/lib/currency";
import { duree } from "@/lib/duree";

/**
 * Les deux chiffres de tête du tableau de bord (Phase 17.1, remaniés le
 * 2026-08-28).
 *
 * La recette d'abord, en gros : c'est ce que le patron vient chercher tous les
 * soirs, et cette habitude quotidienne est ce qui empêche une résiliation au
 * troisième mois. Le temps d'attente moyen juste à côté, pour qu'il voie **en
 * passant** si le service tourne rond aujourd'hui — plutôt que d'aller le
 * chercher sur `/dashboard/stats`, une page qu'il n'ouvrira jamais de
 * lui-même.
 *
 * « Commandes perdues » (annulées) reste mesuré et partagé avec la page de
 * preuve, mais n'est plus le chiffre de tête : Wassim a jugé qu'une commande
 * simplement lente à être prise en charge n'a rien d'une vente ratée, et
 * qu'un chiffre qui pénalise un service occupé décourage plus qu'il n'aide.
 *
 * Zéro s'affiche comme zéro : une case vide se lit comme une panne.
 */
export default function RecetteDuJour({ stats }: { stats: DashboardStats | null }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
      <div className="sm:col-span-2 rounded-xl bg-[var(--harissa)] text-white px-5 py-4">
        <p className="text-sm text-white/80">Ventes du jour</p>
        <p className="text-3xl sm:text-4xl font-semibold tabular-nums mt-1">
          {stats ? formatMoney(stats.revenue_today) : "—"}
        </p>
        <p className="text-xs text-white/70 mt-1">
          Commandes réellement réglées aujourd&apos;hui : paiement carte abouti, ou espèces confirmées par le
          serveur. Une commande servie mais pas encore payée n&apos;y entre pas.
        </p>
      </div>

      <div className="rounded-xl border border-[var(--line)] bg-white px-5 py-4">
        <p className="text-sm text-[var(--ink-soft)]">Temps d&apos;attente moyen</p>
        <p className="text-3xl font-semibold tabular-nums mt-1">
          {stats ? duree(stats.timing.avg_wait_confirmation_seconds) : "—"}
        </p>
        {/* La définition est écrite ici, pas dans une aide : un chiffre dont on
            ne comprend pas la définition ne convainc personne. */}
        <p className="text-xs text-[var(--ink-soft)] mt-1">
          Entre la validation du panier par le client et la prise en charge par un serveur, aujourd&apos;hui.
          Le détail par serveur est sur « Activité du jour ».
        </p>
      </div>
    </div>
  );
}
