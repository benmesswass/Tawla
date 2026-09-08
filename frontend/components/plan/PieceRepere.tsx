"use client";

import {
  boiteEnglobante,
  contourUnion,
  tronconLePlusGrand,
  tronconVise,
} from "@/lib/formeRepere";
import { LIBELLE_REPERE, PlanLandmark } from "./types";

/**
 * Un repère fixe du plan — le bar, une porte d'entrée. L'union de ses
 * tronçons, pas une icône à taille fixe : sa forme EST l'information
 * (l'emplacement réel du bar, qu'il soit droit, en L ou en U). Volontairement
 * discret — pas de couleur d'état, rien qui attire l'œil plus qu'une table
 * qui attend.
 *
 * Le contour est un seul chemin SVG (voir `contourUnion`) et non un rectangle
 * par tronçon : deux tronçons qui se touchent ne laissent pas de couture au
 * milieu du comptoir, et deux qui se chevauchent ne doublent pas la
 * transparence du remplissage.
 *
 * Les zones cliquables, elles, restent un rectangle par tronçon : c'est ce
 * qui fait que le creux d'un U ne capte rien — une table posée dedans reste
 * attrapable, alors qu'un bloc englobant l'aurait recouverte.
 *
 * Ni les zones ni la poignée n'ont leurs propres gestionnaires de pointeur :
 * PlanDeSalle les attache sur le cadre englobant et distingue le tronçon visé
 * via `data-troncon`, la poignée via `data-poignee-redimension` — comme il
 * distingue déjà quelle table est attrapée.
 */

export default function PieceRepere({
  repere,
  selectionnee = false,
  tronconActif = null,
  enDeplacement = false,
  editable = false,
  onActiver,
}: {
  repere: PlanLandmark;
  selectionnee?: boolean;
  /** Le tronçon visé par le dernier appui — celui que la poignée étire. */
  tronconActif?: number | null;
  enDeplacement?: boolean;
  /** Mode éditeur : affiche la poignée sur le tronçon actif. */
  editable?: boolean;
  onActiver?: (troncon: number) => void;
}) {
  const boite = boiteEnglobante(repere.parts);
  const porteur = tronconLePlusGrand(repere.parts);

  /** Un tronçon replacé dans le cadre englobant, qui porte déjà sa position
   *  sur le plan — sinon chaque tronçon serait positionné deux fois. */
  const dansLeCadre = (troncon: number) => {
    const t = repere.parts[troncon];
    return {
      left: `${((t.pos_x - boite.left) / boite.width) * 100}%`,
      top: `${((t.pos_y - boite.top) / boite.height) * 100}%`,
      width: `${(t.width / boite.width) * 100}%`,
      height: `${(t.height / boite.height) * 100}%`,
    };
  };

  const actif = tronconVise(repere.parts, tronconActif);

  return (
    <div
      className="repere-cadre"
      data-deplacement={enDeplacement ? "" : undefined}
      data-selectionnee={selectionnee ? "" : undefined}
    >
      <svg
        className="repere-forme"
        viewBox={`${boite.left} ${boite.top} ${boite.width} ${boite.height}`}
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        {/* Le cadre est étiré aux dimensions du repère : sans cette exception,
            l'épaisseur du trait le serait aussi, et un comptoir long et fin
            aurait une bordure épaisse sur ses petits côtés. */}
        <path d={contourUnion(repere.parts)} vectorEffect="non-scaling-stroke" />
      </svg>

      {repere.parts.map((_, troncon) => (
        <button
          key={troncon}
          type="button"
          onClick={() => onActiver?.(troncon)}
          data-troncon={troncon}
          className="repere-zone"
          style={dansLeCadre(troncon)}
          aria-label={
            repere.parts.length > 1
              ? `${LIBELLE_REPERE[repere.kind]} — tronçon ${troncon + 1}`
              : LIBELLE_REPERE[repere.kind]
          }
        >
          {/* Icône et étiquette sur le tronçon le plus large, pas au centre du
              cadre : dans un U, ce centre tombe dans le creux, donc à côté du
              bar. */}
          {troncon === porteur && (
            <>
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
            </>
          )}
        </button>
      ))}

      {editable && selectionnee && (
        <span
          className="repere-poignee"
          data-poignee-redimension=""
          data-troncon={actif}
          style={{
            left: `${((repere.parts[actif].pos_x + repere.parts[actif].width - boite.left) / boite.width) * 100}%`,
            top: `${((repere.parts[actif].pos_y + repere.parts[actif].height - boite.top) / boite.height) * 100}%`,
          }}
          aria-hidden="true"
        />
      )}
    </div>
  );
}
