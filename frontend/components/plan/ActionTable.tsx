"use client";

import { useEffect, useState } from "react";
import {
  EtatTable,
  LIBELLE_URGENCE,
  PlanTable,
  demandeUnServeur,
  libelleAttente,
  secondesDepuis,
} from "./types";

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
  rang = null,
  actions,
  onFermer,
}: {
  table: PlanTable;
  etat: EtatTable;
  /** Rang d'arrivée parmi les tables qui attendent d'être prises en charge. */
  rang?: number | null;
  actions: ActionsTable;
  onFermer: () => void;
}) {
  // Le panneau tient son propre battement : il reste ouvert pendant que le
  // serveur traverse la salle, et une attente figée sur « à l'instant » pendant
  // cinq minutes lui mentirait.
  const [maintenant, setMaintenant] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setMaintenant(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  // Une seule action proposée, celle que l'état de la table appelle. La
  // couleur suit le statut visé, pas une règle unique : Servie en menthe,
  // Encaissé en laiton, le reste (prise en charge, appel) en harissa.
  const principale = (() => {
    if (etat.urgence === "appel" && actions.resoudreAppel)
      return { texte: "Je m'en occupe", agir: actions.resoudreAppel, tone: "harissa" as const };
    if (etat.urgence === "a_prendre") {
      if (etat.aMoi && actions.envoyerEnCuisine)
        return { texte: "Confirmé → cuisine", agir: actions.envoyerEnCuisine, tone: "harissa" as const };
      if (actions.prendreEnCharge)
        return { texte: "Prendre en charge", agir: actions.prendreEnCharge, tone: "harissa" as const };
    }
    if (etat.urgence === "a_servir" && actions.servir)
      return { texte: "Servie", agir: actions.servir, tone: "menthe" as const };
    if (etat.urgence === "addition" && actions.encaisser)
      return { texte: "Encaissé", agir: actions.encaisser, tone: "laiton" as const };
    return null;
  })();

  const quoi = demandeUnServeur(etat.urgence)
    ? LIBELLE_URGENCE[etat.urgence]
    : etat.urgence === "en_cuisine"
      ? "en cuisine, rien à faire"
      : "rien à faire";

  // « depuis 4 min » plutôt qu'une heure d'horloge : le serveur veut une durée,
  // pas à faire la soustraction lui-même.
  const depuis =
    demandeUnServeur(etat.urgence) && etat.depuis
      ? ` depuis ${libelleAttente(secondesDepuis(etat.depuis, maintenant))}`
      : "";
  const ordre = rang ? ` · ${rang}${rang === 1 ? "re" : "e"} à avoir commandé` : "";

  return (
    <div className="plan-action">
      <span className="quoi">
        <b>
          {table.label} · {table.seats} couverts
        </b>
        {quoi}
        {depuis}
        {ordre}
        {etat.parQui && !etat.aMoi ? ` · pris par ${etat.parQui}` : ""}
      </span>
      <span className="boutons">
        {principale && (
          <button
            type="button"
            onClick={principale.agir}
            style={{
              background:
                principale.tone === "menthe"
                  ? "var(--menthe)"
                  : principale.tone === "laiton"
                    ? "var(--laiton)"
                    : "var(--harissa)",
              color: principale.tone === "laiton" ? "var(--espresso)" : "#fff",
            }}
          >
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
