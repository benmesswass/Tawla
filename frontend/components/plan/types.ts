/**
 * Plan de salle — vocabulaire partagé entre la vue de service et l'éditeur.
 */

import { duree } from "@/lib/duree";
import { Troncon } from "@/lib/formeRepere";

export type TableShape = "round" | "square" | "rect";

export type PlanTable = {
  id: number;
  label: string;
  zone: string | null;
  pos_x: number | null;
  pos_y: number | null;
  shape: TableShape;
  seats: number;
  /** Posé au scan du QR, remis à `null` uniquement par « Libérer la table »
   *  (2026-09-09) — jamais par un délai ou une déconnexion. */
  occupied_at: string | null;
};

/**
 * Un repère fixe du plan — le bar, une porte d'entrée. Pas une table : rien
 * à commander, rien à servir, juste de quoi se repérer dans la salle d'un
 * coup d'œil (« la 4 est près de l'entrée »). Toujours posé — contrairement
 * à une table, il n'a pas de réserve où attendre : il naît déjà à sa place.
 *
 * C'est l'**union** de ses tronçons (`Troncon`, un rectangle chacun) : un
 * seul dessine un comptoir droit, deux en équerre un L, trois un U. La forme
 * EST l'information, et elle naît du geste — glisser, étirer, prolonger —
 * jamais d'un préréglage à choisir dans une liste. Un bar peut être un coin
 * comptoir, courir tout un mur, ou tourner autour de la salle.
 */
export type LandmarkKind = "bar" | "entrance";

export type LandmarkPart = Troncon;

export type PlanLandmark = {
  id: number;
  kind: LandmarkKind;
  parts: LandmarkPart[];
};

export const LIBELLE_REPERE: Record<LandmarkKind, string> = {
  bar: "Bar",
  entrance: "Entrée",
};

/**
 * Ce qu'une table demande à un humain, du plus calme au plus urgent.
 *
 * L'ordre compte : une table peut cumuler plusieurs choses (une commande en
 * cuisine ET un appel serveur), et la tuile ne montre que la plus urgente —
 * un serveur qui traverse la salle a besoin d'une réponse, pas d'un inventaire.
 */
export const URGENCES = ["libre", "occupee", "en_cuisine", "a_servir", "addition", "a_prendre", "appel"] as const;
export type Urgence = (typeof URGENCES)[number];

export const LIBELLE_URGENCE: Record<Urgence, string> = {
  libre: "",
  // Installés, personne à prévenir — le libellé ne sert qu'à l'aria-label,
  // jamais affiché tel quel sur la tuile (voir ActionTable.tsx).
  occupee: "installés",
  en_cuisine: "en cuisine",
  a_servir: "prête à servir",
  addition: "addition",
  a_prendre: "à prendre",
  appel: "vous appelle",
};

/** Les états qui demandent un déplacement maintenant. */
export function demandeUnServeur(urgence: Urgence): boolean {
  return urgence !== "libre" && urgence !== "occupee" && urgence !== "en_cuisine";
}

/**
 * Ce que la table a réglé — délibérément HORS de `URGENCES`.
 *
 * Un règlement ne demande rien à personne : le ranger dans l'échelle
 * d'urgence aurait fait disparaître l'appel d'une table qui vient de payer,
 * puisqu'une tuile ne montre que son état le plus urgent (voir `etats.ts`).
 * C'est donc un second canal visuel, comme le rang d'arrivée et « ma table ».
 *
 * `aucun` couvre les deux cas où il n'y a rien à dire : personne n'a encore
 * payé, ou la table n'a pas de commande du tout.
 */
export const REGLEMENTS = ["aucun", "partiel", "total"] as const;
export type Reglement = (typeof REGLEMENTS)[number];

export const LIBELLE_REGLEMENT: Record<Reglement, string> = {
  aucun: "",
  partiel: "partiellement réglée",
  total: "entièrement réglée",
};

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
