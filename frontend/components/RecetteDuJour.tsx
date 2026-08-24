import { DashboardStats } from "@/lib/api";
import { formatAmount } from "@/lib/market";

/**
 * Les deux chiffres de tête du tableau de bord (Phase 17.1).
 *
 * La recette d'abord, en gros : c'est ce que le patron vient chercher tous les
 * soirs, et cette habitude quotidienne est ce qui empêche une résiliation au
 * troisième mois. Les commandes perdues juste à côté, pour qu'il apprenne
 * **en passant** le chiffre qui justifie l'abonnement — plutôt que d'aller le
 * chercher sur une page qu'il n'ouvrira jamais de lui-même.
 *
 * Zéro s'affiche comme zéro : une case vide se lit comme une panne.
 */
export default function RecetteDuJour({ stats }: { stats: DashboardStats | null }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
      <div className="sm:col-span-2 rounded-xl bg-[var(--harissa)] text-white px-5 py-4">
        <p className="text-sm text-white/80">Ventes du jour</p>
        <p className="text-3xl sm:text-4xl font-semibold tabular-nums mt-1">
          {stats ? formatAmount(stats.revenue_today) : "—"}
        </p>
        <p className="text-xs text-white/70 mt-1">
          Commandes réellement réglées aujourd&apos;hui : paiement carte abouti, ou espèces confirmées par le
          serveur. Une commande servie mais pas encore payée n&apos;y entre pas.
        </p>
      </div>

      <div className="rounded-xl border border-[var(--line)] bg-white px-5 py-4">
        <p className="text-sm text-[var(--ink-soft)]">Commandes perdues</p>
        <p className="text-3xl font-semibold tabular-nums mt-1">
          {stats ? stats.lost_orders_today : "—"}
        </p>
        {/* La définition est écrite ici, pas dans une aide : un chiffre dont on
            ne comprend pas la définition ne convainc personne. */}
        <p className="text-xs text-[var(--ink-soft)] mt-1">
          Annulées, ou restées plus de 10 minutes entre la validation du panier et la prise en charge par un
          serveur.
        </p>
      </div>
    </div>
  );
}
