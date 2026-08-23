"use client";

import { useEffect } from "react";
import { setToken } from "@/lib/auth";

const PARAM = "demo_token";

/**
 * Ouvre un écran staff/cuisine/manager déjà connecté depuis un lien, sur un
 * appareil qui n'a jamais vu cette démo.
 *
 * Nécessaire parce que les comptes serveur et cuisine d'une démo ont un mot
 * de passe généré aléatoirement, jamais révélé nulle part (voir
 * `backend/app/modules/demo/service.py::creer_demo`) — sans ce mécanisme, il
 * n'existe aucun moyen de s'y connecter depuis un deuxième appareil, et
 * montrer l'écran serveur en direct pendant qu'un vrai client commande sur
 * le sien était impossible : un seul onglet ne peut pas jouer les deux rôles
 * à la fois.
 *
 * À appeler en tout premier dans le corps de la page, avant
 * `useCurrentStaff` : les effets d'un composant s'exécutent dans l'ordre où
 * ses hooks ont été appelés pendant le rendu, donc ce `useEffect`, déclaré en
 * premier, pose le jeton avant que `useCurrentStaff` ne vérifie sa présence.
 */
export function useAccesDemoParLien(): void {
  useEffect(() => {
    const jeton = new URLSearchParams(window.location.search).get(PARAM);
    if (!jeton) return;
    setToken(jeton);
    // Retire le jeton de l'adresse : il ne doit ni traîner dans l'historique
    // du navigateur, ni être visible si l'écran est projeté en rendez-vous.
    window.history.replaceState(null, "", window.location.pathname);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

/** Construit le lien à copier pour ouvrir `route`, déjà connecté, ailleurs. */
export function lienDemo(route: string, jeton: string): string {
  return `${window.location.origin}${route}?${PARAM}=${encodeURIComponent(jeton)}`;
}
