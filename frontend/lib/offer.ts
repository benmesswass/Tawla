/**
 * Contenu de l'offre affiché sur la page d'accueil publique (Phase 14.2).
 *
 * Rassemblé ici plutôt que dispersé dans la page : ce sont des engagements
 * commerciaux, pas de la mise en page. Ils se relisent d'un coup d'œil avant
 * une mise en ligne.
 */

/**
 * Trois paliers d'abonnement (offre tranchée le 2026-08-18, remplace le prix
 * unique de la Phase 14.3/22). Chaque palier inclut tout ce qu'offre le
 * précédent — voir `app/core/subscription.py` côté backend pour le gating
 * réel derrière chaque fonctionnalité listée ici.
 *
 * Le palier vendu à un établissement se fixe dans le fichier de config de
 * `scripts/setup_restaurant.py` au moment de l'installation — il n'existe
 * pas de portail self-service tant que la facturation reste manuelle.
 */
export type OfferTier = {
  id: "essentiel" | "pro" | "business";
  name: string;
  priceDT: number;
  tagline: string;
  features: string[];
  recommended?: boolean;
};

export const TIERS: OfferTier[] = [
  {
    id: "essentiel",
    name: "Essentiel",
    priceDT: 50,
    tagline: "Pour un petit café, une seule salle",
    features: [
      "QR, menu et commande client",
      "Écrans serveur et cuisine en temps réel",
      "Appel serveur depuis la table",
      "Paiement en espèces",
      "Mode café simplifié",
      "Liste de tables simple",
      "Installation, QR imprimés et formation",
    ],
  },
  {
    id: "pro",
    name: "Pro",
    priceDT: 100,
    tagline: "Pour vendre plus et fidéliser vos clients",
    recommended: true,
    features: [
      "Tout Essentiel",
      "Paiement carte",
      "Programme de fidélité",
      "Vente incitative « avec ce plat »",
      "Plan de salle visuel, plusieurs zones",
      "Photos des plats, mode Ramadan",
      "Import CSV du menu",
      "Page de preuve complète",
    ],
  },
  {
    id: "business",
    name: "Business",
    priceDT: 150,
    tagline: "Pour une équipe, plusieurs adresses",
    features: [
      "Tout Pro",
      "Rapport d'équipe et primes par serveur",
      "Multi-établissements (construit pour vous à la demande)",
      "Notifications push à vos clients",
      "Support prioritaire",
    ],
  },
];

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
