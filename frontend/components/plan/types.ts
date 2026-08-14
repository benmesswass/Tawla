/**
 * Plan de salle — vocabulaire partagé entre la vue de service et l'éditeur.
 */

export type TableShape = "round" | "square" | "rect";

export type PlanTable = {
  id: number;
  label: string;
  zone: string | null;
  pos_x: number | null;
  pos_y: number | null;
  shape: TableShape;
  seats: number;
};

/**
 * Ce qu'une table demande à un humain, du plus calme au plus urgent.
 *
 * L'ordre compte : une table peut cumuler plusieurs choses (une commande en
 * cuisine ET un appel serveur), et la tuile ne montre que la plus urgente —
 * un serveur qui traverse la salle a besoin d'une réponse, pas d'un inventaire.
 */
export const URGENCES = ["libre", "en_cuisine", "a_servir", "addition", "a_prendre", "appel"] as const;
export type Urgence = (typeof URGENCES)[number];

export const LIBELLE_URGENCE: Record<Urgence, string> = {
  libre: "",
  en_cuisine: "en cuisine",
  a_servir: "prête à servir",
  addition: "addition",
  a_prendre: "à prendre",
  appel: "vous appelle",
};

/** Les états qui demandent un déplacement maintenant. */
export function demandeUnServeur(urgence: Urgence): boolean {
  return urgence !== "libre" && urgence !== "en_cuisine";
}

export type EtatTable = {
  urgence: Urgence;
  /** Depuis quand cet état dure — la base du compte à rebours. */
  depuis: string | null;
  /** Prénom du serveur qui a pris la table, quand elle est prise. */
  parQui: string | null;
  aMoi: boolean;
};

export const ETAT_LIBRE: EtatTable = { urgence: "libre", depuis: null, parQui: null, aMoi: false };

/**
 * Une commande non prise en charge est comptée **perdue** au bout de dix
 * minutes (`ABANDONED_PENDING_AFTER` côté backend, et c'est ce seuil que la
 * page de preuve utilise pour chiffrer l'argent perdu).
 *
 * L'anneau qui entoure une table se referme donc exactement au moment où la
 * commande bascule dans ce compteur : ce n'est pas une décoration, c'est le
 * compte à rebours avant que le patron perde de l'argent.
 */
export const SECONDES_AVANT_PERTE = 600;

export function secondesDepuis(iso: string | null, maintenant: number): number {
  if (!iso) return 0;
  return Math.max(0, (maintenant - new Date(iso).getTime()) / 1000);
}

/** 0 → rien ne presse, 1 → la commande vient de basculer en « perdue ». */
export function pression(etat: EtatTable, maintenant: number): number {
  if (!demandeUnServeur(etat.urgence)) return 0;
  return Math.min(1, secondesDepuis(etat.depuis, maintenant) / SECONDES_AVANT_PERTE);
}
