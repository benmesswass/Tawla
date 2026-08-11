import type { Dictionary } from "./fr";

// Arabe tunisien (derja) en écriture arabe — registre familier et chaleureux,
// adapté à un parcours client de commande au restaurant. `satisfies Dictionary`
// force le compilateur à vérifier que toutes les clés de fr.ts existent ici.
export const ar = {
  locale: "ar",
  dir: "rtl",
  currency: "د.ت",
  localeSwitchLabel: "Français",

  retry: "عاود المحاولة",
  loadingMenu: "قاعد يحمّل المينيو...",
  closeErrorAria: "غلق رسالة الخطأ",

  ramadanBanner: (time) =>
    `🌙 رمضان مبارك — الفطور على الساعة ${time}. تنجم تطلب دلوقتي للفطور، الأكلة تكون لاهية وقتها.`,
  addToCartAria: (name) => `زيد ${name} للقفة`,
  removeFromCartAria: (name) => `نقّص ${name} من القفة`,
  allergensLabel: (allergens) => `مسببات الحساسية: ${allergens}`,
  notHalalBadge: "مش حلال",
  notePlaceholder: "ملاحظة للكوجينة (إختياري، مثال: بلا بصل)",
  sharedCheckboxLabel: "🍽️ أكلة نتقاسموها في الطاولة الكل",
  preorderCheckboxLabel: (time) => `🌙 نطلب للفطور (${time}) بدل دلوقتي`,
  sending: "قاعد يتبعث...",
  validateOrder: "أكد الطلبية",

  orderCancelledTitle: "الطلبية تلغات",
  orderSentTitle: "الطلبية تبعثت 🎉",
  orderSubtitle: (tableLabel, orderId) => `${tableLabel} — الطلبية رقم ${orderId}`,
  preorderBadge: (time) => `🌙 طلبية مسبقة للفطور — التحضير مبرمج للساعة ${time}.`,
  dedicatedServer: (staffName) => `${staffName} باش يكون الجرسون تاعك لهاذي الطلبية.`,

  steps: {
    pending_confirmation: "تبعثت",
    confirmed: "تأكدت",
    sent_to_kitchen: "فالكوجينة",
    in_preparation: "قاعدة تتحضر",
    ready: "لاهية",
    served: "تقدمت",
  },

  orderDetailsTitle: "تفاصيل الطلبية",
  sharedTag: "🍽️ للقسمة",
  total: "المجموع",

  paymentTitle: "الخلاص",
  paidMessage: (method, tipAmount) =>
    `الخلاص تم ✓ ${method === "card" ? "بالكارت" : "كاش"}` +
    (tipAmount > 0 ? ` (فيها ${tipAmount.toFixed(2)} د.ت إكرامية)` : ""),
  cashPendingMessage: (amount) => `طلبت تخلص كاش — جرسون باش يجي يقبض ${amount.toFixed(2)} د.ت.`,
  tipLabel: "الإكرامية (إختياري، للخلاص بالكارت)",
  tipPlaceholder: "0.00 د.ت",
  payByCard: "خلص بالكارت",
  payByCash: "خلص كاش (الجرسون باش يجي يقبض)",
  orderAgain: "أطلب مرة أخرى",

  splitBillToggle: "قسم الفاتورة بين بعضكم",
  splitBillTitle: "قسمة الفاتورة",
  close: "غلق",
  splitModeEqual: "بالتساوي",
  splitModeByItem: "بالأكلة",
  peopleCountLabel: "عدد الناس",
  sharedOption: "للقسمة",
  personLabel: (n) => `شخص ${n}`,
  unassignedSharedNote: "الأكلات إلي ما تعيّنتش تتقسم بالتساوي.",
  splitBillDisclaimer: "إرشادي بركة — الخلاص يبقى للفاتورة الكل مرة وحدة للطاولة.",
} satisfies Dictionary;
