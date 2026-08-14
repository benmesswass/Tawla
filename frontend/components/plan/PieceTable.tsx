"use client";

import { EtatTable, LIBELLE_URGENCE, PlanTable, demandeUnServeur, pression, secondesDepuis } from "./types";

/**
 * Une table dessinée sur le plan.
 *
 * Trois décisions de lecture, dans cet ordre de priorité pour un serveur qui
 * traverse la salle :
 *
 * 1. **La couleur dit s'il faut y aller.** Sable = rien à faire ; ardoise =
 *    quelque chose se passe mais en cuisine, pas pour lui ; harissa = on
 *    l'attend.
 * 2. **L'anneau dit depuis combien de temps**, et il se referme exactement
 *    quand la commande devient « perdue » au sens de la page de preuve. C'est
 *    un compte à rebours avant perte d'argent, pas un ornement.
 * 3. **Le compteur en minutes** donne le chiffre quand il s'approche.
 *
 * Pas de clignotement : dans une salle, ce qui clignote est ignoré au bout de
 * dix minutes, ou insupportable. Seule la table la plus urgente respire
 * lentement, et cette respiration s'arrête sous `prefers-reduced-motion`.
 */

const TAILLE: Record<PlanTable["shape"], { w: number; h: number; r: number }> = {
  round: { w: 84, h: 84, r: 42 },
  square: { w: 80, h: 80, r: 16 },
  rect: { w: 116, h: 72, r: 16 },
};

export default function PieceTable({
  table,
  etat,
  maintenant,
  laPlusUrgente = false,
  selectionnee = false,
  onActiver,
  enDeplacement = false,
}: {
  table: PlanTable;
  etat: EtatTable;
  maintenant: number;
  laPlusUrgente?: boolean;
  selectionnee?: boolean;
  onActiver?: () => void;
  enDeplacement?: boolean;
}) {
  const { w, h, r } = TAILLE[table.shape];
  const appelle = demandeUnServeur(etat.urgence);
  const p = pression(etat, maintenant);
  const minutes = Math.floor(secondesDepuis(etat.depuis, maintenant) / 60);
  // Au-delà d'une heure le chiffre exact n'apprend plus rien, et un « 1946 min »
  // sur une table décrédibilise tout l'écran.
  const attente = minutes >= 60 ? "+1 h" : `${minutes} min`;

  // Le périmètre exact du contour, pour que l'anneau épouse la forme réelle de
  // la table plutôt que d'être un cercle plaqué par-dessus.
  const perimetre = 2 * (w - 2 * r) + 2 * (h - 2 * r) + 2 * Math.PI * r;

  const tone = appelle ? "appelle" : etat.urgence === "en_cuisine" ? "cuisine" : "libre";

  return (
    <button
      type="button"
      onClick={onActiver}
      data-tone={tone}
      data-urgente={laPlusUrgente ? "" : undefined}
      data-selectionnee={selectionnee ? "" : undefined}
      data-deplacement={enDeplacement ? "" : undefined}
      className="piece"
      style={{ width: w, height: h }}
      aria-label={
        appelle
          ? `${table.label} — ${LIBELLE_URGENCE[etat.urgence]} depuis ${attente}`
          : `${table.label} — ${LIBELLE_URGENCE[etat.urgence] || "rien à faire"}`
      }
    >
      <svg className="anneau" viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
        <rect
          x="2"
          y="2"
          width={w - 4}
          height={h - 4}
          rx={Math.max(0, r - 2)}
          className="anneau-fond"
        />
        {appelle && (
          <rect
            x="2"
            y="2"
            width={w - 4}
            height={h - 4}
            rx={Math.max(0, r - 2)}
            className="anneau-jauge"
            style={{
              strokeDasharray: perimetre,
              strokeDashoffset: perimetre * (1 - p),
            }}
          />
        )}
      </svg>

      <span className="etiquette">{table.label}</span>
      {appelle && minutes >= 1 && <span className="minutes">{attente}</span>}
      {!appelle && etat.urgence === "en_cuisine" && <span className="minutes">en cuisine</span>}
      {etat.aMoi && <span className="mienne" aria-hidden="true" />}
    </button>
  );
}
