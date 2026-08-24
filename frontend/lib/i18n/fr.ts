// Dictionnaire de référence — définit la forme (Dictionary) que chaque
// autre langue doit respecter exactement (voir ar.ts, en.ts). Ne couvre QUE
// le parcours client (page /menu/[qrToken] + SplitBill) : les écrans
// staff/cuisine/manager restent en français pour l'instant (back-office
// interne, cf. ROADMAP.md).
//
// Seul dictionnaire partagé entre les deux marchés (le français se parle en
// Tunisie comme en France) : c'est pour ça, et seulement ici, que les
// montants passent par `formatAmount()` plutôt qu'un `toFixed(3) DT` en dur —
// ar.ts et en.ts, eux, ne chargent jamais que sous leur marché respectif et
// peuvent garder leur devise en dur sans risque.
import { currentMarket, formatAmount } from "@/lib/market";

// Le libellé du bouton de bascule s'écrit dans la langue VERS laquelle il
// mène (même convention qu'ar.ts, qui dit "Français" — pas la traduction du
// mot "arabe"/"anglais"). Comme `currency` juste au-dessus, calculé une fois
// pour tout le marché de ce déploiement, jamais par requête.
const OTHER_LANGUAGE_LABEL: Record<string, string> = { ar: "عربي", en: "English" };
const otherLanguage = currentMarket().languages.find((code) => code !== "fr") ?? "ar";

