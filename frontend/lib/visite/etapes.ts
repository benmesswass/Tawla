/**
 * Contenu de la visite guidée commerciale.
 *
 * Sert à montrer Tawla à un restaurateur, en rendez-vous ou par un lien qu'on
 * lui envoie (`tawla.tn/?visite=1`). Chaque étape désigne un élément réel de la
 * page par son attribut `data-visite` : c'est l'écran du produit qui est
 * commenté, jamais une capture ni une maquette.
 *
 * Distinct de `components/DemoGuide.tsx`, qui est l'aide-mémoire de Wassim
 * pendant la démo (« coupez le réseau du téléphone, puis… ») — celui-ci
 * s'adresse au restaurateur, l'autre au vendeur.
 *
 * Rien ici ne doit annoncer de chiffre de terrain : tant qu'aucun pilote n'a
 * fourni de mesure (voir `PILOT_RESULTS` dans `lib/offer.ts`), la visite
 * décrit ce que le produit fait, jamais ce qu'il rapporte.
 */

export type EtapeVisite = {
  /** Identifiant stable — sert aussi de clé de rendu. */
  id: string;
  /** Page sur laquelle l'étape se joue. */
  route: string;
  /**
   * Adresse réellement ouverte par « Suivant », quand elle porte plus que la
   * route : la visite quitte les paliers sur Pro, elle doit donc arriver sur
   * l'inscription avec Pro sélectionné, comme un clic sur « Choisir Pro ».
   * Absent = la route suffit.
   */
  lien?: string;
  /**
   * Valeur de l'attribut `data-visite` de l'élément à mettre en lumière.
   * Absent = bulle centrée, sans projecteur (introduction, conclusion).
   */
  cible?: string;
  titre: string;
  corps: string;
};

