/**
 * Verrou de la règle qui prime sur tout le reste de la Phase F4
 * (MARCHE_FRANCE.md §5) : « le parcours client ne passe JAMAIS par le
 * sélecteur ». Extrait en fonction pure, testable, plutôt qu'inline dans le
 * composant — c'est le point que la spec demande explicitement de
 * verrouiller par un test automatisé, pas juste par une relecture.
 *
 * Même exclusion que `components/visite/BandeauDemo.tsx` (précédent établi
 * dans ce dépôt pour « jamais sur l'écran d'un convive attablé »).
 */
export function selecteurAutorise(pathname: string): boolean {
  return !(pathname === "/menu" || pathname.startsWith("/menu/"));
}
