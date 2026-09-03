/**
 * Contenu de l'offre affiché sur la page d'accueil publique (Phase 14.2).
 *
 * Rassemblé ici plutôt que dispersé dans la page : ce sont des engagements
 * commerciaux, pas de la mise en page. Ils se relisent d'un coup d'œil avant
 * une mise en ligne.
 *
 * `priceDT` vient de `currentMarket.tierPrices` (France, MARCHE_FRANCE.md
 * Phase F3) — plus jamais un deuxième 50/100/150 en dur ici, qui pourrait
 * diverger de la valeur réellement facturée côté serveur
 * (`core/subscription.py::tier_price`). `name`/`tagline`/`features` restent
 * la copie tunisienne telle quelle, sauf la ligne mode Ramadan (gérée via
 * `currentMarket.ramadanModeAvailable`, sans objet en France) : le reste des
 * contenus par marché (démo, visite guidée, catégories, chevalet QR) est un
 * chantier séparé, pas encore fait.
 */
import { currentMarket } from "./market";

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

// Identité visuelle par palier (dashboard manager, 2026-09-02) — les trois
// accents du système déjà réservés aux tuiles de catégorie
// (`--tuile-*-fond`/`-bord`, globals.css), jamais une quatrième couleur
// inventée. Essentiel reste neutre (premier palier, rien à mettre en avant) ;
// Pro/Business montent en couleur pour donner envie de scroller vers le
// palier suivant plutôt que de contacter Tawla (retour utilisateur,
// 2026-09-02).
export const TIER_ACCENTS: Record<OfferTier["id"], { fond: string; bord: string; texte: string }> = {
  essentiel: { fond: "var(--creme)", bord: "var(--line-strong)", texte: "var(--encre)" },
  pro: { fond: "var(--tuile-laiton-fond)", bord: "var(--tuile-laiton-bord)", texte: "var(--laiton)" },
  business: { fond: "var(--tuile-harissa-fond)", bord: "var(--tuile-harissa-bord)", texte: "var(--harissa)" },
};

/**
 * Estime le prorata payé pour un upgrade EN COURS D'ABONNEMENT — jamais pour
 * un tout premier abonnement (`stripe_subscription_active` faux), qui paie
 * le plein tarif via une nouvelle session de paiement, pas ce mécanisme
 * (voir change_tier_immediately côté backend). Approximatif (mois
 * calendaire réel de 28 à 31 jours ; Stripe facture au jour et à la seconde
 * près), mais assez précis pour rassurer avant de cliquer — retour
 * utilisateur, 2026-09-02 : "c'est bien pour vendre", montrer que l'upgrade
 * ne coûte presque rien en fin de mois plutôt que de laisser deviner.
 */
export function estimateUpgradeProration(
  currentPriceDT: number,
  targetPriceDT: number,
  periodEndIso: string,
): number | null {
  const daysRemaining = (new Date(periodEndIso).getTime() - Date.now()) / (1000 * 60 * 60 * 24);
  if (daysRemaining <= 0) return null;
  return Math.round(((targetPriceDT - currentPriceDT) * Math.min(daysRemaining, 30)) / 30);
}

export const TIERS: OfferTier[] = [
  {
    id: "essentiel",
    name: "Essentiel",
    priceDT: currentMarket.tierPrices.essentiel,
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
    priceDT: currentMarket.tierPrices.pro,
    tagline: "Pour vendre plus et fidéliser vos clients",
    recommended: true,
    features: [
      "Tout Essentiel",
      "Paiement carte",
      "Programme de fidélité",
      "Vente incitative « avec ce plat »",
      "Plan de salle visuel, plusieurs zones",
      "Photos des plats",
      ...(currentMarket.ramadanModeAvailable ? ["Mode Ramadan"] : []),
      "Import CSV du menu",
      "Page de preuve complète",
    ],
  },
  {
    id: "business",
    name: "Business",
    priceDT: currentMarket.tierPrices.business,
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
 * fonctionnalité — présenté en problème/solution sur la home (Phase D2bis de
 * ROADMAP_DESIGN.md, comparatif BipOrder). `probleme` est la douleur telle
 * qu'un patron la formulerait, `detail` reste la solution telle quelle.
 *
 * Chaque `detail` est vérifié contre le code réel (2026-09-03), pas juste
 * plausible : les deux premiers correspondent à `OrderStatus`/
 * `ALLOWED_TRANSITIONS` (orders/service.py — la cuisine ne reçoit le
 * broadcast `channel="kitchen"` que sur la transition SENT_TO_KITCHEN,
 * jamais avant). Le troisième a été réécrit : la version précédente listait
 * "commandes perdues" et "panier moyen" comme visibles au même endroit que
 * l'activité par serveur, alors que ce sont deux écrans distincts
 * (`/dashboard` en direct vs `/dashboard/preuve`, un outil de preuve pour un
 * pilote/jury) — voir RecetteDuJour.tsx et stats/schemas.py.
 */
export const BENEFITS = [
  {
    probleme: "Les commandes se perdent à l'oral — un plat mal entendu, une table oubliée.",
    detail: "La commande arrive sur l'écran partagé des serveurs, confirmée avant de partir en cuisine.",
  },
  {
    probleme: "D'autres systèmes envoient tout direct en cuisine, sans repasser par la salle.",
    detail: "Rien n'entre en cuisine sans qu'un serveur l'ait vérifiée à table.",
  },
  {
    probleme: "Aucune visibilité sur ce qui se passe vraiment en salle chaque soir.",
    detail:
      "Ventes et temps d'attente moyen dès la connexion, détail par serveur et comparaison avant/après en un clic.",
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
