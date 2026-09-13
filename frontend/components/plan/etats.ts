import { ETAT_LIBRE, EtatTable, Reglement, URGENCES, Urgence } from "./types";

/**
 * Traduit ce que l'écran serveur sait déjà en un état par table.
 *
 * Volontairement dérivé des mêmes listes que celles affichées en dessous du
 * plan, et non d'une route dédiée : deux sources finiraient par se contredire,
 * et un plan qui ment sur l'état d'une table est pire qu'aucun plan.
 *
 * Une table peut cumuler plusieurs choses — une commande en cuisine *et* un
 * appel serveur. La tuile ne montre que la plus urgente : un serveur qui
 * traverse la salle a besoin d'une réponse, pas d'un inventaire.
 */

export type SourceEtats = {
  /** Tables occupées (`occupied_at` non nul) — état de base, posé au scan du
   *  QR et jamais dérivé des commandes en cours (voir types.ts). */
  tablesOccupees: Set<number>;
  aPrendre: { table_id: number; depuis: string | null; parQui: string | null; aMoi: boolean }[];
  aServir: { table_id: number; depuis: string | null }[];
  additions: { table_id: number; aMoi: boolean }[];
  appels: { table_id: number; depuis: string | null }[];
  enCuisine: { table_id: number }[];
};

function plusUrgent(a: Urgence, b: Urgence): boolean {
  return URGENCES.indexOf(a) > URGENCES.indexOf(b);
}

export function construireEtats(source: SourceEtats): Record<number, EtatTable> {
  const etats: Record<number, EtatTable> = {};

  // Base : occupée ou libre, avant toute urgence. Posée en premier, elle ne
  // peut jamais être redescendue en dessous — `poser` ne fait que monter.
  for (const tableId of source.tablesOccupees) {
    etats[tableId] = { urgence: "occupee", depuis: null, parQui: null, aMoi: false };
  }

  const poser = (tableId: number, etat: EtatTable) => {
    const actuel = etats[tableId] ?? ETAT_LIBRE;
    if (plusUrgent(etat.urgence, actuel.urgence)) etats[tableId] = etat;
  };

  for (const o of source.enCuisine) {
    poser(o.table_id, { urgence: "en_cuisine", depuis: null, parQui: null, aMoi: false });
  }
  // Une addition demandée n'a pas d'horodatage en base : on n'invente pas de
  // compteur. La table vire au rouge, sans durée affichée — mieux vaut pas de
  // chiffre qu'un chiffre faux.
  for (const o of source.additions) {
    poser(o.table_id, { urgence: "addition", depuis: null, parQui: null, aMoi: o.aMoi });
  }
  for (const o of source.aServir) {
    poser(o.table_id, { urgence: "a_servir", depuis: o.depuis, parQui: null, aMoi: false });
  }
  for (const o of source.aPrendre) {
    poser(o.table_id, { urgence: "a_prendre", depuis: o.depuis, parQui: o.parQui, aMoi: o.aMoi });
  }
  for (const o of source.appels) {
    poser(o.table_id, { urgence: "appel", depuis: o.depuis, parQui: null, aMoi: false });
  }

  return etats;
}

/**
 * Ce que chaque table a réglé, par table — un second canal, jamais mélangé
 * aux urgences ci-dessus (voir `Reglement` dans types.ts).
 *
 * Dérivé de l'agrégat du backend et non recalculé ici : `fully_paid` tient
 * compte de TOUTES les commandes de l'occupation en cours, ce que l'écran
 * serveur ne peut pas savoir seul — une commande servie puis payée ne fait
 * plus partie des commandes actives qu'il connaît.
 */
export function construireReglements(
  reglements: { table_id: number; amount_paid: number; fully_paid: boolean }[]
): Record<number, Reglement> {
  const par: Record<number, Reglement> = {};
  for (const reglement of reglements) {
    par[reglement.table_id] = reglement.fully_paid ? "total" : reglement.amount_paid > 0 ? "partiel" : "aucun";
  }
  return par;
}
