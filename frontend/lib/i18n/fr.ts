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
  loyaltyProgress: (count: number, remaining: number) =>
    `Fidélité : ${count} commande${count > 1 ? "s" : ""} — encore ${remaining} pour un article offert !`,
  loyaltyRewardAvailable: "🎉 Récompense disponible ! Montrez cet écran à votre serveur.",
  loyaltyBirthdayBanner: "Bon anniversaire ! Demandez votre réduction spéciale au serveur.",

  pushSubscribeButton: "Me notifier quand c'est prêt",
  pushSubscribed: "Vous serez notifié dès que votre commande sera prête.",
  pushDenied: "Notifications bloquées — activez-les dans les réglages de votre navigateur si vous changez d'avis.",
};

export type Dictionary = typeof fr;
