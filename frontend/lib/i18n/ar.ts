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
    `رمضان مبارك — الفطور على الساعة ${time}. تنجم تطلب دلوقتي للفطور، الأكلة تكون لاهية وقتها.`,
  addToCartAria: (name) => `زيد ${name} للقفة`,
  removeFromCartAria: (name) => `نقّص ${name} من القفة`,
  allergensLabel: (allergens) => `مسببات الحساسية: ${allergens}`,
  notHalalBadge: "مش حلال",
  callWaiterButton: "نادي على الجرسون",
  callWaiterSent: "✓ الجرسون تعرّف، باش يجي دلوقتي",
  notePlaceholder: "ملاحظة للكوجينة (إختياري، مثال: بلا بصل)",
  sharedCheckboxLabel: "أكلة نتقاسموها في الطاولة الكل",
  preorderCheckboxLabel: (time) => `نطلب للفطور (${time}) بدل دلوقتي`,
  sending: "قاعد يتبعث...",
  validateOrder: "أكد الطلبية",

  orderCancelledTitle: "الطلبية تلغات",
  orderSentTitle: "الطلبية تبعثت 🎉",
  orderSubtitle: (tableLabel, orderId) => `${tableLabel} — الطلبية رقم ${orderId}`,
  preorderBadge: (time) => `طلبية مسبقة للفطور — التحضير مبرمج للساعة ${time}.`,
  dedicatedServer: (staffName) => `${staffName} باش يكون الجرسون تاعك لهاذي الطلبية.`,

  steps: {
    pending_confirmation: "تبعثت",
    confirmed: "تأكدت",
    sent_to_kitchen: "فالكوجينة",
    in_preparation: "قاعدة تتحضر",
    ready: "لاهية",
    served: "تقدمت",
  },
  kitchenWaitHint: "عادة من 10 إلى 20 دقيقة، يتبدل حسب الزحمة.",

  orderDetailsTitle: "تفاصيل الطلبية",
  sharedTag: "للقسمة",
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

  offlineQueuedTitle: "ما فماش نات",
  offlineQueuedMessage: "الطلبية تسجلت في تليفونك وباش تتبعث وحدها كي ترجع النات.",
  retryNow: "عاود جرب دلوقتي",

  loyaltyToggle: "بطاقة الولاء (إختياري)",
  loyaltyPhoneLabel: "رقم التليفون",
  loyaltyPhonePlaceholder: "مثال : 20 123 456",
  loyaltyBirthDateLabel: "تاريخ الميلاد (إختياري، للتخفيض تاع عيد ميلادك)",
  loyaltyConsentNotice:
    "رقمك يخدم كان لبطاقة الولاء تاع هذا المطعم. عمرو ما يتشارك، عمرو ما يتستعمل باش يعيطولك، ويتمسح بعد 24 شهر بلا طلبية.",
  loyaltyPrivacyLink: "سياسة الخصوصية",
  loyaltyProgress: (count, remaining) => `عندك ${count} طلبية — باقي ${remaining} باش تربح حاجة فالمجان!`,
  loyaltyRewardAvailable: "🎉 عندك حاجة مربوحة! وريها للجرسون.",
  loyaltyBirthdayBanner: "عيد ميلاد سعيد! اطلب التخفيض الخاص من الجرسون.",

  pushSubscribeButton: "عرفني كي تكون لاهية",
  pushSubscribed: "باش تتعرف كي الطلبية تكون لاهية.",
  pushDenied: "الإشعارات موقوفة — نجم تفعّلها من إعدادات المتصفح إذا بدّلت رايك.",

  suggestionTitle: (name: string) => `مع « ${name} » ؟`,
  suggestionHint: "المطعم ينصحك بيه — تنجم تتجاوز.",
  suggestionAdd: "زيدها",
  suggestionDismiss: "لا شكرا",
  cartClearedNotice: "أكلة من القفة تاعك ماعادتش موجودة ونحاتلك. القفة تاعك دلوقتي فاضية.",

  shareOrderButton: "شارك الطلبية تاعك",
  shareCardTitle: (restaurantName) => `الماكلة تاعي عند ${restaurantName}`,
  shareCardText: "طلبت من Tawla 🍽️",
} satisfies Dictionary;
