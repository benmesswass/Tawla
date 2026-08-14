import { ETAT_LIBRE, EtatTable, URGENCES, Urgence } from "./types";

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

  const poser = (tableId: number, etat: EtatTable) => {
    const actuel = etats[tableId] ?? ETAT_LIBRE;
    if (plusUrgent(etat.urgence, actuel.urgence)) etats[tableId] = etat;
  };

  for (const o of source.enCuisine) {
    poser(o.table_id, { urgence: "en_cuisine", depuis: null, parQui: null, aMoi: false });
  }
  // Une addition demandée n'a pas d'horodatage en base : on n'invente pas de
  // compteur. La table vire au rouge, sans anneau — mieux vaut pas de chiffre
  // qu'un chiffre faux.
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
