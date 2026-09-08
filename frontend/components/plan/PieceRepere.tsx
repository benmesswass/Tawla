"use client";

import { DIAMETRE_REPERE, LIBELLE_REPERE, PlanLandmark } from "./types";

/**
 * Un repère fixe du plan — le bar, une porte d'entrée. Volontairement plus
 * discret qu'une table : pas de couleur d'état, pas de chaises, rien qui
 * attire l'œil plus qu'une table qui attend. Il n'est là que pour répondre à
 * une question d'orientation, jamais pour demander une action.
 */

export default function PieceRepere({
  repere,
  selectionnee = false,
  enDeplacement = false,
  onActiver,
}: {
  repere: PlanLandmark;
  selectionnee?: boolean;
  enDeplacement?: boolean;
  onActiver?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onActiver}
      data-selectionnee={selectionnee ? "" : undefined}
      data-deplacement={enDeplacement ? "" : undefined}
      className="repere"
      aria-label={LIBELLE_REPERE[repere.kind]}
    >
      <svg
        className="repere-icone"
        viewBox="0 0 32 32"
        style={{ width: DIAMETRE_REPERE[repere.size], height: DIAMETRE_REPERE[repere.size] }}
        aria-hidden="true"
      >
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
  );
}
