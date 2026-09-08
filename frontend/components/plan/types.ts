/**
 * Plan de salle — vocabulaire partagé entre la vue de service et l'éditeur.
 */

import { duree } from "@/lib/duree";

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
 * Un repère fixe du plan — le bar, une porte d'entrée. Pas une table : rien
 * à commander, rien à servir, juste de quoi se repérer dans la salle d'un
 * coup d'œil (« la 4 est près de l'entrée »). Toujours posé — contrairement
 * à une table, il n'a pas de réserve où attendre : il naît déjà à sa place.
 */
export type LandmarkKind = "bar" | "entrance";

/** Taille dessinée du repère — un coin comptoir ou tout un mur de bar, une
 *  porte simple ou une double entrée. */
export type LandmarkSize = "small" | "medium" | "large";

export type PlanLandmark = {
  id: number;
  kind: LandmarkKind;
  pos_x: number;
  pos_y: number;
  size: LandmarkSize;
};

export const LIBELLE_REPERE: Record<LandmarkKind, string> = {
  bar: "Bar",
  entrance: "Entrée",
};

/** Diamètre en pixels de l'icône — même logique que TAILLE dans PieceTable :
 *  un réglage, pas un calcul. */
export const DIAMETRE_REPERE: Record<LandmarkSize, number> = {
  small: 30,
  medium: 44,
  large: 60,
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

export function secondesDepuis(iso: string | null, maintenant: number): number {
  if (!iso) return 0;
  return Math.max(0, (maintenant - new Date(iso).getTime()) / 1000);
}

/**
 * Le temps d'attente d'une table, qui **monte** et ne s'arrête pas.
 *
 * Pas de seuil, pas de jauge qui se remplit : une salle ne fonctionne pas au
 * chronomètre, elle fonctionne dans l'ordre. Le serveur a besoin de savoir
 * laquelle attend depuis le plus longtemps, pas si une limite est franchie —
 * une limite ne lui apprend rien qu'il puisse faire.
 *
 * Les secondes comptent ici : deux tables qui affichent « 3 min » ne se
 * départagent pas, « 3min12 » et « 3min48 » si.
 */
export function libelleAttente(secondes: number): string {
  return duree(secondes);
}

/**
 * L'ordre d'arrivée des commandes qui attendent d'être prises en charge.
 *
 * Plusieurs tables commandent en même temps — c'est le cas normal d'un service,
 * pas l'exception. Chacune porte donc son rang : 1 est celle qui a commandé en
 * premier, et c'est elle qu'on sert d'abord. Sans ce chiffre, six tables rouges
 * se valent, et le serveur choisit celle qu'il voit plutôt que celle qui
 * attend.
 *
 * Seules les tables en attente de validation sont classées : « prête à servir »
 * ou « addition » ne se font pas la course entre elles.
 */
export function ordreDArrivee(etats: Record<number, EtatTable>): Record<number, number> {
  const enAttente = Object.entries(etats)
    .filter(([, e]) => e.urgence === "a_prendre" && e.depuis)
    .sort((a, b) => new Date(a[1].depuis as string).getTime() - new Date(b[1].depuis as string).getTime());

  const rangs: Record<number, number> = {};
  enAttente.forEach(([id], i) => {
    rangs[Number(id)] = i + 1;
  });
  return rangs;
}
