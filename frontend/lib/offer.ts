/**
 * Contenu de l'offre affiché sur la page d'accueil publique (Phase 14.2).
 *
 * Rassemblé ici plutôt que dispersé dans la page : ce sont des engagements
 * commerciaux, pas de la mise en page. Ils se relisent d'un coup d'œil avant
 * une mise en ligne.
 */

/**
 * Prix mensuel affiché publiquement, en dinars.
 *
 * `null` tant que Wassim ne l'a pas tranché (ROADMAP Phase 14.3) : la page
 * affiche alors « tarif communiqué au premier rendez-vous » plutôt qu'un
 * montant. La revue d'investissement du 2026-08-13 propose 120 DT avec le
 * service inclus — c'est une proposition, pas une décision, et publier un prix
 * non validé engagerait l'entreprise sur un montant que personne n'a arrêté.
 */
export const PRICE_MONTHLY_DT: number | null = null;

/**
 * Ce qui est inclus dans l'abonnement. C'est le cœur du positionnement retenu :
 * un éditeur en libre-service à 19 DT ne se déplacera jamais, et c'est
 * exactement là que se joue l'écart de prix.
 */
export const INCLUDED = [
  {
    title: "Votre carte saisie pour vous",
    detail:
      "Vous envoyez votre carte telle que vous l'avez — un fichier, une photo, un vieux menu. Elle est en ligne avant votre arrivée.",
  },
  {
    title: "Les QR imprimés et livrés",
    detail:
      "Un chevalet par table, prêt à poser, avec le nom de votre établissement. Vous n'avez rien à imprimer.",
  },
  {
    title: "L'équipe formée sur place",
    detail:
      "Dix minutes pendant un service creux, avec vos serveurs et vos téléphones. Pas une visioconférence.",
  },
  {
    title: "Joignable pendant le service",
    detail:
      "Un numéro direct, y compris le vendredi soir. Le carnet papier reste sur le comptoir : on ne vous retire jamais le filet.",
  },
];

/**
 * Ce que le produit fait, dit du point de vue du restaurateur et non de la
 * fonctionnalité.
 */
export const BENEFITS = [
  {
    title: "Plus une commande oubliée",
    detail:
      "La commande du client arrive sur l'écran partagé de vos serveurs. Un serveur la prend en charge, la confirme à table, et elle part en cuisine. Rien ne se perd entre les deux.",
  },
  {
    title: "Votre serveur garde la main",
    detail:
      "Rien n'entre en cuisine sans qu'un serveur l'ait vérifié à table. Le client commande depuis son téléphone, votre équipe reste maîtresse du service.",
  },
  {
    title: "Vous voyez enfin vos chiffres",
    detail:
      "Commandes perdues, délai entre la commande et la cuisine, panier moyen, activité par serveur. De quoi décider d'une prime sur des chiffres plutôt que sur une impression.",
  },
];

/**
 * Résultats de pilotes, à citer sur la page.
 *
 * Vide, et à ne remplir qu'avec des chiffres réellement relevés sur
 * `/dashboard/preuve` chez un établissement qui a donné son accord écrit pour
 * être cité (ROADMAP Phase 13.4). Inventer un résultat ou un témoignage
 * ruinerait la seule chose que cette page a à vendre.
 */
export const PILOT_RESULTS: { establishment: string; metric: string; value: string }[] = [];
