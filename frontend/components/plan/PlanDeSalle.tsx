"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { boiteEnglobante } from "@/lib/formeRepere";
import PieceTable from "./PieceTable";
import PieceRepere from "./PieceRepere";
import {
  ETAT_LIBRE,
  EtatTable,
  PlanLandmark,
  PlanTable,
  Reglement,
  URGENCES,
  demandeUnServeur,
  ordreDArrivee,
  secondesDepuis,
} from "./types";

/**
 * Le plan de salle.
 *
 * Sert deux écrans avec le même dessin : la vue de service (le serveur lit) et
 * l'éditeur (le manager pose ses tables). Un seul rendu, donc ce que le manager
 * dispose est exactement ce que le serveur verra — pas deux représentations
 * qui divergent.
 *
 * Les zones ne sont pas dessinées à la main : elles se déduisent de l'endroit
 * où les tables ont été posées. Le manager place ses tables, la terrasse
 * apparaît toute seule autour de celles qui lui appartiennent.
 */

const MARGE_ZONE = 7; // en % — l'air autour des tables d'une même zone

type Props = {
  tables: PlanTable[];
  /** Repères fixes (bar, entrée) — purement visuels côté service. */
  landmarks?: PlanLandmark[];
  etats?: Record<number, EtatTable>;
  /** Ce que chaque table a réglé — second canal visuel, jamais fondu dans
   *  `etats` : un règlement ne demande rien, il ne doit donc jamais masquer
   *  l'urgence d'une table qui a payé ET qui appelle. */
  reglements?: Record<number, Reglement>;
  onTableActivee?: (table: PlanTable) => void;
  tableSelectionnee?: number | null;
  /** Mode éditeur : les tables se déplacent à la souris ou au doigt. */
  editable?: boolean;
  onDeplacer?: (tableId: number, x: number, y: number) => void;
  /** Repère sélectionné (éditeur uniquement — pour lui proposer un retrait).
   *  Le tronçon visé vient avec : c'est lui que la poignée étirera, et lui que
   *  « Prolonger » coudera. */
  onRepereActive?: (repere: PlanLandmark, troncon: number) => void;
  repereSelectionne?: number | null;
  tronconSelectionne?: number | null;
  onDeplacerRepere?: (repereId: number, troncon: number, x: number, y: number) => void;
  /** Glisser la poignée du coin : recalculée à chaque mouvement depuis la
   *  position du pointeur, jamais un delta cumulé. */
  onRedimensionnerRepere?: (
    repereId: number,
    troncon: number,
    largeur: number,
    hauteur: number
  ) => void;
  /**
   * Panneau d'action pour la table sélectionnée. Rendu **sous** la salle et
   * non par-dessus : posé en surimpression, il recouvrait justement la table
   * dont il parle — et sur un téléphone, la moitié de la salle avec.
   */
  action?: React.ReactNode;
};

function zonesDessinees(tables: PlanTable[]) {
  const parZone = new Map<string, PlanTable[]>();
  for (const t of tables) {
    if (t.pos_x === null || t.pos_y === null || !t.zone) continue;
    const liste = parZone.get(t.zone) ?? [];
    liste.push(t);
    parZone.set(t.zone, liste);
  }
  return [...parZone.entries()].map(([nom, membres]) => {
    const xs = membres.map((t) => t.pos_x as number);
    const ys = membres.map((t) => t.pos_y as number);
    return {
      nom,
      gauche: Math.max(0, Math.min(...xs) - MARGE_ZONE),
      haut: Math.max(0, Math.min(...ys) - MARGE_ZONE),
      droite: Math.min(100, Math.max(...xs) + MARGE_ZONE),
      bas: Math.min(100, Math.max(...ys) + MARGE_ZONE),
    };
  });
}

