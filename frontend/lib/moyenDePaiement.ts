import { PaymentMethod } from "./api";

/**
 * Ce qu'un membre du personnel lit pour un moyen de paiement.
 *
 * Écrans staff (`/staff`, `/dashboard`) uniquement, donc en français : le
 * parcours client, lui, est bilingue et passe par `lib/i18n` — un dictionnaire
 * arabe n'a rien à faire ici, et ces libellés n'ont rien à y faire non plus.
 *
 * « carte en salle » plutôt que « carte physique » ou « terminal » : c'est ce
 * qu'un serveur dit, et ça se distingue d'un coup d'œil de « carte en ligne »,
 * qui est la seule des trois que personne n'encaisse.
 */
export const LIBELLE_MOYEN: Record<PaymentMethod, string> = {
  cash: "espèces",
  card_terminal: "carte en salle",
  card: "carte en ligne",
};
