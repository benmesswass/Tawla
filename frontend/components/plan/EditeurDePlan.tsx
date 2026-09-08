"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api, LandmarkKind, LandmarkPart, PlanLandmark, PlanTable, TableShape } from "@/lib/api";
import { tronconSuivant, tronconVise } from "@/lib/formeRepere";
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

/** Temps de calme après le dernier geste avant d'écrire. */
const DELAI_ENREGISTREMENT = 1000;

/** Rectangle de départ d'un repère fraîchement posé — un petit comptoir,
 *  pas encore le mur qu'il pourra devenir une fois étiré. */
const LARGEUR_REPERE_DEFAUT = 12;
const HAUTEUR_REPERE_DEFAUT = 7;

/** Longueur du bras que « Prolonger en angle » fait naître — assez visible
 *  pour être attrapé tout de suite, assez court pour ne pas traverser la
 *  salle avant que le manager ne l'ait étiré. */
const LONGUEUR_TRONCON_DEFAUT = 16;

/** Bornes du rectangle, en % de la surface — mêmes valeurs que côté serveur
 *  (schemas.py) : large pour courir tout un mur, jamais assez pour avaler la
 *  salle entière ni disparaître en un point. */
const TAILLE_REPERE_MIN = 2;
const TAILLE_REPERE_MAX = 90;

/** Un tronçon droit, un L, un U, un comptoir qui suit trois murs — même borne
 *  que côté serveur. Au-delà on dessine un logiciel d'architecture, pas un
 *  outil de service. */
const TRONCONS_MAX = 4;

function borneTailleRepere(valeur: number): number {
  return Math.min(TAILLE_REPERE_MAX, Math.max(TAILLE_REPERE_MIN, valeur));
}

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
  // Quel tronçon du repère le dernier appui a visé : celui que la poignée
  // étire, celui que « Prolonger en angle » coude. Un repère droit n'en a
  // qu'un, et le manager n'a alors rien de plus à comprendre qu'avant.
  const [tronconSelectionne, setTronconSelectionne] = useState<number | null>(null);
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
        await api.shapeLandmark(restaurantId, repere.id, repere.parts);
      } catch (e) {
        onErreurRef.current?.(e);
      }
    }, DELAI_ENREGISTREMENT);
    return () => clearTimeout(t);
  }, [repereModifie, landmarks, restaurantId]);

  /** Retoucher un seul tronçon du repère, en laissant les autres tels quels —
   *  l'écriture, elle, part toujours avec la forme entière (shapeLandmark). */
  function retoucherTroncon(id: number, troncon: number, retouche: (t: LandmarkPart) => LandmarkPart) {
    derniereRepereDeplaceeRef.current = id;
    setLandmarks((prev) =>
      prev.map((r) =>
        r.id === id ? { ...r, parts: r.parts.map((t, i) => (i === troncon ? retouche(t) : t)) } : r
      )
    );
    setRepereModifie(true);
  }

  function deplacerRepere(id: number, troncon: number, x: number, y: number) {
    retoucherTroncon(id, troncon, (t) => ({ ...t, pos_x: x, pos_y: y }));
  }

  /** Glisser la poignée du coin : le coin haut-gauche ne bouge pas, seules la
   *  largeur/hauteur suivent le pointeur — recalculées à chaque mouvement,
   *  jamais un delta cumulé (même politique que positionDepuisEvenement). */
  function redimensionnerRepere(id: number, troncon: number, largeur: number, hauteur: number) {
    retoucherTroncon(id, troncon, (t) => ({
      ...t,
      width: borneTailleRepere(largeur),
      height: borneTailleRepere(hauteur),
    }));
  }

  /** Couder le comptoir : un bras perpendiculaire naît au bout libre du
   *  tronçon actif et se replie vers le reste (voir `tronconSuivant`). Un clic
   *  donne un L, deux donnent un U — le manager le glisse et l'étire ensuite,
   *  il n'a jamais à choisir une orientation dans une liste. */
  function prolongerRepere(id: number, troncon: number) {
    const repere = landmarks.find((r) => r.id === id);
    if (!repere || repere.parts.length >= TRONCONS_MAX) return;
    const bras = tronconSuivant(repere.parts, troncon, {
      longueur: LONGUEUR_TRONCON_DEFAUT,
      min: TAILLE_REPERE_MIN,
      max: TAILLE_REPERE_MAX,
    });
    derniereRepereDeplaceeRef.current = id;
    setLandmarks((prev) =>
      prev.map((r) => (r.id === id ? { ...r, parts: [...r.parts, bras] } : r))
    );
    setTronconSelectionne(repere.parts.length);
    setRepereModifie(true);
  }

  /** Retirer un tronçon, pas le repère : défaire un coude de trop ne doit pas
   *  obliger à reposer le bar. Le dernier tronçon ne part pas — un repère sans
   *  forme n'est pas un repère, c'est « Retirer ce repère ». */
  function retirerTroncon(id: number, troncon: number) {
    const repere = landmarks.find((r) => r.id === id);
    if (!repere || repere.parts.length <= 1) return;
    derniereRepereDeplaceeRef.current = id;
    setLandmarks((prev) =>
      prev.map((r) => (r.id === id ? { ...r, parts: r.parts.filter((_, i) => i !== troncon) } : r))
    );
    setTronconSelectionne(null);
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
        14 + ((rang * 10) % 8),
        LARGEUR_REPERE_DEFAUT,
        HAUTEUR_REPERE_DEFAUT
      );
      setLandmarks((prev) => [...prev, repere]);
      setRepereSelectionne(repere.id);
      setTronconSelectionne(0);
      setSelectionnee(null);
    } catch (e) {
      onErreurRef.current?.(e);
    }
  }

  async function retirerRepere(id: number) {
    if (!restaurantId) return;
    setLandmarks((prev) => prev.filter((r) => r.id !== id));
    setRepereSelectionne(null);
    setTronconSelectionne(null);
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
  // Même résolution que la poignée dans PieceRepere : les boutons ci-dessous
  // doivent couder et retirer le tronçon que le manager voit sélectionné.
  const tronconActif = repereSelectionneObjet
    ? tronconVise(repereSelectionneObjet.parts, tronconSelectionne)
    : 0;

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
        onRedimensionnerRepere={redimensionnerRepere}
        onRepereActive={(r, troncon) => {
          // Toucher un autre tronçon du même repère change de tronçon actif ;
          // c'est le second appui sur le *même* qui désélectionne, sinon
          // façonner un U demanderait de re-sélectionner à chaque coude.
          const memeTroncon = repereSelectionne === r.id && tronconSelectionne === troncon;
          setRepereSelectionne(memeTroncon ? null : r.id);
          setTronconSelectionne(memeTroncon ? null : troncon);
          setSelectionnee(null);
        }}
        repereSelectionne={repereSelectionne}
        tronconSelectionne={tronconSelectionne}
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
          <span className="text-neutral-500">
            Faites glisser le point en bas à droite pour étirer ce tronçon.
          </span>
          <button
            onClick={() => prolongerRepere(repereSelectionneObjet.id, tronconActif)}
            disabled={repereSelectionneObjet.parts.length >= TRONCONS_MAX}
            className="rounded-lg border border-dashed border-[var(--line)] px-3 py-1.5 disabled:opacity-40"
          >
            Prolonger en angle
          </button>
          {repereSelectionneObjet.parts.length > 1 && (
            <button
              onClick={() => retirerTroncon(repereSelectionneObjet.id, tronconActif)}
              className="text-neutral-500 underline ml-1"
            >
              Retirer ce tronçon
            </button>
          )}
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
