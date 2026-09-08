"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api, LandmarkKind, LandmarkSize, PlanLandmark, PlanTable, TableShape } from "@/lib/api";
import PlanDeSalle from "./PlanDeSalle";
import { LIBELLE_REPERE } from "./types";

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

const TAILLES: { valeur: LandmarkSize; nom: string }[] = [
  { valeur: "small", nom: "Petit" },
  { valeur: "medium", nom: "Moyen" },
  { valeur: "large", nom: "Grand" },
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
  restaurantId,
  onEnregistrer,
  enregistrement = false,
  onErreur,
}: {
  tables: PlanTable[];
  /** Pour poser/déplacer/retirer les repères (bar, entrée) — gérés en direct
   *  par cet éditeur, indépendamment du brouillon de tables du parent. */
  restaurantId: number | null;
  onEnregistrer: (placements: Placement[]) => Promise<void> | void;
  enregistrement?: boolean;
  /** Ex: handleGatedError du parent — un palier insuffisant doit ouvrir la
   *  même incitation que partout ailleurs, pas un bandeau différent. */
  onErreur?: (e: unknown) => void;
}) {
  const [brouillon, setBrouillon] = useState<PlanTable[]>(tables);
  const [selectionnee, setSelectionnee] = useState<number | null>(null);
  const [modifie, setModifie] = useState(false);

  const [landmarks, setLandmarks] = useState<PlanLandmark[]>([]);
  const [repereSelectionne, setRepereSelectionne] = useState<number | null>(null);
  const [repereModifie, setRepereModifie] = useState(false);
  const derniereRepereDeplaceeRef = useRef<number | null>(null);

  const onErreurRef = useRef(onErreur);
  onErreurRef.current = onErreur;

  useEffect(() => {
    if (!restaurantId) return;
    api.listLandmarks(restaurantId).then(setLandmarks).catch((e) => onErreurRef.current?.(e));
  }, [restaurantId]);

  // Même politique que les tables : le geste (glisser) est immédiat, l'écriture
  // réseau attend une seconde de calme — sans ça, chaque pixel de glissement
  // produirait son propre PUT.
  useEffect(() => {
    if (!repereModifie || !restaurantId) return;
    const t = setTimeout(async () => {
      setRepereModifie(false);
      const repere = landmarks.find((r) => r.id === derniereRepereDeplaceeRef.current);
      if (!repere) return;
      try {
        await api.moveLandmark(restaurantId, repere.id, repere.pos_x, repere.pos_y, repere.size);
      } catch (e) {
        onErreurRef.current?.(e);
      }
    }, DELAI_ENREGISTREMENT);
    return () => clearTimeout(t);
  }, [repereModifie, landmarks, restaurantId]);

  function deplacerRepere(id: number, x: number, y: number) {
    derniereRepereDeplaceeRef.current = id;
    setLandmarks((prev) => prev.map((r) => (r.id === id ? { ...r, pos_x: x, pos_y: y } : r)));
    setRepereModifie(true);
  }

  function changerTailleRepere(taille: LandmarkSize) {
    if (repereSelectionne === null) return;
    derniereRepereDeplaceeRef.current = repereSelectionne;
    setLandmarks((prev) => prev.map((r) => (r.id === repereSelectionne ? { ...r, size: taille } : r)));
    setRepereModifie(true);
  }

  async function ajouterRepere(kind: LandmarkKind) {
    if (!restaurantId) return;
    // Décalé à chaque ajout, comme une table qui sort de réserve : deux
    // repères posés coup sur coup ne doivent pas atterrir l'un sur l'autre.
    const rang = landmarks.length;
    try {
      const repere = await api.createLandmark(
        restaurantId,
        kind,
        40 + ((rang * 12) % 24),
        14 + ((rang * 10) % 8)
      );
      setLandmarks((prev) => [...prev, repere]);
      setRepereSelectionne(repere.id);
      setSelectionnee(null);
    } catch (e) {
      onErreurRef.current?.(e);
    }
  }

  async function retirerRepere(id: number) {
    if (!restaurantId) return;
    setLandmarks((prev) => prev.filter((r) => r.id !== id));
    setRepereSelectionne(null);
    try {
      await api.deleteLandmark(restaurantId, id);
    } catch (e) {
      onErreurRef.current?.(e);
      // L'optimisme ci-dessus était faux (ex: palier insuffisant) — se
      // resynchroniser sur l'état serveur plutôt que garder un repère
      // affiché disparu à tort, ou l'inverse.
      api.listLandmarks(restaurantId).then(setLandmarks).catch(() => {});
    }
  }

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
  const repereSelectionneObjet = landmarks.find((r) => r.id === repereSelectionne) ?? null;

  // Enregistrement automatique. La référence évite de relancer le compte à
  // rebours quand seule l'identité de la fonction parente change.
  const enregistrerRef = useRef(onEnregistrer);
  enregistrerRef.current = onEnregistrer;

  useEffect(() => {
    if (!modifie) return;
    const t = setTimeout(async () => {
      try {
        await enregistrerRef.current(
          posees.map((t) => ({
            table_id: t.id,
            pos_x: t.pos_x as number,
            pos_y: t.pos_y as number,
            shape: t.shape,
            seats: t.seats,
          }))
        );
      } catch {
        // Le parent a déjà affiché l'erreur (ex: palier insuffisant) — ici on
        // revient au dernier état confirmé par le serveur, sinon le brouillon
        // garderait la table affichée posée sur le plan alors que rien n'a
        // été enregistré.
        setBrouillon(tables);
      }
      setModifie(false);
    }, DELAI_ENREGISTREMENT);
    return () => clearTimeout(t);
  }, [modifie, posees, tables]);

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
        landmarks={landmarks}
        editable
        onDeplacer={deplacer}
        onTableActivee={(t) => {
          setSelectionnee(t.id);
          setRepereSelectionne(null);
        }}
        tableSelectionnee={selectionnee}
        onDeplacerRepere={deplacerRepere}
        onRepereActive={(r) => {
          setRepereSelectionne((actuel) => (actuel === r.id ? null : r.id));
          setSelectionnee(null);
        }}
        repereSelectionne={repereSelectionne}
      />

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-neutral-500">Repères</span>
        <button
          type="button"
          onClick={() => ajouterRepere("bar")}
          className="rounded-lg border border-dashed border-[var(--line)] px-3 py-1.5"
        >
          + Bar
        </button>
        <button
          type="button"
          onClick={() => ajouterRepere("entrance")}
          className="rounded-lg border border-dashed border-[var(--line)] px-3 py-1.5"
        >
          + Porte d&apos;entrée
        </button>
      </div>

      {repereSelectionneObjet && (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-3 text-sm">
          <span className="font-medium mr-1">{LIBELLE_REPERE[repereSelectionneObjet.kind]}</span>
          <span className="text-neutral-500">taille</span>
          {TAILLES.map((t) => (
            <button
              key={t.valeur}
              onClick={() => changerTailleRepere(t.valeur)}
              className={`rounded-lg border px-3 py-1.5 ${
                repereSelectionneObjet.size === t.valeur
                  ? "border-[var(--harissa)] text-[var(--harissa)]"
                  : "border-[var(--line)] text-neutral-600"
              }`}
              aria-pressed={repereSelectionneObjet.size === t.valeur}
            >
              {t.nom}
            </button>
          ))}
          <button
            onClick={() => retirerRepere(repereSelectionneObjet.id)}
            className="text-neutral-500 underline ml-1"
          >
            Retirer ce repère
          </button>
        </div>
      )}

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
