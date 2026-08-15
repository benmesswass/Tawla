"use client";

import { useEffect, useState } from "react";

/**
 * Une durée telle qu'on la dit à voix haute en salle : « une minute trente »,
 * jamais « 1,5 minute ».
 *
 * Un chiffre décimal oblige le lecteur à faire la conversion de tête, et
 * personne ne la fait sur un écran de service — « 1,7 min » se lit « une
 * minute et quelque » et se range dans la catégorie « à peu près rien », alors
 * que c'est 1min42. Les secondes sont sur deux chiffres pour que deux durées
 * s'alignent l'une sous l'autre dans un tableau.
 *
 * Au-delà de l'heure les secondes n'apprennent plus rien : on passe aux heures
 * et minutes.
 */
export function duree(secondes: number | null): string {
  if (secondes === null || Number.isNaN(secondes)) return "—";
  const s = Math.max(0, Math.round(secondes));
  if (s < 60) return `${s} s`;
  const minutes = Math.floor(s / 60);
  if (minutes < 60) return `${minutes}min${String(s % 60).padStart(2, "0")}`;
  return `${Math.floor(minutes / 60)} h ${String(minutes % 60).padStart(2, "0")}`;
}

/**
 * Secondes écoulées depuis un horodatage ISO, ou `null` s'il n'y en a pas.
 *
 * `now` est passé en argument plutôt que lu ici : les écrans de service
 * rafraîchissent un seul compteur commun, sinon chaque carte recalculerait
 * l'heure de son côté et deux commandes arrivées ensemble afficheraient des
 * durées différentes.
 */
export function elapsedSeconds(iso: string | null, now: number): number | null {
  if (!iso) return null;
  return Math.max(0, (now - new Date(iso).getTime()) / 1000);
}

/**
 * Horloge partagée d'un écran, réévaluée toutes les 30 secondes — assez fin
 * pour un service, assez lâche pour ne pas réveiller le téléphone du client
 * en permanence.
 */
export function useHorloge(intervalMs = 30_000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(tick);
  }, [intervalMs]);
  return now;
}
