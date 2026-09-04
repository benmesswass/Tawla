import type { Dictionary } from "./fr";
import { formatAmount } from "@/lib/currency";

// Arabe tunisien (derja) en écriture arabe — registre familier et chaleureux,
// adapté à un parcours client de commande au restaurant. `satisfies Dictionary`
// force le compilateur à vérifier que toutes les clés de fr.ts existent ici.
export const ar = {
  locale: "ar",
  dir: "rtl",
  // Fixe (pas currentMarket.currency.symbol) : cette derja tunisienne ne sert
  // aujourd'hui que le marché tunisien. Le jour où le marché français a sa
  // propre variante arabe littéraire (§6 F1 de MARCHE_FRANCE.md), elle aura
  // son propre dictionnaire, pas ce symbole rendu dynamique ici.
  currency: "د.ت",

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

  modifyOrderButton: "بدّل الطلبية",
  modifyOrderHint: "تنجم تبدلها ما دام الجرسون ما أكدهاش",
  editOrderTitle: "بدّل الطلبية",
  editOrderSave: "سجل التبديلات",
  editOrderCancel: "الغي",
  itemsUpdatedAt: (heure) => `تبدلت الساعة ${heure}`,

  requestModificationButton: "اطلب تبديل",
  requestModificationHint: "لازم الجرسون يتأكد مع الكوجينة قبل أي تبديل",
  requestEditBanner: "هاذا الطلب لازم الجرسون يتأكد منه مع الكوجينة قبل ما يتطبق.",
  requestEditSend: "ابعث طلب التبديل",
  requestEditSubcopy: "الجرسون باش يتأكد مع الكوجينة قبل ما يطبق هاذم التبديلات.",
  requestEditNewTotalLabel: "المجموع الجديد إذا تقبل",
  requestEditCurrentTotal: (total) => `المجموع الحالي للطلبية : ${total}`,
  requestSentButton: "✓ الطلب تبعث",
  requestPendingBanner: "الطلب تبعث — قاعدين ننتظرو جواب الجرسون.",
  requestOutcomeTitle: "جواب الجرسون",
  requestLineAccepted: "تقبل",
  requestLineDeclined: "ترفض",
  requestOrderSeparately: "اطلبها وحدها",

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
    (tipAmount > 0 ? ` (فيها ${formatAmount(tipAmount)} د.ت إكرامية)` : ""),
  cashPendingMessage: (amount) => `طلبت تخلص كاش — جرسون باش يجي يقبض ${formatAmount(amount)} د.ت.`,
  cardTerminalPendingMessage: (amount) =>
    `طلبت تخلص بالكارت — جرسون باش يجي بالماكينة يقبض ${formatAmount(amount)} د.ت.`,
  tipLabel: "الإكرامية (إختياري، للخلاص بالكارت)",
  tipNone: "بلا",
  tipPlaceholder: `${formatAmount(0)} د.ت`,
  emailLabel: "الإيميل (إختياري، باش توصلك الفاتورة)",
  emailPlaceholder: "انت@مثال.com",
  payByCard: "خلص أونلاين",
  payByCardTerminal: "خلص بالكارت (الجرسون يجيب الماكينة)",
  payByCash: "خلص كاش (الجرسون باش يجي يقبض)",
  paymentFailedRetry: "الخلاص ما نجحش. تنجم تعاود تجرب.",
  invoiceDownload: "حمل الفاتورة (PDF)",
  invoiceQrCaption: "إسكانيها باش تلقاها في جهاز آخر",
  orderAgain: "أطلب مرة أخرى",
  postOrderSuggestionTitle: "حابب حاجة أخرى قبل الفاتورة؟",

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
  sharedPerPersonAmount: (amount) => `${formatAmount(amount)} د.ت للشخص`,
  dinersLabel: "قداش عباد عالطاولة",
  openOrdersTitle: (count, reste) =>
    count > 1
      ? `${count} طلبيات مازالوا — باقي ${formatAmount(reste)} د تتخلص`
      : `طلبية مازالت — باقي ${formatAmount(reste)} د تتخلص`,
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

  optionsChooseTitle: (name) => `اختار لـ « ${name} »`,
  optionsGroupHint: (min, max) => (min === max ? `اختار ${min}` : min === 0 ? `اختار حتى ${max}` : `اختار بين ${min} و ${max}`),
  optionsConfirmAdd: "زيد للقفة",
  optionsCancelChoice: "الغي",
  cartClearedNotice: "أكلة من القفة تاعك ماعادتش موجودة ونحاتلك. القفة تاعك دلوقتي فاضية.",

  shareOrderButton: "شارك الطلبية تاعك",
  shareCardTitle: (restaurantName) => `الماكلة تاعي عند ${restaurantName}`,
  shareCardText: "طلبت من Tawla 🍽️",

  googleReviewTitle: "عجبتكم الماكلة؟",
  googleReviewBody: (restaurantName) => `رأي في Google يعاون ${restaurantName} باش يتعرف عليه أكثر — ما ياخذش غير شوية وقت.`,
  googleReviewCta: "حط رأي في Google",
  googleReviewDismiss: "من بعد",
} satisfies Dictionary;
