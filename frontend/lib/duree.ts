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
