"use client";

import { EtatTable, LIBELLE_URGENCE, PlanTable, demandeUnServeur } from "./types";

/**
 * Ce que le serveur peut faire pour la table qu'il vient de toucher (Phase 18.1).
 *
 * Sans ça, le plan ne fait que signaler : il faut ensuite redescendre dans la
 * liste, retrouver la bonne carte, et cliquer. Le plan devenait une décoration
 * posée au-dessus d'une liste.
 *
 * Un seul bouton, celui qui correspond à ce que la table attend — pas un menu.
 * Le serveur a une main libre et dix secondes.
 */

export type ActionsTable = {
  prendreEnCharge?: () => void;
  envoyerEnCuisine?: () => void;
  servir?: () => void;
  encaisser?: () => void;
  resoudreAppel?: () => void;
};

export default function ActionTable({
  table,
  etat,
  actions,
  onFermer,
}: {
  table: PlanTable;
  etat: EtatTable;
  actions: ActionsTable;
  onFermer: () => void;
}) {
  // Une seule action proposée, celle que l'état de la table appelle.
  const principale = (() => {
    if (etat.urgence === "appel" && actions.resoudreAppel)
      return { texte: "Je m'en occupe", agir: actions.resoudreAppel };
    if (etat.urgence === "a_prendre") {
      if (etat.aMoi && actions.envoyerEnCuisine)
        return { texte: "Confirmé → cuisine", agir: actions.envoyerEnCuisine };
      if (actions.prendreEnCharge)
        return { texte: "Prendre en charge", agir: actions.prendreEnCharge };
    }
    if (etat.urgence === "a_servir" && actions.servir)
      return { texte: "Servie", agir: actions.servir };
    if (etat.urgence === "addition" && actions.encaisser)
      return { texte: "Encaissé", agir: actions.encaisser };
    return null;
  })();

  const quoi = demandeUnServeur(etat.urgence)
    ? LIBELLE_URGENCE[etat.urgence]
    : etat.urgence === "en_cuisine"
      ? "en cuisine, rien à faire"
      : "rien à faire";

  return (
    <div className="plan-action">
      <span className="quoi">
        <b>
          {table.label} · {table.seats} couverts
        </b>
        {quoi}
        {etat.parQui && !etat.aMoi ? ` · pris par ${etat.parQui}` : ""}
      </span>
      <span className="boutons">
        {principale && (
          <button type="button" onClick={principale.agir}>
            {principale.texte}
          </button>
        )}
        <button type="button" className="secondaire" onClick={onFermer}>
          Fermer
        </button>
      </span>
    </div>
  );
}
