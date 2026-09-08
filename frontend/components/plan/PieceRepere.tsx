"use client";

import { LIBELLE_REPERE, PlanLandmark } from "./types";

/**
 * Un repère fixe du plan — le bar, une porte d'entrée. Un rectangle, pas une
 * icône à taille fixe : sa forme EST l'information (l'emplacement réel du
 * bar), remplie à 100 %/100 % de son emplacement (dimensionné en % de la
 * surface par PlanDeSalle). Volontairement discret — pas de couleur d'état,
 * rien qui attire l'œil plus qu'une table qui attend.
 *
 * La poignée de redimensionnement (coin bas-droit) n'a pas ses propres
 * gestionnaires de pointeur : PlanDeSalle les attache sur l'emplacement
 * englobant et distingue la poignée du corps via `data-poignee-redimension`,
 * comme il distingue déjà quelle table est attrapée.
 */

export default function PieceRepere({
  repere,
  selectionnee = false,
  enDeplacement = false,
  editable = false,
  onActiver,
}: {
  repere: PlanLandmark;
  selectionnee?: boolean;
  enDeplacement?: boolean;
  /** Mode éditeur : affiche la poignée quand sélectionné. */
  editable?: boolean;
  onActiver?: () => void;
}) {
  return (
    <div className="repere-cadre" data-deplacement={enDeplacement ? "" : undefined}>
      <button
        type="button"
        onClick={onActiver}
        data-selectionnee={selectionnee ? "" : undefined}
        className="repere-boite"
        aria-label={LIBELLE_REPERE[repere.kind]}
      >
        <svg className="repere-icone" viewBox="0 0 32 32" aria-hidden="true">
          {repere.kind === "bar" ? (
            <>
              <polygon points="6,7 26,7 16,19" />
              <line x1="16" y1="19" x2="16" y2="26" />
              <line x1="10" y1="26" x2="22" y2="26" />
            </>
          ) : (
            <>
              <rect x="9" y="4" width="16" height="24" rx="1.5" />
              <circle cx="20" cy="16" r="1.6" />
            </>
          )}
        </svg>
        <span className="repere-etiquette">{LIBELLE_REPERE[repere.kind]}</span>
      </button>

      {editable && selectionnee && (
        <span className="repere-poignee" data-poignee-redimension="" aria-hidden="true" />
      )}
    </div>
  );
}
