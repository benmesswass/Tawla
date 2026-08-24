import type { Dictionary } from "./fr";
import { formatAmount } from "@/lib/market";

// Anglais — parcours client du marché français (F5-A9, MARCHE_FRANCE.md).
// Ne charge jamais que sous MARKET=fr (voir lib/market.ts, languages: ["fr",
// "en"]) : contrairement à fr.ts, partagé entre les deux marchés, celui-ci
// peut garder sa devise en dur sans risque — toujours l'euro sous ce marché.
// `satisfies Dictionary` force le compilateur à vérifier que toutes les clés
// de fr.ts existent ici, même principe que ar.ts.
export const en = {
  locale: "en",
  dir: "ltr",
  currency: "€",
  localeSwitchLabel: "Français",

  retry: "Retry",
  loadingMenu: "Loading menu...",
  closeErrorAria: "Close error message",

  ramadanBannerPrefix: "Ramadan Mubarak",
  ramadanBannerRest: (time) =>
    ` — iftar at ${time}. You can order now for iftar, your dish will be ready on time.`,
  addToCartAria: (name) => `Add ${name} to cart`,
  removeFromCartAria: (name) => `Remove one ${name}`,
  allergensLabel: (allergens) => `Allergens: ${allergens}`,
  notHalalBadge: "Not halal",
  vegetarianBadge: "Vegetarian",
  veganBadge: "Vegan",
  glutenFreeBadge: "Gluten-free",
  formulasSectionTitle: "Set menus",
  callWaiterButton: "Call a waiter",
  callWaiterSent: "✓ Waiter notified, on their way",
  notePlaceholder: "Note for the kitchen (optional, e.g. no onions)",
  sharedCheckboxLabel: "Dish to share for the whole table",
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
    confirmed: "Confirmed by waiter",
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
    (tipAmount > 0 ? ` (including ${formatAmount(tipAmount)} tip)` : ""),
  cashPendingMessage: (amount) => `Cash payment requested — a waiter will collect ${formatAmount(amount)}.`,
  cardTerminalPendingMessage: (amount) =>
    `Card payment requested — a waiter will bring the terminal to collect ${formatAmount(amount)}.`,
  tipLabel: "Tip (optional, for card payment)",
  tipNone: "None",
  tipPlaceholder: formatAmount(0, { decimals: 2 }),
  emailLabel: "Email (optional, to receive your invoice)",
  emailPlaceholder: "you@example.com",
  payByCard: "Pay online",
  payByCardTerminal: "Card at the table (waiter's terminal)",
  payByCash: "Cash (a waiter will collect it)",
  paymentFailedRetry: "Payment failed. You can try again.",
  invoiceDownload: "Download invoice (PDF)",
  invoiceQrCaption: "Scan to reopen it on another device",
  orderAgain: "Order again",

  splitBillToggle: "Split the bill between several people",
  splitBillTitle: "Split the bill",
  close: "Close",
  splitModeEqual: "Equal split",
  splitModeByItem: "By dish",
  peopleCountLabel: "Number of people",
  sharedOption: "Shared",
  personLabel: (n) => `Person ${n}`,
  unassignedSharedNote: "Unassigned dishes are split equally.",
  splitBillDisclaimer: "For reference only — the whole bill is paid at once, for the table.",

  offlineQueuedTitle: "Connection lost",
  offlineQueuedMessage:
    "Your order is saved on this phone. It will be sent as soon as the network is back — don't refresh the page.",
  offlineRetryCountdown: (seconds) => `Retrying in ${seconds}s…`,
  retryNow: "Retry now",

  loyaltyToggle: "Loyalty program (optional)",
  loyaltyCardTitle: "Loyalty card",
  loyaltyCompleteTitle: "Card complete",
  loyaltyPhoneLabel: "Phone number",
  loyaltyPhonePlaceholder: "e.g. 06 12 34 56 78",
  loyaltyBirthDateLabel: "Date of birth (optional, for your birthday discount)",
  loyaltyConsentNotice:
    "Your number is only used for this restaurant's loyalty card. It is never shared, never used to contact you otherwise, and deleted after 24 months without an order.",
  loyaltyPrivacyLink: "Privacy policy",
  loyaltyProgress: (count, remaining) =>
    `Loyalty: ${count} order${count > 1 ? "s" : ""} — ${remaining} more for a free item!`,
  itemOutOfStock: "Currently unavailable",
  orderElapsed: (duree) => `Sent ${duree} ago`,
  tableTotalTitle: "What your table owes in total",
  orderLabel: (id) => `Order #${id}`,
  thisOrder: "this one",
  tableTotal: "Total to pay",
  tableTotalNote:
    "The payment below only settles the order shown. Come back to the others to pay them in turn, or ask a waiter to collect everything at once.",
  sharedWithLabel: "Shared with:",
  sharedWithEveryone: "No one selected: shared by the whole table.",
  sharedPerPersonAmount: (amount) => `${formatAmount(amount)} per person`,
  dinersLabel: "People at the table",
  openOrdersTitle: (count, reste) =>
    count > 1
      ? `${count} orders in progress — ${formatAmount(reste)} left to pay`
      : `One order in progress — ${formatAmount(reste)} left to pay`,
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
  cartClearedNotice: "An item in your cart is no longer available and was removed. Your cart is now empty.",

  shareOrderButton: "Share my order",
  shareCardTitle: (restaurantName) => `My meal at ${restaurantName}`,
  shareCardText: "Ordered on Tawla 🍽️",

  googleReviewPromptTitle: "Enjoyed your meal?",
  googleReviewPromptButton: "Leave a Google review",
} satisfies Dictionary;
