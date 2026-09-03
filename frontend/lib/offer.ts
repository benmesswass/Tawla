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
 * Ce que le produit fait, un triptyque problème/solution par écran plutôt
 * qu'une liste générique (Phase D2bis de ROADMAP_DESIGN.md, test demandé par
 * Wassim le 2026-09-03 : fondre les bénéfices dans la vitrine à 4 écrans de
 * `components/home/ApercuProduit.tsx` au lieu d'un bloc séparé au-dessus).
 * Voix impersonnelle, toujours au même registre que les trois premiers
 * couples déjà validés — jamais "vos clients"/"vos serveurs".
 *
 * Chaque `solution` est vérifiée contre le code réel (2026-09-03), pas juste
 * plausible :
 * - client : suivi en direct (orders/service.py::transition_status,
 *   broadcast sur le channel de la commande) et appel serveur (module
 *   `waiter_calls`, déjà vendu comme fonctionnalité Essentiel dans `TIERS`
 *   ci-dessus).
 * - manager : mêmes deux chiffres de tête que RecetteDuJour.tsx, la charge
 *   par serveur de `StaffActiveLoad` (stats/schemas.py — décision de Wassim
 *   du 2026-08-28, remplace "commandes perdues" en tête), et
 *   `TeamReport`/`StaffPeriodReport` pour le rapport de prime.
 * - serveur : le pool partagé (`claim_order`) et le halo rouge des lignes en
 *   retard (`app/staff/page.tsx`, variable `tardive`), l'alerte "prête"
 *   (broadcast `order.ready` sur le channel "staff").
 * - cuisine : le minuteur et le rouge au-delà du délai d'alerte
 *   (`app/kitchen/page.tsx`, `ELAPSED_ALERT_MINUTES`), les options/notes en
 *   évidence (`--note-cuisine`).
 */
export const BENEFITS_PAR_ROLE: Record<"client" | "manager" | "serveur" | "cuisine", { probleme: string; solution: string }[]> = {
  client: [
    {
      probleme: "Le client attend qu'un serveur soit libre pour passer commande.",
      solution: "Il commande depuis son téléphone dès qu'il est prêt.",
    },
    {
      probleme: "Une fois la commande envoyée, aucune idée de son avancement.",
      solution: "Suivi en direct sur son téléphone, jusqu'à « prête ».",
    },
    {
      probleme: "Il faut héler un serveur à travers la salle pour un besoin simple.",
      solution: "Bouton d'appel serveur direct, depuis la table.",
    },
  ],
  manager: [
    {
      probleme: "Aucune visibilité sur ce qui se passe vraiment en salle chaque soir.",
      solution: "Ventes et temps d'attente moyen dès la connexion.",
    },
    {
      probleme: "Impossible de savoir qui, dans l'équipe, est débordé en plein service.",
      solution: "Charge en temps réel par serveur, là, maintenant.",
    },
    {
      probleme: "Décider d'une prime au feeling, faute de chiffres.",
      solution: "Rapport d'équipe par période : commandes, pourboires, montant traité.",
    },
  ],
  serveur: [
    {
      probleme: "Courir après chaque table pour savoir qui a commandé quoi.",
      solution: "Toutes les commandes en attente sur un seul écran, prises en charge en un clic.",
    },
    {
      probleme: "Une commande oubliée en pleine salle, sans que personne ne le voie.",
      solution: "La ligne se teinte de rouge si elle attend trop longtemps.",
    },
    {
      probleme: "Ne pas savoir quand aller chercher un plat prêt en cuisine.",
      solution: "Alerte dès qu'un plat est prêt, avec la table concernée.",
    },
  ],
  cuisine: [
    {
      probleme: "Recevoir une commande sans savoir depuis combien de temps elle attend.",
      solution: "Minuteur visible sur chaque commande, dès qu'elle arrive.",
    },
    {
      probleme: "Découvrir un plat en retard seulement quand le client se plaint.",
      solution: "La carte passe au rouge au-delà du délai d'alerte.",
    },
    {
      probleme: "Faire répéter au serveur les consignes d'un plat.",
      solution: "Options et notes affichées en évidence sur le ticket.",
    },
  ],
};

/**
 * Résultats de pilotes, à citer sur la page.
 *
 * Vide, et à ne remplir qu'avec des chiffres réellement relevés sur
 * `/dashboard/preuve` chez un établissement qui a donné son accord écrit pour
 * être cité (ROADMAP Phase 13.4). Inventer un résultat ou un témoignage
 * ruinerait la seule chose que cette page a à vendre.
 */
export const PILOT_RESULTS: { establishment: string; metric: string; value: string }[] = [];
