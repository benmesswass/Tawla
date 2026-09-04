import type { Dictionary } from "./fr";
import { formatMoney } from "@/lib/currency";
import { currentMarket } from "@/lib/market";

// Anglais — France, MARCHE_FRANCE.md phase F5/A9 (le seul marché qui liste
// "en" dans `Market.languages`, voir lib/market.ts). `formatMoney` comme
// fr.ts, jamais un symbole en dur : ce dictionnaire suit le marché courant
// (EUR aujourd'hui), pas une devise figée comme ar.ts (Tunisie/TND
// seulement). `satisfies Dictionary` force le compilateur à vérifier que
// toutes les clés de fr.ts existent ici.
export const en = {
  locale: "en",
  dir: "ltr",
  currency: currentMarket.currency.symbol,

  retry: "Try again",
  loadingMenu: "Loading menu...",
  closeErrorAria: "Close error message",

  ramadanBannerPrefix: "Ramadan Mubarak",
  ramadanBannerRest: (time) =>
    ` — iftar at ${time}. You can order now for iftar, your dish will be ready on time.`,
  addToCartAria: (name) => `Add ${name} to cart`,
  removeFromCartAria: (name) => `Remove one ${name} from cart`,
  allergensLabel: (allergens) => `Allergens: ${allergens}`,
  notHalalBadge: "Not halal",
  halalBadge: "Halal",
  callWaiterButton: "Call the waiter",
  callWaiterSent: "✓ Waiter notified, on their way",
  notePlaceholder: "Note for the kitchen (optional, e.g. no onions)",
  sharedCheckboxLabel: "Dish to share with the whole table",
  preorderCheckboxLabel: (time) => `Order for iftar (${time}) instead of now`,
  sending: "Sending...",
  validateOrder: "Place order",
  cartItemsCount: (n) => `${n} item${n > 1 ? "s" : ""}`,

  orderCancelledTitle: "Order cancelled",
  orderSentTitle: "Order sent 🎉",
  orderSubtitle: (tableLabel, orderId) => `${tableLabel} — order #${orderId}`,
  preorderBadge: (time) => `Pre-order for iftar — preparation planned for ${time}.`,
  dedicatedServer: (staffName) => `${staffName} is your dedicated waiter for this order.`,

  trackingSteps: {
    received: "Order received",
    confirmed: "Confirmed by the waiter",
    in_kitchen: "In the kitchen",
    ready: "Ready to serve",
    served: "Served",
  },
  kitchenWaitHint: "Usually 10 to 20 minutes depending on how busy we are.",

  orderDetailsTitle: "Order details",
  sharedTag: "to share",
  total: "Total",

  paymentTitle: "Payment",
  paidMessage: (method, tipAmount) =>
    `Paid ✓ ${method === "cash" ? "in cash" : "by card"}` +
    (tipAmount > 0 ? ` (including ${formatMoney(tipAmount)} tip)` : ""),
  cashPendingMessage: (amount) =>
    `Cash payment requested — a waiter will come to collect ${formatMoney(amount)}.`,
  cardTerminalPendingMessage: (amount) =>
    `Card payment requested — a waiter will bring the terminal to collect ${formatMoney(amount)}.`,
  tipLabel: "Tip (optional, for card payment)",
  tipNone: "None",
  tipPlaceholder: formatMoney(0),
  emailLabel: "Email (optional, to receive your invoice)",
  emailPlaceholder: "you@example.com",
  payByCard: "Pay online by card",
  payByCardTerminal: "Card at the table (waiter's terminal)",
  payByCash: "Cash (the waiter will come to collect)",
  paymentFailedRetry: "The payment did not go through. You can try again.",
  invoiceDownload: "Download invoice (PDF)",
  invoiceQrCaption: "Scan to find it on another device",
  orderAgain: "Order again",
  postOrderSuggestionTitle: "Fancy something else before the bill?",

  splitBillToggle: "Split the bill between several people",
  splitBillTitle: "Split the bill",
  close: "Close",
  splitModeEqual: "Equal",
  splitModeByItem: "By dish",
  peopleCountLabel: "Number of people",
  sharedOption: "Shared",
  personLabel: (n) => `Person ${n}`,
  unassignedSharedNote: "Unassigned dishes are shared equally.",
  splitBillDisclaimer: "For guidance only — payment covers the full bill, once for the whole table.",

  offlineQueuedTitle: "Connection lost",
  offlineQueuedMessage:
    "Your order is saved on this phone. It will be sent as soon as the network is back — don't refresh the page.",
  offlineRetryCountdown: (seconds) => `Retrying in ${seconds}s…`,
  retryNow: "Retry now",

  loyaltyToggle: "Loyalty program (optional)",
  loyaltyCardTitle: "Loyalty card",
  loyaltyCompleteTitle: "Card complete",
  loyaltyPhoneLabel: "Phone number",
  // Format plausible pour le marché français, jamais l'exemple tunisien de
  // fr.ts/ar.ts ("20 123 456") : un client anglophone à Paris ne doit pas
  // voir un indice tunisien dans le placeholder.
  loyaltyPhonePlaceholder: "E.g.: 06 12 34 56 78",
  loyaltyBirthDateLabel: "Date of birth (optional, for your birthday discount)",
  loyaltyConsentNotice:
    "Your number is only used for this restaurant's loyalty card. It is never shared, never used to contact you for marketing purposes, and is deleted after 24 months without an order.",
  loyaltyPrivacyLink: "Privacy policy",
  loyaltyProgress: (count, remaining) =>
    `Loyalty: ${count} order${count > 1 ? "s" : ""} — ${remaining} more for a free item!`,
  itemOutOfStock: "Currently unavailable",
  orderElapsed: (duree) => `Sent ${duree} ago`,
  tableTotalTitle: "What your table owes in total",
  orderLabel: (id) => `Order #${id}`,
  thisOrder: "this one",
  tableTotal: "Total due",
  tableTotalNote:
    "The payment below only settles the order shown. Come back to the others to pay them in turn, or ask the waiter to collect everything at once.",
  sharedWithLabel: "Shared with:",
  sharedWithEveryone: "No one selected: shared by the whole table.",
  sharedPerPersonAmount: (amount) => `${formatMoney(amount)} per person`,
  dinersLabel: "Number of guests",
  openOrdersTitle: (count, reste) =>
    count > 1
      ? `${count} orders in progress — ${formatMoney(reste)} left to pay`
      : `One order in progress — ${formatMoney(reste)} left to pay`,
  openOrderLine: (id, lines) => `Order #${id} — ${lines} item${lines > 1 ? "s" : ""}`,
  loyaltyFirstVisit: "First visit — your card starts with this order.",
  loyaltyRewardAvailable: "🎉 Reward available! Show this screen to your waiter.",
  loyaltyBirthdayBanner: "Happy birthday! Ask your waiter for your special discount.",

  pushSubscribeButton: "Notify me when it's ready",
  pushSubscribed: "You'll be notified as soon as your order is ready.",
  pushDenied: "Notifications blocked — enable them in your browser settings if you change your mind.",

  suggestionTitle: (name) => `With "${name}"?`,
  suggestionHint: "Suggested by the restaurant — feel free to skip.",
  suggestionAdd: "Add",
  suggestionDismiss: "No thanks",

  optionsChooseTitle: (name) => `Choose for "${name}"`,
  optionsGroupHint: (min, max) =>
    min === max ? `Choose ${min}` : min === 0 ? `Up to ${max} choices` : `Choose between ${min} and ${max}`,
  optionsConfirmAdd: "Add to cart",
  optionsCancelChoice: "Cancel",
  cartClearedNotice: "An item in your cart is no longer available and has been removed. Your cart is now empty.",

  shareOrderButton: "Share my order",
  shareCardTitle: (restaurantName) => `My meal at ${restaurantName}`,
  shareCardText: "Ordered on Tawla 🍽️",

  googleReviewTitle: "Enjoyed your meal?",
  googleReviewBody: (restaurantName) =>
    `A Google review helps ${restaurantName} get noticed — it only takes thirty seconds.`,
  googleReviewCta: "Leave a Google review",
  googleReviewDismiss: "Later",
} satisfies Dictionary;
