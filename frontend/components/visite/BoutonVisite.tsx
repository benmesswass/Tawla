"use client";

import { demarrerVisite } from "@/lib/visite/etat";

/**
 * Démarre la visite guidée depuis la page d'accueil, qui est un composant
 * serveur — d'où ce bouton client minuscule plutôt qu'un `onClick` sur place.
 *
 * Un lien `/?visite=1` ne suffirait pas : la navigation côté client ne remonte
 * pas le layout, donc le moteur ne relirait jamais l'URL.
 *
 * Le libellé dit « démo » parce que c'est le mot du restaurateur ; le code, lui,
 * garde « visite » partout, pour ne pas se confondre avec `?demo=1`, qui est
 * l'aide-mémoire du vendeur (`components/DemoGuide.tsx`).
 */
export default function BoutonVisite({
  className = "",
  libelle = "Voir la démo",
}: {
  className?: string;
  libelle?: string;
}) {
  // Pas `onClick={demarrerVisite}` : React passerait l'événement souris en
  // premier argument, donc comme numéro d'étape de départ.
  return (
    <button type="button" onClick={() => demarrerVisite()} className={className}>
      {libelle}
    </button>
  );
}
