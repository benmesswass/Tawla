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

  ramadanBannerPrefix: "رمضان مبارك",
  ramadanBannerRest: (time) =>
    ` — الفطور على الساعة ${time}. تنجم تطلب دلوقتي للفطور، الأكلة تكون لاهية وقتها.`,
  addToCartAria: (name) => `زيد ${name} للقفة`,
  removeFromCartAria: (name) => `نقّص ${name} من القفة`,
  allergensLabel: (allergens) => `مسببات الحساسية: ${allergens}`,
  notHalalBadge: "مش حلال",
  vegetarianBadge: "نباتي",
  veganBadge: "فيغان",
  glutenFreeBadge: "خالي من الغلوتين",
  formulasSectionTitle: "الفورمولات",
  callWaiterButton: "نادي على الجرسون",
  callWaiterSent: "✓ الجرسون تعرّف، باش يجي دلوقتي",
  notePlaceholder: "ملاحظة للكوجينة (إختياري، مثال: بلا بصل)",
  sharedCheckboxLabel: "أكلة نتقاسموها في الطاولة الكل",
  preorderCheckboxLabel: (time) => `نطلب للفطور (${time}) بدل دلوقتي`,
  sending: "قاعد يتبعث...",
  validateOrder: "أكد الطلبية",
  cartItemsCount: (n) => `${n} حاجة`,

  orderCancelledTitle: "الطلبية تلغات",
  orderSentTitle: "الطلبية تبعثت 🎉",
  orderSubtitle: (tableLabel, orderId) => `${tableLabel} — الطلبية رقم ${orderId}`,
  preorderBadge: (time) => `طلبية مسبقة للفطور — التحضير مبرمج للساعة ${time}.`,
  dedicatedServer: (staffName) => `${staffName} باش يكون الجرسون تاعك لهاذي الطلبية.`,

  trackingSteps: {
    received: "تبعثت",
    confirmed: "تأكدت من الجرسون",
    in_kitchen: "فالكوجينة",
    ready: "لاهية",
    served: "تقدمت",
  },
  kitchenWaitHint: "عادة من 10 إلى 20 دقيقة، يتبدل حسب الزحمة.",

  orderDetailsTitle: "تفاصيل الطلبية",
  sharedTag: "للقسمة",
  total: "المجموع",

  paymentTitle: "الخلاص",
  paidMessage: (method, tipAmount) =>
    `الخلاص تم ✓ ${method === "cash" ? "كاش" : "بالكارت"}` +
    (tipAmount > 0 ? ` (فيها ${tipAmount.toFixed(3)} د.ت إكرامية)` : ""),
  cashPendingMessage: (amount) => `طلبت تخلص كاش — جرسون باش يجي يقبض ${amount.toFixed(3)} د.ت.`,
  cardTerminalPendingMessage: (amount) =>
    `طلبت تخلص بالكارت — جرسون باش يجي بالماكينة يقبض ${amount.toFixed(3)} د.ت.`,
  tipLabel: "الإكرامية (إختياري، للخلاص بالكارت)",
  tipNone: "بلا",
  tipPlaceholder: "0.00 د.ت",
  emailLabel: "الإيميل (إختياري، باش توصلك الفاتورة)",
  emailPlaceholder: "انت@مثال.com",
  payByCard: "خلص أونلاين",
  payByCardUnavailable: "الخلاص أونلاين — قريبًا",
  payByCardTerminal: "خلص بالكارت (الجرسون يجيب الماكينة)",
  payByCash: "خلص كاش (الجرسون باش يجي يقبض)",
  paymentFailedRetry: "الخلاص ما نجحش. تنجم تعاود تجرب.",
  invoiceDownload: "حمل الفاتورة (PDF)",
  invoiceQrCaption: "إسكانيها باش تلقاها في جهاز آخر",
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
  offlineRetryCountdown: (seconds) => `عاود المحاولة من بعد ${seconds} ثواني…`,
  retryNow: "عاود جرب دلوقتي",

  loyaltyToggle: "بطاقة الولاء (إختياري)",
  loyaltyCardTitle: "بطاقة الولاء",
  loyaltyCompleteTitle: "بطاقة كاملة",
  loyaltyPhoneLabel: "رقم التليفون",
  loyaltyPhonePlaceholder: "مثال : 20 123 456",
  loyaltyBirthDateLabel: "تاريخ الميلاد (إختياري، للتخفيض تاع عيد ميلادك)",
  loyaltyConsentNotice:
    "رقمك يخدم كان لبطاقة الولاء تاع هذا المطعم. عمرو ما يتشارك، عمرو ما يتستعمل باش يعيطولك، ويتمسح بعد 24 شهر بلا طلبية.",
  loyaltyPrivacyLink: "سياسة الخصوصية",
  loyaltyProgress: (count, remaining) => `عندك ${count} طلبية — باقي ${remaining} باش تربح حاجة فالمجان!`,
  itemOutOfStock: "ما فماش توّا",
  orderElapsed: (duree) => `تبعثت من ${duree}`,
  tableTotalTitle: "شنوة تسال الطاولة تاعك بالكل",
  orderLabel: (id) => `طلبية #${id}`,
  thisOrder: "هاذي",
  tableTotal: "المجموع إلي يتخلص",
  tableTotalNote:
    "الخلاص إلي تحت يخلص كان الطلبية المعروضة. ارجع للأخرين باش تخلصهم، ولا اطلب من الجرسون يخلصهم الكل مرة وحدة.",
  sharedWithLabel: "مقسوم بين :",
  sharedWithEveryone: "ما اخترت حتى واحد : مقسوم على الطاولة الكل.",
  sharedPerPersonAmount: (amount) => `${amount.toFixed(3)} د.ت للشخص`,
  dinersLabel: "قداش عباد عالطاولة",
  openOrdersTitle: (count, reste) =>
    count > 1
      ? `${count} طلبيات مازالوا — باقي ${reste.toFixed(3)} د تتخلص`
      : `طلبية مازالت — باقي ${reste.toFixed(3)} د تتخلص`,
  openOrderLine: (id, lines) => `طلبية #${id} — ${lines} حاجة`,
  loyaltyFirstVisit: "أول مرة — بطاقتك تبدا مع هذي الطلبية.",
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

  googleReviewPromptTitle: "عجبتك الماكلة؟",
  googleReviewPromptButton: "حط رأيك في Google",
} satisfies Dictionary;
