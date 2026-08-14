"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { PlanTable, TableShape } from "@/lib/api";
import PlanDeSalle from "./PlanDeSalle";

/**
 * Le manager dessine sa salle (Phase 18).
 *
 * Deux partis pris, tirés du seul critère qui compte ici — un restaurateur
 * doit pouvoir poser sa salle sans qu'on lui explique :
 *
 * 1. **Rien à enregistrer.** Le plan se sauvegarde tout seul une seconde après
 *    le dernier geste. Un bouton « Enregistrer » ne sert qu'à donner au manager
 *    l'occasion de perdre son travail en fermant l'onglet.
 * 2. **On règle des couverts, pas des formes.** Personne ne se dit « ma table
 *    est rectangulaire » ; il se dit « c'est une table de six ». La forme suit
 *    le nombre de couverts, et reste rattrapable pour les cas particuliers.
 *
 * Une table nouvellement créée n'apparaît pas d'office sur le plan : elle
 * attend dans la réserve, en dessous. Les poser toutes empilerait la salle
 * dans un coin, et le manager devrait défaire avant de faire.
 */

const COUVERTS = [2, 4, 6, 8];

const FORMES: { valeur: TableShape; nom: string }[] = [
  { valeur: "round", nom: "Ronde" },
  { valeur: "square", nom: "Carrée" },
  { valeur: "rect", nom: "Longue" },
];

/** Temps de calme après le dernier geste avant d'écrire. */
const DELAI_ENREGISTREMENT = 1000;

export type Placement = {
  table_id: number;
  pos_x: number;
  pos_y: number;
  shape: TableShape;
  seats: number;
};

