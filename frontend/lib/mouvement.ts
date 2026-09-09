/**
 * Les jetons de mouvement, côté JavaScript.
 *
 * Même source de vérité que les variables CSS de `globals.css` — les valeurs
 * sont dupliquées ici parce que Motion attend des secondes et des tableaux de
 * points de Bézier, pas des chaînes CSS. Toute modification se fait des deux
 * côtés, sinon une animation CSS et une animation Motion sur le même geste
 * partent en désaccord de quelques dizaines de millisecondes — ce qui se voit.
 *
 * Le catalogue est volontairement court. Les sept principes de
 * `MOTION_DESIGN.md` tiennent avec ça ; une transition qui n'y trouve pas son
 * compte est probablement une animation qui n'a pas de rôle.
 */

/** Durées en secondes (l'unité de Motion). Le pendant CSS est en ms. */
export const DUREE = {
  micro: 0.12,
  rapide: 0.18,
  normal: 0.28,
  lent: 0.4,
  sortie: 0.2,
} as const;

/** Courbes de `globals.css`, en points de Bézier. */
export const COURBE = {
  entree: [0.32, 0.72, 0, 1],
  sortie: [0.4, 0, 1, 1],
  deplacement: [0.4, 0, 0.2, 1],
} as const;

/**
 * Ressorts. Ils n'existent que côté JS, et `MOTION_DESIGN.md` en restreint
 * l'usage : le rebond n'appartient qu'à ce que le doigt tient, ou à un élément
 * qui atterrit à une nouvelle place. Trois rôles, pas trois adjectifs — un
 * ressort nommé « bouncy » finit posé partout.
 *
 * `visualDuration` plutôt que `stiffness`/`damping` : c'est la durée réellement
 * perçue jusqu'à la cible, donc la seule qu'on puisse accorder aux durées
 * ci-dessus.
 */
export const RESSORT = {
  /** Ce que le doigt tient : glisser une table sur le plan, le carrousel. */
  prise: { type: "spring", visualDuration: 0.22, bounce: 0.18 },
  /** Un élément qui atterrit ailleurs : animation de layout, réordonnancement. */
  depot: { type: "spring", visualDuration: 0.32, bounce: 0.12 },
  /** Une valeur qui s'impose : compteur du panier, pastille de quantité. */
  saillie: { type: "spring", visualDuration: 0.26, bounce: 0.3 },
} as const;

/**
 * Transitions prêtes à l'emploi, à passer directement en `transition`.
 * `entree`/`sortie` vont par paire : la sortie est toujours la plus courte.
 */
export const TRANSITION = {
  entree: { duration: DUREE.normal, ease: COURBE.entree },
  sortie: { duration: DUREE.sortie, ease: COURBE.sortie },
  deplacement: { duration: DUREE.rapide, ease: COURBE.deplacement },
  pression: { duration: DUREE.micro, ease: COURBE.deplacement },
} as const;

/**
 * Variants d'une couche qui monte (feuille sur téléphone, modale sur écran
 * large) — principe 1 de `MOTION_DESIGN.md`. Le recul de la page en dessous
 * est porté par la page elle-même, pas par la couche.
 */
export const COUCHE = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0, transition: TRANSITION.entree },
  exit: { opacity: 0, y: 16, transition: TRANSITION.sortie },
} as const;

/** Le voile derrière une couche. Pas de déplacement, juste une opacité. */
export const VOILE = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: DUREE.normal } },
  exit: { opacity: 0, transition: { duration: DUREE.sortie } },
} as const;