export default function PlanDeSalle({
  tables,
  landmarks = [],
  etats = {},
  reglements = {},
  onTableActivee,
  tableSelectionnee = null,
  editable = false,
  onDeplacer,
  onRepereActive,
  repereSelectionne = null,
  tronconSelectionne = null,
  onDeplacerRepere,
  onRedimensionnerRepere,
  action,
}: Props) {
  const surface = useRef<HTMLDivElement>(null);
  // Une table et un repère peuvent partager le même id (deux séquences
  // distinctes côté serveur) : sans le type dans la clé, attraper la table 1
  // ferait aussi bouger le repère 1. "redimension" est un troisième geste
  // possible sur un repère, distinct du déplacement de son corps — et sur un
  // repère coudé, les deux visent un tronçon précis, pas la forme entière.
  const [attrapee, setAttrapee] = useState<
    { type: "table" | "repere" | "redimension"; id: number; troncon: number } | null
  >(null);

  // Les compteurs avancent tout seuls : sans ce battement, une table qui attend
  // depuis huit minutes en afficherait toujours deux. À la seconde, puisque
  // c'est à la seconde que le temps s'affiche.
  const [maintenant, setMaintenant] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setMaintenant(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const posees = useMemo(
    () => tables.filter((t) => t.pos_x !== null && t.pos_y !== null),
    [tables]
  );
  // Un repère sans tronçon n'a pas de boîte englobante — impossible via
  // l'API, mais un cadre positionné sur NaN passerait inaperçu à l'écriture
  // et sauterait aux yeux à l'écran.
  const dessinables = useMemo(() => landmarks.filter((r) => r.parts.length > 0), [landmarks]);
  const zones = useMemo(() => zonesDessinees(posees), [posees]);

  // L'ordre d'arrivée des commandes en attente de validation : c'est lui qui
  // dit au serveur par quelle table commencer quand plusieurs l'appellent.
  const rangs = useMemo(() => ordreDArrivee(etats), [etats]);

  // Une seule table respire : celle qui attend depuis le plus longtemps. En
  // faire respirer trois transformerait la salle en sapin de Noël. À attente
  // égale, l'état le plus urgent l'emporte (un appel passe devant une addition).
  const laPlusUrgente = useMemo(() => {
    let gagnante: number | null = null;
    let record = -1;
    for (const t of posees) {
      const etat = etats[t.id] ?? ETAT_LIBRE;
      if (!demandeUnServeur(etat.urgence)) continue;
      const score = secondesDepuis(etat.depuis, maintenant) + URGENCES.indexOf(etat.urgence);
      if (score > record) {
        record = score;
        gagnante = t.id;
      }
    }
    return gagnante;
  }, [posees, etats, maintenant]);

  function positionDepuisEvenement(e: React.PointerEvent) {
    const boite = surface.current?.getBoundingClientRect();
    if (!boite) return null;
    // Bornée à 4 % des murs : au ras du bord, une table déborde du cadre et se
    // fait rogner — surtout sur un téléphone, où la salle est plus étroite que
    // les tables ne sont petites.
    // Aimantation sur une grille de 4 % : la salle reste droite sans que le
    // manager ait à viser, et deux tables alignées le restent.
    const pas = 4;
    const aimante = (v: number) => Math.round(Math.min(96, Math.max(4, v)) / pas) * pas;
    return {
      x: aimante(((e.clientX - boite.left) / boite.width) * 100),
      y: aimante(((e.clientY - boite.top) / boite.height) * 100),
    };
  }

  return (
    <div className="plan-cadre">
      <div className="plan-surface" ref={surface} data-editable={editable ? "" : undefined}>
        {zones.map((z) => (
          <div
            key={z.nom}
            className="plan-zone"
            style={{
              left: `${z.gauche}%`,
              top: `${z.haut}%`,
              width: `${z.droite - z.gauche}%`,
              height: `${z.bas - z.haut}%`,
            }}
          >
            <span className="plan-zone-nom">{z.nom}</span>
          </div>
        ))}

        {posees.map((table) => (
          <div
            key={table.id}
            className="plan-emplacement"
            style={{ left: `${table.pos_x}%`, top: `${table.pos_y}%` }}
            onPointerDown={
              editable
                ? (e) => {
                    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
                    setAttrapee({ type: "table", id: table.id, troncon: 0 });
                  }
                : undefined
            }
            onPointerMove={
              editable && attrapee?.type === "table" && attrapee.id === table.id
                ? (e) => {
                    const p = positionDepuisEvenement(e);
                    if (p) onDeplacer?.(table.id, p.x, p.y);
                  }
                : undefined
            }
            onPointerUp={editable ? () => setAttrapee(null) : undefined}
            onPointerCancel={editable ? () => setAttrapee(null) : undefined}
          >
            <PieceTable
              table={table}
              etat={etats[table.id] ?? ETAT_LIBRE}
              maintenant={maintenant}
              rang={rangs[table.id] ?? null}
              reglement={reglements[table.id] ?? "aucun"}
              laPlusUrgente={table.id === laPlusUrgente}
              selectionnee={table.id === tableSelectionnee}
              enDeplacement={attrapee?.type === "table" && attrapee.id === table.id}
              onActiver={() => onTableActivee?.(table)}
            />
          </div>
        ))}

        {dessinables.map((repere) => {
          // Le cadre est la boîte englobante des tronçons, pas un rectangle
          // stocké : un repère coudé n'a plus de « son » rectangle, et le
          // creux d'un U ne doit rien capter (voir .plan-emplacement-repere).
          const boite = boiteEnglobante(repere.parts);
          return (
            <div
              key={`repere-${repere.id}`}
              className="plan-emplacement-repere"
              style={{
                left: `${boite.left}%`,
                top: `${boite.top}%`,
                width: `${boite.width}%`,
                height: `${boite.height}%`,
              }}
              onPointerDown={
                editable
                  ? (e) => {
                      const cible = e.target as HTMLElement;
                      // La poignée et les tronçons sont des éléments à part
                      // (voir PieceRepere) : les repérer par leurs attributs
                      // évite de faire remonter le geste jusqu'ici via des
                      // props dédiées pour un booléen et un index.
                      const surPoignee = cible.hasAttribute("data-poignee-redimension");
                      cible.setPointerCapture?.(e.pointerId);
                      setAttrapee({
                        type: surPoignee ? "redimension" : "repere",
                        id: repere.id,
                        troncon: Number(cible.getAttribute("data-troncon") ?? 0),
                      });
                    }
                  : undefined
              }
              onPointerMove={
                editable &&
                attrapee?.id === repere.id &&
                (attrapee.type === "repere" || attrapee.type === "redimension")
                  ? (e) => {
                      const p = positionDepuisEvenement(e);
                      const troncon = repere.parts[attrapee.troncon];
                      if (!p || !troncon) return;
                      if (attrapee.type === "redimension") {
                        // Le coin haut-gauche (pos_x/pos_y) ne bouge pas : seule la
                        // largeur/hauteur suit le pointeur, comme étirer un coin
                        // dans n'importe quel outil de dessin.
                        onRedimensionnerRepere?.(
                          repere.id,
                          attrapee.troncon,
                          p.x - troncon.pos_x,
                          p.y - troncon.pos_y
                        );
                      } else {
                        onDeplacerRepere?.(repere.id, attrapee.troncon, p.x, p.y);
                      }
                    }
                  : undefined
              }
              onPointerUp={editable ? () => setAttrapee(null) : undefined}
              onPointerCancel={editable ? () => setAttrapee(null) : undefined}
            >
              <PieceRepere
                repere={repere}
                selectionnee={repere.id === repereSelectionne}
                tronconActif={repere.id === repereSelectionne ? tronconSelectionne : null}
                enDeplacement={attrapee?.type === "repere" && attrapee.id === repere.id}
                editable={editable}
                onActiver={(troncon) => onRepereActive?.(repere, troncon)}
              />
            </div>
          );
        })}

        {posees.length === 0 && dessinables.length === 0 && (
          <p className="plan-vide">
            {editable
              ? "Faites glisser vos tables depuis la liste ci-dessous pour dessiner votre salle."
              : "Votre salle n'est pas encore dessinée."}
          </p>
        )}
      </div>

      {action}
    </div>
  );
}
