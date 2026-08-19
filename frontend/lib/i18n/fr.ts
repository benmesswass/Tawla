// Dictionnaire de référence — définit la forme (Dictionary) que chaque
// autre langue doit respecter exactement (voir ar.ts). Ne couvre QUE le
// parcours client (page /menu/[qrToken] + SplitBill) : les écrans
// staff/cuisine/manager restent en français pour l'instant (back-office
// interne, cf. ROADMAP.md).
export const fr = {
  locale: "fr" as "fr" | "ar",
  dir: "ltr" as "ltr" | "rtl",
  currency: "DT",
  localeSwitchLabel: "عربي",

  retry: "Réessayer",
  loadingMenu: "Chargement du menu...",
  closeErrorAria: "Fermer le message d'erreur",

  ramadanBanner: (time: string) =>
    `Ramadan Moubarak — rupture du jeûne à ${time}. Vous pouvez commander maintenant pour l'iftar, votre plat sera prêt à l'heure.`,
  addToCartAria: (name: string) => `Ajouter ${name} au panier`,
  removeFromCartAria: (name: string) => `Retirer un ${name} du panier`,
  allergensLabel: (allergens: string) => `Allergènes : ${allergens}`,
  notHalalBadge: "Non halal",
  callWaiterButton: "Appeler le serveur",
  callWaiterSent: "✓ Serveur prévenu, il arrive",
  notePlaceholder: "Note pour la cuisine (facultatif, ex : sans oignons)",
  sharedCheckboxLabel: "Plat à partager pour toute la table",
  preorderCheckboxLabel: (time: string) => `Commander pour l'iftar (${time}) plutôt que maintenant`,
  sending: "Envoi...",
  validateOrder: "Valider la commande",

  orderCancelledTitle: "Commande annulée",
  orderSentTitle: "Commande envoyée 🎉",
  orderSubtitle: (tableLabel: string, orderId: number) => `${tableLabel} — commande #${orderId}`,
  preorderBadge: (time: string) => `Pré-commande pour l'iftar — préparation prévue pour ${time}.`,
  dedicatedServer: (staffName: string) => `${staffName} est votre serveur dédié pour cette commande.`,

  steps: {
    pending_confirmation: "Envoyée",
    confirmed: "Confirmée",
    sent_to_kitchen: "En cuisine",
    in_preparation: "En préparation",
    ready: "Prête",
    served: "Servie",
  },
  kitchenWaitHint: "Généralement 10 à 20 minutes selon l'affluence.",

  orderDetailsTitle: "Détail de la commande",
  sharedTag: "à partager",
  total: "Total",

  paymentTitle: "Paiement",
  paidMessage: (method: "card" | "cash", tipAmount: number) =>
    `Payé ✓ ${method === "card" ? "par carte" : "en espèces"}` +
    (tipAmount > 0 ? ` (dont ${tipAmount.toFixed(2)} DT de pourboire)` : ""),
  cashPendingMessage: (amount: number) =>
    `Paiement en espèces demandé — un serveur va passer encaisser ${amount.toFixed(2)} DT.`,
  tipLabel: "Pourboire (facultatif, pour un paiement par carte)",
  tipPlaceholder: "0.00 DT",
  payByCard: "Payer par carte",
  payByCash: "Payer en espèces (le serveur passera encaisser)",
  paymentFailedRetry: "Le paiement n'a pas abouti. Vous pouvez réessayer.",
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

  offlineQueuedTitle: "Pas de connexion",
  offlineQueuedMessage: "Votre commande est enregistrée sur votre téléphone et sera envoyée automatiquement dès que la connexion revient.",
  retryNow: "Réessayer maintenant",

  loyaltyToggle: "Programme fidélité (facultatif)",
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
  dinersLabel: "Personnes à table",
  openOrdersTitle: (count: number, reste: number) =>
    count > 1
      ? `${count} commandes en cours — ${reste.toFixed(2)} DT restent à régler`
      : `Une commande en cours — ${reste.toFixed(2)} DT restent à régler`,
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
