// Dictionnaire de référence — définit la forme (Dictionary) que chaque
// autre langue doit respecter exactement (voir ar.ts). Ne couvre QUE le
// parcours client (page /menu/[qrToken] + SplitBill) : les écrans
// staff/cuisine/manager restent en français pour l'instant (back-office
// interne, cf. ROADMAP.md).
import { formatMoney } from "@/lib/currency";
import { currentMarket } from "@/lib/market";

export const fr = {
  locale: "fr" as "fr" | "ar",
  dir: "ltr" as "ltr" | "rtl",
  // Symbole du marché courant, jamais "DT" en dur : le français sert les deux
  // marchés (TN et FR), l'arabe (ar.ts) reste écrit pour la Tunisie seule
  // pour l'instant — voir sa propre valeur, fixe, à cet endroit.
  currency: currentMarket.currency.symbol,
  localeSwitchLabel: "عربي",

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

  // Modification directe (fenêtre 1, tant que la commande est en attente de
  // confirmation) — voir orders/service.py::update_order_items.
  modifyOrderButton: "Modifier la commande",
  modifyOrderHint: "Modifiable tant que le serveur n'a pas confirmé",
  editOrderTitle: "Modifier la commande",
  editOrderSave: "Enregistrer les modifications",
  editOrderCancel: "Annuler",
  itemsUpdatedAt: (heure: string) => `Modifiée à ${heure}`,

  // Demande de modification (fenêtre 2, une fois la commande confirmée) —
  // voir orders/service.py::create_modification_request/resolve_modification_request.
  requestModificationButton: "Demander une modification",
  requestModificationHint: "Le serveur doit valider avec la cuisine avant toute modification",
  requestEditBanner: "Cette demande doit être validée par le serveur avec la cuisine avant d'être appliquée.",
  requestEditSend: "Envoyer la demande de modification",
  requestEditSubcopy: "Le serveur vérifiera avec la cuisine avant d'appliquer ces changements.",
  requestEditNewTotalLabel: "Nouveau total si accepté",
  requestEditCurrentTotal: (total: string) => `Total actuel de la commande : ${total}`,
  requestSentButton: "✓ Demande envoyée",
  requestPendingBanner: "Demande envoyée — en attente de la réponse du serveur.",
  requestOutcomeTitle: "Réponse du serveur",
  requestLineAccepted: "accepté",
  requestLineDeclined: "refusé",
  requestOrderSeparately: "Commander séparément",

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
    (tipAmount > 0 ? ` (dont ${formatMoney(tipAmount)} de pourboire)` : ""),
  cashPendingMessage: (amount: number) =>
    `Paiement en espèces demandé — un serveur va passer encaisser ${formatMoney(amount)}.`,
  cardTerminalPendingMessage: (amount: number) =>
    `Paiement carte demandé — un serveur va passer avec le terminal pour encaisser ${formatMoney(amount)}.`,
  tipLabel: "Pourboire (facultatif, pour un paiement par carte)",
  tipNone: "Sans",
  tipPlaceholder: formatMoney(0),
  emailLabel: "E-mail (facultatif, pour recevoir votre facture)",
  emailPlaceholder: "vous@exemple.com",
  payByCard: "Payer en ligne par carte",
  payByCardTerminal: "Carte à table (terminal serveur)",
  payByCash: "Espèces (le serveur passe encaisser)",
  paymentFailedRetry: "Le paiement n'a pas abouti. Vous pouvez réessayer.",
  invoiceDownload: "Télécharger la facture (PDF)",
  invoiceQrCaption: "Scannez pour la retrouver sur un autre appareil",
  orderAgain: "Commander à nouveau",
  postOrderSuggestionTitle: "Envie d'autre chose avant l'addition ?",

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
  sharedPerPersonAmount: (amount: number) => `${formatMoney(amount)} par personne`,
  dinersLabel: "Personnes à table",
  openOrdersTitle: (count: number, reste: number) =>
    count > 1
      ? `${count} commandes en cours — ${formatMoney(reste)} restent à régler`
      : `Une commande en cours — ${formatMoney(reste)} restent à régler`,
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

  // Options et suppléments sur un article (cuisson, sauce, accompagnement...).
  optionsChooseTitle: (name: string) => `Choisissez pour « ${name} »`,
  optionsGroupHint: (min: number, max: number) =>
    min === max ? `Choisissez ${min}` : min === 0 ? `Jusqu'à ${max} au choix` : `Entre ${min} et ${max} au choix`,
  optionsConfirmAdd: "Ajouter au panier",
  optionsCancelChoice: "Annuler",
  cartClearedNotice:
    "Un article de votre panier n'est plus disponible et a été retiré. Votre panier est maintenant vide.",

  shareOrderButton: "Partager ma commande",
  shareCardTitle: (restaurantName: string) => `Mon repas chez ${restaurantName}`,
  shareCardText: "Commandé sur Tawla 🍽️",

  // Modale d'avis Google après paiement (Phase D1bis, palier Pro+).
  googleReviewTitle: "Le repas vous a plu ?",
  googleReviewBody: (restaurantName: string) =>
    `Un avis Google aide ${restaurantName} à se faire connaître — ça prend trente secondes.`,
  googleReviewCta: "Laisser un avis Google",
  googleReviewDismiss: "Plus tard",
};

export type Dictionary = typeof fr;
