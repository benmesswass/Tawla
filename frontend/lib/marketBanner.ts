/**
 * Verrou de la règle qui prime sur tout le reste de la Phase F4
 * (MARCHE_FRANCE.md §5) : « le parcours client ne passe JAMAIS par le
 * sélecteur ». Extrait en fonction pure, testable, plutôt qu'inline dans le
 * composant — c'est le point que la spec demande explicitement de
 * verrouiller par un test automatisé, pas juste par une relecture.
 *
 * Même exclusion que `components/visite/BandeauDemo.tsx` (précédent établi
 * dans ce dépôt pour « jamais sur l'écran d'un convive attablé »).
 *
 * Exclut aussi `/choisir-pays` lui-même : trouvé pendant la vérification
 * visuelle de l'étape 3 (capture à l'appui) — le bandeau qui suggère
 * l'autre marché n'a rien à faire par-dessus la page qui propose déjà
 * exactement ce choix, plus clairement.
 */
export function selecteurAutorise(pathname: string): boolean {
  if (pathname === "/menu" || pathname.startsWith("/menu/")) return false;
  if (pathname === "/choisir-pays") return false;
  return true;
}
