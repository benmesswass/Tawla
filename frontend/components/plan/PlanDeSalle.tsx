"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import PieceTable from "./PieceTable";
import { ETAT_LIBRE, EtatTable, PlanTable, URGENCES, demandeUnServeur, pression } from "./types";

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
  etats?: Record<number, EtatTable>;
  onTableActivee?: (table: PlanTable) => void;
  tableSelectionnee?: number | null;
  /** Mode éditeur : les tables se déplacent à la souris ou au doigt. */
  editable?: boolean;
  onDeplacer?: (tableId: number, x: number, y: number) => void;
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
  etats = {},
  onTableActivee,
  tableSelectionnee = null,
  editable = false,
  onDeplacer,
  action,
}: Props) {
  const surface = useRef<HTMLDivElement>(null);
  const [attrapee, setAttrapee] = useState<number | null>(null);

  // Le compte à rebours des anneaux avance tout seul : sans ce battement, une
  // table qui attend depuis huit minutes en afficherait toujours deux.
  const [maintenant, setMaintenant] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setMaintenant(Date.now()), 5000);
    return () => clearInterval(t);
  }, []);

  const posees = useMemo(
    () => tables.filter((t) => t.pos_x !== null && t.pos_y !== null),
    [tables]
  );
  const zones = useMemo(() => zonesDessinees(posees), [posees]);

  // Une seule table respire : celle qui attend depuis le plus longtemps. En
  // faire respirer trois transformerait la salle en sapin de Noël.
  const laPlusUrgente = useMemo(() => {
    let gagnante: number | null = null;
    let record = 0;
    for (const t of posees) {
      const etat = etats[t.id] ?? ETAT_LIBRE;
      if (!demandeUnServeur(etat.urgence)) continue;
      const p = pression(etat, maintenant);
      const rang = URGENCES.indexOf(etat.urgence) / 100;
      if (p + rang > record) {
        record = p + rang;
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
                    setAttrapee(table.id);
                  }
                : undefined
            }
            onPointerMove={
              editable && attrapee === table.id
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
              laPlusUrgente={table.id === laPlusUrgente}
              selectionnee={table.id === tableSelectionnee}
              enDeplacement={attrapee === table.id}
              onActiver={() => onTableActivee?.(table)}
            />
          </div>
        ))}

        {posees.length === 0 && (
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
