"use client";

import { demarrerVisite } from "@/lib/visite/etat";

/**
 * Démarre la visite guidée depuis la page d'accueil, qui est un composant
 * serveur — d'où ce bouton client minuscule plutôt qu'un `onClick` sur place.
 *
 * Un lien `/?visite=1` ne suffirait pas : la navigation côté client ne remonte
 * pas le layout, donc le moteur ne relirait jamais l'URL.
 */
export default function BoutonVisite({ className = "" }: { className?: string }) {
  // Pas `onClick={demarrerVisite}` : React passerait l'événement souris en
  // premier argument, donc comme numéro d'étape de départ.
  return (
    <button type="button" onClick={() => demarrerVisite()} className={className}>
      Voir la visite guidée
    </button>
  );
}