export const fr = {
  locale: "fr" as "fr" | "ar" | "en",
  dir: "ltr" as "ltr" | "rtl",
  currency: currentMarket().currency.symbol,
  localeSwitchLabel: OTHER_LANGUAGE_LABEL[otherLanguage] ?? "عربي",

  retry: "Réessayer",
  loadingMenu: "Chargement du menu...",
  closeErrorAria: "Fermer le message d'erreur",

  ramadanBannerPrefix: "Ramadan Moubarak",
  ramadanBannerRest: (time: string) =>
    ` — rupture du jeûne à ${time}. Vous pouvez commander maintenant pour l'iftar, votre plat sera prêt à l'heure.`,
  addToCartAria: (name: string) => `Ajouter ${name} au panier`,
  removeFromCartAria: (name: string) => `Retirer un ${name} du panier`,
  allergensLabel: (allergens: string) => `Allergènes : ${allergens}`,
  notHalalBadge: "Non halal",
  vegetarianBadge: "Végétarien",
  veganBadge: "Vegan",
  glutenFreeBadge: "Sans gluten",
  formulasSectionTitle: "Formules",
  callWaiterButton: "Appeler le serveur",
  callWaiterSent: "✓ Serveur prévenu, il arrive",
  notePlaceholder: "Note pour la cuisine (facultatif, ex : sans oignons)",
  sharedCheckboxLabel: "Plat à partager pour toute la table",
  preorderCheckboxLabel: (time: string) => `Commander pour l'iftar (${time}) plutôt que maintenant`,
  sending: "Envoi...",
  validateOrder: "Valider la commande",
  cartItemsCount: (n: number) => `${n} article${n > 1 ? "s" : ""}`,

  orderCancelledTitle: "Commande annulée",
  orderSentTitle: "Commande envoyée 🎉",
  orderSubtitle: (tableLabel: string, orderId: number) => `${tableLabel} — commande #${orderId}`,
  preorderBadge: (time: string) => `Pré-commande pour l'iftar — préparation prévue pour ${time}.`,
  dedicatedServer: (staffName: string) => `${staffName} est votre serveur dédié pour cette commande.`,

  trackingSteps: {
    received: "Commande reçue",
    confirmed: "Confirmée par le serveur",
    in_kitchen: "En cuisine",
    ready: "Prête à servir",
    served: "Servie",
  },
  kitchenWaitHint: "Généralement 10 à 20 minutes selon l'affluence.",

  orderDetailsTitle: "Détail de la commande",
  sharedTag: "à partager",
  total: "Total",

  paymentTitle: "Paiement",
  paidMessage: (method: "card" | "card_terminal" | "cash", tipAmount: number) =>
    `Payé ✓ ${method === "cash" ? "en espèces" : "par carte"}` +
    (tipAmount > 0 ? ` (dont ${formatAmount(tipAmount)} de pourboire)` : ""),
  cashPendingMessage: (amount: number) =>
    `Paiement en espèces demandé — un serveur va passer encaisser ${formatAmount(amount)}.`,
  cardTerminalPendingMessage: (amount: number) =>
    `Paiement carte demandé — un serveur va passer avec le terminal pour encaisser ${formatAmount(amount)}.`,
  tipLabel: "Pourboire (facultatif, pour un paiement par carte)",
  tipNone: "Sans",
  tipPlaceholder: formatAmount(0, { decimals: 2 }),
  emailLabel: "E-mail (facultatif, pour recevoir votre facture)",
  emailPlaceholder: "vous@exemple.com",
  payByCard: "Payer en ligne — Konnect",
  payByCardTerminal: "Carte à table (terminal serveur)",
  payByCash: "Espèces (le serveur passe encaisser)",
  paymentFailedRetry: "Le paiement n'a pas abouti. Vous pouvez réessayer.",
  invoiceDownload: "Télécharger la facture (PDF)",
  invoiceQrCaption: "Scannez pour la retrouver sur un autre appareil",
  orderAgain: "Commander à nouveau",

  splitBillToggle: "Partager l'addition entre plusieurs personnes",
  splitBillTitle: "Partager l'addition",
  close: "Fermer",
  splitModeEqual: "Équitable",
  splitModeByItem: "Par plat",
  peopleCountLabel: "Nombre de personnes",
  sharedOption: "Partagé",
  personLabel: (n: number) => `Personne ${n}`,
  unassignedSharedNote: "Les plats non attribués sont partagés équitablement.",
  splitBillDisclaimer: "Indicatif — le paiement se fait pour l'addition complète, une seule fois pour la table.",

  offlineQueuedTitle: "Connexion perdue",
  offlineQueuedMessage: "Votre commande est enregistrée sur ce téléphone. Elle partira dès le retour du réseau — n'actualisez pas la page.",
  offlineRetryCountdown: (seconds: number) => `Nouvel essai dans ${seconds} s…`,
  retryNow: "Réessayer maintenant",

  loyaltyToggle: "Programme fidélité (facultatif)",
  loyaltyCardTitle: "Carte de fidélité",
  loyaltyCompleteTitle: "Carte complète",
  loyaltyPhoneLabel: "Numéro de téléphone",
  loyaltyPhonePlaceholder: "Ex : 20 123 456",
  loyaltyBirthDateLabel: "Date de naissance (facultatif, pour votre réduction anniversaire)",
  // Consentement explicite (Phase 16) : le client doit savoir à quoi sert son
  // numéro AVANT de le taper, pas dans une page qu'il n'ouvrira jamais.
  loyaltyConsentNotice:
    "Votre numéro sert uniquement à la carte de fidélité de ce restaurant. Il n'est jamais partagé, jamais utilisé pour vous démarcher, et il est supprimé après 24 mois sans commande.",
  loyaltyPrivacyLink: "Politique de confidentialité",
  loyaltyProgress: (count: number, remaining: number) =>
    `Fidélité : ${count} commande${count > 1 ? "s" : ""} — encore ${remaining} pour un article offert !`,
  itemOutOfStock: "Indisponible actuellement",
  orderElapsed: (duree: string) => `Envoyée il y a ${duree}`,
  tableTotalTitle: "Ce que votre table doit en tout",
  orderLabel: (id: number) => `Commande #${id}`,
  thisOrder: "celle-ci",
  tableTotal: "Total à régler",
  tableTotalNote:
    "Le paiement ci-dessous règle uniquement la commande affichée. Revenez sur les autres pour les régler à leur tour, ou demandez au serveur de tout encaisser en une fois.",
  sharedWithLabel: "Partagé entre :",
  sharedWithEveryone: "Personne de sélectionnée : partagé par toute la table.",
  sharedPerPersonAmount: (amount: number) => `${formatAmount(amount)} par personne`,
  dinersLabel: "Personnes à table",
  openOrdersTitle: (count: number, reste: number) =>
    count > 1
      ? `${count} commandes en cours — ${formatAmount(reste)} restent à régler`
      : `Une commande en cours — ${formatAmount(reste)} restent à régler`,
  openOrderLine: (id: number, lines: number) =>
    `Commande #${id} — ${lines} article${lines > 1 ? "s" : ""}`,
  loyaltyFirstVisit: "Première visite — votre carte démarre avec cette commande.",
  loyaltyRewardAvailable: "🎉 Récompense disponible ! Montrez cet écran à votre serveur.",
  loyaltyBirthdayBanner: "Bon anniversaire ! Demandez votre réduction spéciale au serveur.",

  pushSubscribeButton: "Me notifier quand c'est prêt",
  pushSubscribed: "Vous serez notifié dès que votre commande sera prête.",
  pushDenied: "Notifications bloquées — activez-les dans les réglages de votre navigateur si vous changez d'avis.",

  suggestionTitle: (name: string) => `Avec « ${name} » ?`,
  suggestionHint: "Proposé par le restaurant — vous pouvez ignorer.",
  suggestionAdd: "Ajouter",
  suggestionDismiss: "Non merci",
  cartClearedNotice:
    "Un article de votre panier n'est plus disponible et a été retiré. Votre panier est maintenant vide.",

  shareOrderButton: "Partager ma commande",
  shareCardTitle: (restaurantName: string) => `Mon repas chez ${restaurantName}`,
  shareCardText: "Commandé sur Tawla 🍽️",
};

export type Dictionary = typeof fr;