export const ETAPES: EtapeVisite[] = [
  // --- Page d'accueil : ce qu'est le produit, puis l'offre ------------------
  {
    id: "intro",
    route: "/",
    titre: "Tawla en deux minutes",
    corps:
      "Votre client scanne le QR posé sur sa table, commande depuis son téléphone, et la commande arrive sur l'écran partagé de vos serveurs. Un serveur la prend en charge, la confirme à table, et elle part en cuisine. Cette visite vous montre chaque écran, dans l'ordre. Vous pouvez la quitter à tout moment.",
  },
  {
    id: "promesse",
    route: "/",
    cible: "accueil-promesse",
    titre: "Le serveur garde la main",
    corps:
      "C'est la différence avec une borne ou un menu PDF : rien n'entre en cuisine sans qu'un serveur l'ait vérifié à table. Le client gagne du temps, votre équipe garde le service.",
  },
  {
    id: "benefices",
    route: "/",
    cible: "accueil-benefices",
    titre: "Ce que ça change en salle",
    corps:
      "Trois choses : plus de commande oubliée entre la table et la cuisine, un serveur qui reste maître de ce qui part, et des chiffres sur votre service que vous n'avez aujourd'hui nulle part.",
  },
  {
    id: "inclus",
    route: "/",
    cible: "accueil-inclus",
    titre: "Vous n'avez rien à installer",
    corps:
      "Votre carte est saisie pour vous, les QR sont imprimés et livrés, et votre équipe est formée sur place en dix minutes. C'est ce qui sépare Tawla d'un logiciel en libre-service : personne ne vous laisse seul devant un écran.",
  },
  {
    id: "tarif-essentiel",
    route: "/",
    cible: "tarif-essentiel",
    titre: "Essentiel — 50 DT / mois",
    corps:
      "Pour un café ou une petite salle : le QR, la carte, la commande client, les écrans serveur et cuisine en temps réel, l'appel serveur depuis la table, et le paiement en espèces. Installation, QR imprimés et formation compris.",
  },
  {
    id: "tarif-pro",
    route: "/",
    cible: "tarif-pro",
    titre: "Pro — 100 DT / mois",
    corps:
      "Tout Essentiel, plus le paiement carte, le programme de fidélité, la suggestion « avec ce plat », le plan de salle visuel, les photos des plats et le mode Ramadan. C'est le palier que nous recommandons pour un restaurant qui sert à table.",
  },
  {
    id: "tarif-business",
    route: "/",
    cible: "tarif-business",
    titre: "Business — 150 DT / mois",
    corps:
      "Tout Pro, plus la gestion d'équipe : rapport par serveur pour décider d'une prime sur des chiffres, notifications à vos clients, support prioritaire. Le multi-établissements est construit à la demande, pour vous.",
  },
  {
    id: "creer-compte",
    route: "/",
    cible: "accueil-creer-compte",
    titre: "On crée votre établissement",
    corps:
      "Aucune commission sur vos commandes, quel que soit le palier : vos clients vous règlent directement, comme aujourd'hui. Passons à la création du compte — c'est quatre champs.",
  },

  // --- Création de compte ---------------------------------------------------
  {
    id: "signup-palier",
    route: "/signup",
    // La visite vient de présenter Pro comme le palier recommandé : elle entre
    // ici par le même chemin qu'un clic sur « Choisir Pro ».
    lien: "/signup?tier=pro",
    cible: "signup-palier",
    titre: "Le palier que vous avez choisi",
    corps:
      "Il reprend la carte tarif sur laquelle vous avez cliqué. Vous pourrez passer à un palier supérieur plus tard depuis votre tableau de bord, sans refaire de compte.",
  },
  {
    id: "signup-etablissement",
    route: "/signup",
    cible: "signup-etablissement",
    titre: "Le nom de votre établissement",
    corps:
      "C'est ce nom qui s'affichera sur le chevalet QR posé sur vos tables et en tête de la carte que voit votre client. Écrivez-le comme sur votre devanture.",
  },
  {
    id: "signup-identifiants",
    route: "/signup",
    cible: "signup-identifiants",
    titre: "Votre compte manager",
    corps:
      "Ce premier compte est le vôtre, celui de la direction. Vos serveurs et votre cuisine auront ensuite leurs propres accès, créés depuis votre tableau de bord — personne ne partage un mot de passe.",
  },
  {
    id: "signup-valider",
    route: "/signup",
    cible: "signup-valider",
    titre: "Et après ce bouton ?",
    corps:
      "Votre établissement est créé et vous arrivez directement sur votre tableau de bord. En vrai, à ce stade, votre carte et vos tables sont déjà en place : on les installe avec vous avant votre premier service.",
  },

  // --- Connexion ------------------------------------------------------------
  {
    id: "login-roles",
    route: "/login",
    cible: "login-formulaire",
    titre: "Une seule adresse, trois métiers",
    corps:
      "Vos serveurs, votre cuisine et vous entrez par cet écran. Chacun arrive sur le sien : le pool des commandes pour le serveur, les tickets pour la cuisine, le tableau de bord pour vous. Un serveur ne voit jamais votre recette.",
  },

  // --- Tableau de bord manager ---------------------------------------------
  {
    id: "dashboard-navigation",
    route: "/dashboard",
    cible: "dashboard-navigation",
    titre: "Vos quatre écrans de direction",
    corps:
      "La carte, l'activité du jour, la preuve du pilote et le rapport d'équipe. « Service en salle » vous ouvre l'écran de vos serveurs : vous pouvez confirmer une commande vous-même quand il y a du monde.",
  },
  {
    id: "dashboard-recette",
    route: "/dashboard",
    cible: "dashboard-recette",
    titre: "Votre service, en direct",
    corps:
      "La recette du jour se met à jour à chaque commande encaissée, sans que personne ait à saisir quoi que ce soit. Seul ce qui est réellement réglé y entre : une commande servie mais pas encore payée n'y est pas comptée.",
  },
  {
    id: "dashboard-onglets",
    route: "/dashboard",
    cible: "dashboard-onglets",
    titre: "Votre carte, vos tables, votre équipe",
    corps:
      "Un plat en rupture se signale en un clic : il se barre chez le client dans la seconde, sans qu'il ait à recharger. Il reste affiché, parce que « il n'y en a plus ce soir » est une information, pas un vide. Vous ajoutez une table, imprimez son QR, créez un accès serveur — sans nous appeler.",
  },
  {
    id: "fin",
    route: "/dashboard",
    titre: "Voilà pour le tour",
    corps:
      "La suite se voit mieux en vrai qu'en texte : le QR scanné à votre table, la commande qui apparaît chez le serveur, le ticket qui s'affiche en cuisine sans rafraîchir l'écran. On peut le faire chez vous, pendant un service creux.",
  },
];
