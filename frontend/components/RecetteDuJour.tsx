import { DashboardStats } from "@/lib/api";
import { formatMoney } from "@/lib/currency";
import { duree } from "@/lib/duree";
import { LIBELLE_MOYEN } from "@/lib/moyenDePaiement";

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
 * Un compteur de « commandes perdues » a occupé cette place jusqu'au
 * 2026-08-28, puis a survécu sur la page de preuve jusqu'au 2026-09-09. Il ne
 * comptait que les annulations qu'un serveur avait pris la peine
 * d'enregistrer : retiré du produit, on ne montre pas un chiffre qui dépend du
 * bon vouloir de la salle.
 *
 * Zéro s'affiche comme zéro : une case vide se lit comme une panne.
 *
 * Depuis le 2026-09-10, la recette compte ce qui est RÉELLEMENT rentré, parts
 * partielles comprises : une table de quatre dont trois convives avaient réglé
 * pesait 0 DT, l'argent était en caisse et ce chiffre n'en disait rien. Son
 * pendant — ce qu'il reste à encaisser — est posé juste en dessous plutôt que
 * fondu dedans : l'écart entre le service et la caisse doit être lisible, pas
 * caché.
 */
export default function RecetteDuJour({ stats }: { stats: DashboardStats | null }) {
  const reste = stats?.reste_a_encaisser_today ?? 0;
  const parMoyen = stats?.revenue_by_method ?? [];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
      <div className="sm:col-span-2 rounded-xl bg-[var(--harissa)] text-white px-5 py-4">
        <p className="text-sm text-white/80">Ventes du jour</p>
        <p className="text-3xl sm:text-4xl font-semibold tabular-nums mt-1">
          {stats ? formatMoney(stats.revenue_today) : "—"}
        </p>
        <p className="text-xs text-white/70 mt-1">
          Ce qui est réellement rentré aujourd&apos;hui : espèces et carte encaissées en salle, paiement en
          ligne abouti. Une part réglée compte, même si la table n&apos;a pas fini de payer.
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

      {/* D'où vient l'argent, et ce qui n'est pas encore rentré. Le moyen de
          paiement était enregistré depuis toujours (espèces, carte en salle,
          carte en ligne) sans qu'aucun écran ne le montre au patron. Agrégé
          part par part côté backend : une table moitié espèces moitié carte
          apparaît dans les deux, jamais entièrement dans un seul. */}
      {(parMoyen.length > 0 || reste > 0) && (
        <div className="sm:col-span-3 rounded-xl border border-[var(--line)] bg-white px-5 py-4 flex flex-wrap items-baseline gap-x-6 gap-y-2">
          {parMoyen.map((ligne) => (
            <p key={ligne.method ?? "inconnu"} className="text-sm text-[var(--ink-soft)]">
              {ligne.method ? LIBELLE_MOYEN[ligne.method] : "moyen non enregistré"}{" "}
              <span className="font-semibold tabular-nums text-[var(--encre)]">{formatMoney(ligne.amount)}</span>
            </p>
          ))}
          {reste > 0 && (
            <p className="text-sm text-[var(--ink-soft)] sm:ms-auto">
              Reste à encaisser{" "}
              <span className="font-semibold tabular-nums text-[var(--laiton-text)]">{formatMoney(reste)}</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
