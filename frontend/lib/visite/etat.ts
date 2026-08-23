/**
 * État de la visite guidée : démarrage, reprise, arrêt.
 *
 * Isolé du moteur (`components/visite/VisiteGuidee.tsx`) parce que deux autres
 * endroits en ont besoin sans rien connaître du rendu : le bouton « Visite
 * guidée » de la page d'accueil, et l'aide-mémoire de démo (`DemoGuide`) qui
 * s'efface quand la visite tourne — deux panneaux flottants à la fois en
 * rendez-vous, c'est un de trop.
 */

import type { Parcours } from "./etapes";

export const CLE_ACTIVE = "tawlaVisiteActive";
export const CLE_ETAPE = "tawlaVisiteEtape";
export const CLE_PARCOURS = "tawlaVisiteParcours";
export const CLE_DEMO = "tawlaDemoSession";

/**
 * L'établissement jetable ouvert pour cette démo. Gardé ici parce que deux
 * choses en dépendent après le clic : le bandeau qui annonce l'échéance, et
 * l'étape finale qui propose d'ouvrir la carte de la table — la seule façon
 * d'atteindre le parcours client depuis un ordinateur.
 */
export type SessionDemo = { qrToken: string; expireLe: string; nom: string };

export function sessionDemo(): SessionDemo | null {
  try {
    const brut = window.localStorage.getItem(CLE_DEMO);
    if (!brut) return null;
    const session = JSON.parse(brut) as SessionDemo;
    // Une session échue ne vaut rien : le backend a déjà effacé
    // l'établissement, les liens qu'elle porte mènent à un 404.
    if (new Date(session.expireLe).getTime() <= Date.now()) return null;
    return session;
  } catch {
    return null;
  }
}

export function enregistrerSessionDemo(session: SessionDemo): void {
  try {
    window.localStorage.setItem(CLE_DEMO, JSON.stringify(session));
  } catch {
    /* voir visiteEnCours */
  }
}

/**
 * La visite démarre aussi depuis un bouton, donc sans rechargement de page :
 * le moteur est monté une fois dans le layout et ne relit pas l'URL à chaque
 * navigation client. Cet événement est le seul lien entre les deux.
 */
export const EVENEMENT_VISITE = "tawla:visite";

export function visiteEnCours(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(CLE_ACTIVE) === "1";
  } catch {
    // Navigation privée verrouillée : pas de visite, mais pas de page cassée.
    return false;
  }
}

/** Ouvre la visite à une étape précise d'un parcours (voir `resoudreVisite`). */
export function demarrerVisite(depuis = 0, parcours: Parcours = "vente"): void {
  try {
    window.localStorage.setItem(CLE_ACTIVE, "1");
    window.localStorage.setItem(CLE_ETAPE, String(depuis));
    window.localStorage.setItem(CLE_PARCOURS, parcours);
  } catch {
    /* voir visiteEnCours */
  }
  window.dispatchEvent(new CustomEvent(EVENEMENT_VISITE));
}

export function arreterVisite(): void {
  try {
    window.localStorage.removeItem(CLE_ACTIVE);
    window.localStorage.removeItem(CLE_ETAPE);
    window.localStorage.removeItem(CLE_PARCOURS);
    // La session de démo, elle, survit à la fermeture de la visite : le
    // visiteur qui referme les bulles doit pouvoir continuer à cliquer dans
    // le produit jusqu'à l'échéance.
  } catch {
    /* voir visiteEnCours */
  }
  window.dispatchEvent(new CustomEvent(EVENEMENT_VISITE));
}

export function enregistrerEtape(index: number): void {
  try {
    window.localStorage.setItem(CLE_ETAPE, String(index));
  } catch {
    /* voir visiteEnCours */
  }
}

export function parcoursEnregistre(): Parcours {
  try {
    return window.localStorage.getItem(CLE_PARCOURS) === "client" ? "client" : "vente";
  } catch {
    return "vente";
  }
}

export function etapeEnregistree(): number {
  try {
    const brut = Number(window.localStorage.getItem(CLE_ETAPE));
    return Number.isFinite(brut) && brut >= 0 ? Math.trunc(brut) : 0;
  } catch {
    return 0;
  }
}
