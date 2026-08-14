"use client";

import { useMemo, useState } from "react";
import { PlanTable, TableShape } from "@/lib/api";
import PlanDeSalle from "./PlanDeSalle";
import Button from "@/components/ui/Button";

/**
 * Le manager dessine sa salle (Phase 18).
 *
 * Une table nouvellement créée n'apparaît pas sur le plan : elle attend dans
 * la réserve, en dessous. Les poser d'office empilerait toute la salle dans un
 * coin, et le manager devrait défaire avant de faire.
 *
 * Rien n'est enregistré tant qu'il n'a pas validé : déplacer six tables est
 * une seule intention, pas six.
 */

const FORMES: { valeur: TableShape; nom: string }[] = [
  { valeur: "round", nom: "Ronde" },
  { valeur: "square", nom: "Carrée" },
  { valeur: "rect", nom: "Rectangulaire" },
];

export default function EditeurDePlan({
  tables,
  onEnregistrer,
  enregistrement = false,
}: {
  tables: PlanTable[];
  onEnregistrer: (
    placements: { table_id: number; pos_x: number; pos_y: number; shape: TableShape }[]
  ) => Promise<void> | void;
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

  function deplacer(tableId: number, x: number, y: number) {
    setBrouillon((prev) =>
      prev.map((t) => (t.id === tableId ? { ...t, pos_x: x, pos_y: y } : t))
    );
    setModifie(true);
  }

  function poserSurLePlan(tableId: number) {
    // Posée au centre, décalée un peu à chaque fois pour que deux tables
    // successives ne se recouvrent pas exactement.
    const rang = posees.length;
    setBrouillon((prev) =>
      prev.map((t) =>
        t.id === tableId
          ? { ...t, pos_x: 40 + ((rang * 13) % 30), pos_y: 35 + ((rang * 17) % 30) }
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

  function changerForme(forme: TableShape) {
    if (selectionnee === null) return;
    setBrouillon((prev) => prev.map((t) => (t.id === selectionnee ? { ...t, shape: forme } : t)));
    setModifie(true);
  }

  async function enregistrer() {
    await onEnregistrer(
      posees.map((t) => ({
        table_id: t.id,
        pos_x: t.pos_x as number,
        pos_y: t.pos_y as number,
        shape: t.shape,
      }))
    );
    setModifie(false);
  }

  return (
    <div className="flex flex-col gap-4">
      <PlanDeSalle
        tables={brouillon}
        editable
        onDeplacer={deplacer}
        onTableActivee={(t) => setSelectionnee(t.id)}
        tableSelectionnee={selectionnee}
      />

      {tableSelectionnee && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-medium">{tableSelectionnee.label}</span>
          {FORMES.map((f) => (
            <button
              key={f.valeur}
              onClick={() => changerForme(f.valeur)}
              className={`rounded-lg border px-3 py-1 ${
                tableSelectionnee.shape === f.valeur
                  ? "border-[var(--harissa)] text-[var(--harissa)]"
                  : "border-[var(--line)] text-neutral-600"
              }`}
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

      <div className="flex items-center gap-3">
        <Button onClick={enregistrer} disabled={!modifie || enregistrement}>
          {enregistrement ? "Enregistrement..." : "Enregistrer le plan"}
        </Button>
        {modifie && <span className="text-sm text-neutral-500">Modifications non enregistrées</span>}
      </div>
    </div>
  );
}
