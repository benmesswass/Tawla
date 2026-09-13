"use client";

import { useEffect, useState } from "react";
import { Order, TableSettlement } from "@/lib/api";
import { formatMoney } from "@/lib/currency";
import { LIBELLE_MOYEN } from "@/lib/moyenDePaiement";
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
  /** Encaisser ce qu'il reste dû SANS que la table l'ait demandé depuis son
   *  téléphone — le règlement en espèces au comptoir, qui n'avait aucun
   *  chemin jusqu'ici. Distinct d'`encaisser`, qui close une demande déjà
   *  affichée. */
  encaisserLeRestant?: () => void;
  resoudreAppel?: () => void;
  /** Présent uniquement si la table est occupée — jamais gêné par une
   *  urgence en cours (voir CLAUDE.md, 2026-09-09) : libérer ne fait
   *  disparaître ni la commande ni l'addition en attente, qui restent
   *  visibles pour toute autre table tant qu'elles ne sont pas traitées. */
  libererTable?: () => void;
};

export default function ActionTable({
  table,
  etat,
  rang = null,
  actions,
  commandeItems,
  reglement = null,
  onFermer,
}: {
  table: PlanTable;
  etat: EtatTable;
  /** Rang d'arrivée parmi les tables qui attendent d'être prises en charge. */
  rang?: number | null;
  actions: ActionsTable;
  /** Ce que la table a réglé aujourd'hui, toutes ses commandes confondues —
   *  null quand elle n'a aucune commande dans l'occupation en cours. */
  reglement?: TableSettlement | null;
  /** Articles de la commande en attente de confirmation — affichés pour que
   *  le serveur les relise avec la table avant de cliquer "Confirmé → cuisine". */
  commandeItems?: Order["items"];
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
      : etat.urgence === "occupee"
        ? "installés, rien à faire"
        : "rien à faire";

  // « depuis 4 min » plutôt qu'une heure d'horloge : le serveur veut une durée,
  // pas à faire la soustraction lui-même.
  const depuis =
    demandeUnServeur(etat.urgence) && etat.depuis
      ? ` depuis ${libelleAttente(secondesDepuis(etat.depuis, maintenant))}`
      : "";
  const ordre = rang ? ` · ${rang}${rang === 1 ? "re" : "e"} à avoir commandé` : "";

  // La liste des articles n'a de sens que juste avant "Confirmé → cuisine" :
  // c'est le seul moment où le serveur doit la relire avec la table.
  const aRelire = principale?.texte === "Confirmé → cuisine" && commandeItems && commandeItems.length > 0;

  // Ce que la table a réglé. Une ligne, toujours au même endroit : c'est la
  // seule réponse à « est-ce que je peux libérer cette table ». Jusqu'ici la
  // seule information disponible était l'ABSENCE de rouge sur le plan.
  const aRegler = reglement && reglement.orders_count > 0;
  const reste = reglement ? reglement.amount_remaining : 0;
  const etatDuReglement = !aRegler
    ? null
    : reglement.fully_paid
      ? { texte: `Entièrement réglée — ${formatMoney(reglement.amount_paid)}`, tone: "menthe" as const }
      : reglement.amount_paid > 0
        ? {
            texte: `Reste ${formatMoney(reste)} sur ${formatMoney(reglement.total_amount)}`,
            tone: "laiton" as const,
          }
        : { texte: `À encaisser — ${formatMoney(reste)}`, tone: "laiton" as const };

  // Proposé quand la table n'attend rien de plus pressé : un serveur qui doit
  // encore confirmer une commande ou apporter un plat n'encaisse pas d'abord,
  // et trois boutons côte à côte ne se lisent pas en dix secondes. Le cas
  // visé est la table installée qui a fini de manger — celle, précisément,
  // qui n'apparaissait nulle part.
  //
  // Le bouton annonce ce que CE clic encaisse, c'est-à-dire l'addition la plus
  // ancienne encore due — pas le total de la table, qui peut porter deux
  // commandes (la ligne au-dessus, elle, dit bien le total).
  const aEncaisser = reglement?.dues[0];
  const peutEncaisser = !principale && actions.encaisserLeRestant && aEncaisser;

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
      {etatDuReglement && (
        <span className="plan-action-reglement" data-tone={etatDuReglement.tone}>
          {etatDuReglement.texte}
          {aRegler && reglement.parts.length > 0 && (
            <span className="plan-action-parts">
              {reglement.parts.slice(0, 3).map((part) => (
                <span key={part.payment_id}>
                  {LIBELLE_MOYEN[part.method]} · {formatMoney(part.amount)}
                  {part.payer_name ? ` · ${part.payer_name}` : ""}
                  {part.collected_by_name ? ` · encaissé par ${part.collected_by_name}` : ""}
                </span>
              ))}
            </span>
          )}
        </span>
      )}
      {aRelire && (
        <div className="plan-action-commande">
          {commandeItems.map((item) => (
            <div key={item.id} className="plan-action-item">
              <span>
                {item.quantity}x {item.menu_item_name}
              </span>
              {(item.notes || item.options.length > 0) && (
                <span className="plan-action-item-detail">
                  {[item.notes, ...item.options.map((opt) => opt.option_name)].filter(Boolean).join(" · ")}
                </span>
              )}
            </div>
          ))}
          <p className="plan-action-relire">Lisez la commande à voix haute avec la table avant de valider.</p>
        </div>
      )}
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
        {peutEncaisser && (
          <button
            type="button"
            onClick={actions.encaisserLeRestant}
            style={{ background: "var(--laiton)", color: "var(--espresso)" }}
          >
            Encaisser {formatMoney(aEncaisser.amount_remaining)}
          </button>
        )}
        {actions.libererTable && (
          <button type="button" className="secondaire" onClick={actions.libererTable}>
            Libérer la table
          </button>
        )}
        <button type="button" className="secondaire" onClick={onFermer}>
          Fermer
        </button>
      </span>
    </div>
  );
}
