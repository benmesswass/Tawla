// Dictionnaire de référence — définit la forme (Dictionary) que chaque
// autre langue doit respecter exactement (voir ar.ts). Ne couvre QUE le
// parcours client (page /menu/[qrToken]) : les écrans
// staff/cuisine/manager restent en français pour l'instant (back-office
// interne, cf. ROADMAP.md).
import { formatMoney } from "@/lib/currency";
import { currentMarket } from "@/lib/market";

export const fr = {
  locale: "fr" as "fr" | "ar" | "en",
  dir: "ltr" as "ltr" | "rtl",
  // Symbole du marché courant, jamais "DT" en dur : le français sert les deux
  // marchés (TN et FR), l'arabe (ar.ts) reste écrit pour la Tunisie seule
  // pour l'instant — voir sa propre valeur, fixe, à cet endroit.
  currency: currentMarket.currency.symbol,

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
  // Polarité inverse, marché France (F5/A6) — voir Market.defaultHalal et
  // son commentaire dans lib/market.ts : le badge signale l'EXCEPTION,
  // jamais la norme du marché servi.
  halalBadge: "Halal",
  callWaiterButton: "Appeler le serveur",
  callWaiterSent: "✓ Serveur prévenu, il arrive",
  notePlaceholder: "Note pour la cuisine (facultatif, ex : sans oignons)",
  sharedCheckboxLabel: "Plat à partager",
  preorderCheckboxLabel: (time: string) => `Commander pour l'iftar (${time}) plutôt que maintenant`,
  sending: "Envoi...",
  validateOrder: "Valider la commande",
  cartItemsCount: (n: number) => `${n} article${n > 1 ? "s" : ""}`,
  // Écran de récapitulatif ouvert avant validation (façon « panier » d'appli
  // de livraison) : le bouton du bandeau bas ouvre ce récapitulatif au lieu
  // de valider directement, pour que le client revoie tout avant de confirmer.
  viewCartButton: "Panier de table",
  cartSummaryTitle: "Panier de la table",
  backToMenuButton: "← Retour à la carte",

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

  // Ajouter d'autres plats en éditant une commande : rouvre la carte complète
  // (mêmes fiches que le premier passage) plutôt qu'une liste repliée sur
  // place — décision de Wassim, 2026-09-09 (ROADMAP_DESIGN.md).
  myOrderTitle: "Ma commande",
  orderPanelCount: (n: number) => `${n} plat${n > 1 ? "s" : ""}`,
  browseCarteButton: "+ Ajouter d'autres plats",
  browseCarteTitle: "La carte",
  backToOrderButton: "Retour à ma commande",

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
  totalToPayLabel: "Total à payer (pourboire inclus)",
  emailLabel: "E-mail (facultatif, pour recevoir votre facture)",
  emailPlaceholder: "vous@exemple.com",
  payByCard: "Payer en ligne par carte",
  payByCardTerminal: "Carte à table (terminal serveur)",
  payByCash: "Espèces (le serveur passe encaisser)",
  paymentFailedRetry: "Le paiement n'a pas abouti. Vous pouvez réessayer.",
  // Paiement par personne (identité de table, ROADMAP.md §Override, extension).
  paidByPerson: (name: string) => `${name} a payé sa part`,
  remainingAmountLabel: "Reste à payer :",
  myShareTitle: "Votre part",
  myShareAlreadyPaidMessage: "Vous avez réglé votre part — merci !",
  invoiceDownload: "Télécharger la facture (PDF)",
  invoiceQrCaption: "Scannez pour la retrouver sur un autre appareil",
  orderAgain: "Commander à nouveau",
  postOrderSuggestionTitle: "Envie d'autre chose avant l'addition ?",

  // Répartir l'addition (chantier hiérarchie du paiement, 2026-09-10) — nom
  // choisi pour ne plus se confondre avec `shareOrderButton` ("Partager ma
  // commande", partage social, sans rapport).
  repartitionSectionTitle: "Répartition",
  shareBillCardTitle: "Répartir l'addition",
  shareBillHelper: "Répartissez cette commande avec les autres personnes à table.",
  totalOrderAmountNote: (amount: number) => `sur une addition totale de ${formatMoney(amount)}`,
  splitModeEqual: "Équitable",
  splitModeByItem: "Par plat",
  sharedOption: "Partagé",
  personLabel: (n: number) => `Personne ${n}`,
  unassignedSharedNote: "Les plats non attribués sont partagés équitablement.",
  equalSplitNote: "Chacun paie le même montant, quel que soit ce qu'il a commandé.",

  // Identité de table (ROADMAP.md §Override, extension) : modale affichée dès
  // le scan, remplace l'ancien "vous êtes combien à table ?" posé une fois
  // pour toute la tablée — chaque téléphone répond pour lui-même.
  identityPromptTitle: "Votre prénom",
  identityPromptSubtitle:
    "Il suivra vos plats jusqu'au paiement — pratique pour partager l'addition à la fin.",
  identityInputPlaceholder: "Perso1",
  identityInputCaption: "Laissé vide, vous resterez « Perso1 ».",
  identityContinue: "Continuer",
  identityPromptSkip: "Passer",
  rosterSectionTitle: "À table",
  rosterYouTag: (name: string) => `Vous · ${name}`,
  rosterAddGuestChip: "+ Ajouter",
  rosterAddGuestPlaceholder: "Prénom (ex : Yassine)",
  rosterAddGuestConfirm: "Ajouter",
  rosterOwnItemsOnlyNote: "Vous ne pouvez retirer que vos propres plats.",
  // Rappel dans le panier de l'assignation faite sur la carte (« Pour qui ? »).
  // Sans ça, le convive coche des prénoms côté carte et le panier n'en garde
  // aucune trace visible — l'assignation semble perdue (retour QA).
  cartForWhom: (names: string) => `Pour ${names}`,

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
  sharedWithLabel: "Pour qui ?",
  sharedWithEveryone: "Non assigné : réparti équitablement à l'addition.",
  sharedPerPersonAmount: (amount: number) => `${formatMoney(amount)} par personne`,
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