export default function EditeurDePlan({
  tables,
  onEnregistrer,
  enregistrement = false,
}: {
  tables: PlanTable[];
  onEnregistrer: (placements: Placement[]) => Promise<void> | void;
  enregistrement?: boolean;
}) {
  const [brouillon, setBrouillon] = useState<PlanTable[]>(tables);
  const [selectionnee, setSelectionnee] = useState<number | null>(null);
  const [modifie, setModifie] = useState(false);

  // Les tables créées ou supprimées ailleurs dans l'écran doivent apparaître
  // ici sans écraser un placement en cours.
  const signature = tables.map((t) => t.id).join(",");
  const signatureBrouillon = brouillon.map((t) => t.id).join(",");
  if (signature !== signatureBrouillon && !modifie) {
    setBrouillon(tables);
  }

  const posees = useMemo(() => brouillon.filter((t) => t.pos_x !== null), [brouillon]);
  const enReserve = useMemo(() => brouillon.filter((t) => t.pos_x === null), [brouillon]);
  const tableSelectionnee = brouillon.find((t) => t.id === selectionnee) ?? null;

  // Enregistrement automatique. La référence évite de relancer le compte à
  // rebours quand seule l'identité de la fonction parente change.
  const enregistrerRef = useRef(onEnregistrer);
  enregistrerRef.current = onEnregistrer;

  useEffect(() => {
    if (!modifie) return;
    const t = setTimeout(async () => {
      await enregistrerRef.current(
        posees.map((t) => ({
          table_id: t.id,
          pos_x: t.pos_x as number,
          pos_y: t.pos_y as number,
          shape: t.shape,
          seats: t.seats,
        }))
      );
      setModifie(false);
    }, DELAI_ENREGISTREMENT);
    return () => clearTimeout(t);
  }, [modifie, posees]);

  function deplacer(tableId: number, x: number, y: number) {
    setBrouillon((prev) => prev.map((t) => (t.id === tableId ? { ...t, pos_x: x, pos_y: y } : t)));
    setModifie(true);
  }

  function poserSurLePlan(tableId: number) {
    // Posée au centre, décalée un peu à chaque fois pour que deux tables
    // successives ne se recouvrent pas exactement.
    const rang = posees.length;
    setBrouillon((prev) =>
      prev.map((t) =>
        t.id === tableId
          ? { ...t, pos_x: 40 + ((rang * 12) % 24), pos_y: 36 + ((rang * 16) % 28) }
          : t
      )
    );
    setSelectionnee(tableId);
    setModifie(true);
  }

  function retirerDuPlan(tableId: number) {
    setBrouillon((prev) =>
      prev.map((t) => (t.id === tableId ? { ...t, pos_x: null, pos_y: null } : t))
    );
    setSelectionnee(null);
    setModifie(true);
  }

  function changerCouverts(n: number) {
    if (selectionnee === null) return;
    setBrouillon((prev) =>
      prev.map((t) =>
        t.id === selectionnee
          ? // Au-delà de quatre couverts, une table ronde n'existe presque plus
            // en salle : on bascule sur la table longue, que le manager peut
            // toujours corriger juste en dessous.
            { ...t, seats: n, shape: n >= 6 ? "rect" : t.shape }
          : t
      )
    );
    setModifie(true);
  }

  function changerForme(forme: TableShape) {
    if (selectionnee === null) return;
    setBrouillon((prev) => prev.map((t) => (t.id === selectionnee ? { ...t, shape: forme } : t)));
    setModifie(true);
  }

  const etatEnregistrement = enregistrement
    ? "Enregistrement…"
    : modifie
      ? "Modifications en cours…"
      : posees.length > 0
        ? "Enregistré"
        : "";

  return (
    <div className="flex flex-col gap-4">
      <PlanDeSalle
        tables={brouillon}
        editable
        onDeplacer={deplacer}
        onTableActivee={(t) => setSelectionnee(t.id)}
        tableSelectionnee={selectionnee}
      />

      {tableSelectionnee ? (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-3 text-sm">
          <span className="font-medium mr-1">{tableSelectionnee.label}</span>
          <span className="text-neutral-500">couverts</span>
          {COUVERTS.map((n) => (
            <button
              key={n}
              onClick={() => changerCouverts(n)}
              className={`h-9 w-9 rounded-lg border ${
                tableSelectionnee.seats === n
                  ? "border-[var(--harissa)] text-[var(--harissa)] font-semibold"
                  : "border-[var(--line)] text-neutral-600"
              }`}
              aria-pressed={tableSelectionnee.seats === n}
            >
              {n}
            </button>
          ))}
          <span className="mx-1 h-5 w-px bg-[var(--line)]" aria-hidden="true" />
          {FORMES.map((f) => (
            <button
              key={f.valeur}
              onClick={() => changerForme(f.valeur)}
              className={`rounded-lg border px-3 py-1.5 ${
                tableSelectionnee.shape === f.valeur
                  ? "border-[var(--harissa)] text-[var(--harissa)]"
                  : "border-[var(--line)] text-neutral-600"
              }`}
              aria-pressed={tableSelectionnee.shape === f.valeur}
            >
              {f.nom}
            </button>
          ))}
          <button
            onClick={() => retirerDuPlan(tableSelectionnee.id)}
            className="text-neutral-500 underline ml-1"
          >
            Retirer du plan
          </button>
        </div>
      ) : (
        posees.length > 0 && (
          <p className="text-sm text-neutral-500">
            Touchez une table du plan pour changer son nombre de couverts ou sa forme.
          </p>
        )
      )}

      {enReserve.length > 0 && (
        <div>
          <p className="text-sm text-neutral-500 mb-2">
            Pas encore sur le plan — touchez une table pour la poser, puis faites-la glisser à sa
            place.
          </p>
          <div className="flex flex-wrap gap-2">
            {enReserve.map((t) => (
              <button
                key={t.id}
                onClick={() => poserSurLePlan(t.id)}
                className="rounded-lg border border-dashed border-[var(--line)] px-3 py-1.5 text-sm"
              >
                + {t.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {etatEnregistrement && (
        <p className="text-sm text-neutral-500" aria-live="polite">
          {etatEnregistrement}
        </p>
      )}
    </div>
  );
}
