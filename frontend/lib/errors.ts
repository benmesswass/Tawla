import { ApiError } from "./api";

// Traduction des codes d'erreur backend (voir lib/api.ts) — avant ce fichier,
// l'utilisateur voyait le message anglais brut renvoyé par FastAPI
// ("invalid table code", "'X' is no longer available"...).
const MESSAGES: Record<string, (ctx: Record<string, unknown>) => string> = {
  INVALID_TABLE_CODE: () =>
    "Ce QR code ne correspond à aucune table. Demandez à votre serveur de le vérifier.",
  TABLE_NOT_FOUND: () => "Cette table n'existe pas pour ce restaurant.",
  ITEM_UNAVAILABLE: (ctx) =>
    `« ${ctx.item_name} » vient d'être marqué indisponible et a été retiré de votre commande. Vous pouvez valider le reste.`,
  ITEM_NOT_FOUND: () => "Un article de votre commande n'existe plus. Le menu a été rechargé.",
  EMPTY_ORDER: () => "Ajoutez au moins un article avant de valider.",
  ORDER_NOT_FOUND: () => "Cette commande n'existe plus.",
  INVALID_TRANSITION: () => "Cette commande a déjà changé de statut. La page va se mettre à jour.",
  STAFF_NOT_FOUND: () => "Ce membre du personnel n'existe pas.",
  STAFF_WRONG_RESTAURANT: () => "Ce membre du personnel n'appartient pas à ce restaurant.",
  INVALID_CREDENTIALS: () => "E-mail ou mot de passe incorrect.",
  NOT_AUTHENTICATED: () => "Session expirée, merci de vous reconnecter.",
  INVALID_TOKEN: () => "Session expirée, merci de vous reconnecter.",
  FORBIDDEN: () => "Vous n'avez pas accès à cette action.",
  ALREADY_CLAIMED: () => "Cette commande vient d'être prise en charge par un collègue.",
  ALREADY_PAID: () => "Cette commande a déjà été payée.",
  ORDER_CANCELLED: () => "Cette commande a été annulée, le paiement n'est plus possible.",
  NO_PENDING_CASH_PAYMENT: () => "Aucune demande de paiement en espèces en attente pour cette commande.",
  ORDER_NOT_CONFIRMED: () =>
    "Cette commande doit d'abord être confirmée par un serveur avant de pouvoir être payée.",
  ORDER_NOT_MODIFIABLE: () =>
    "Le serveur vient de confirmer votre commande, elle ne peut plus être modifiée directement.",
  MODIFICATION_REQUEST_NOT_ALLOWED: () =>
    "Cette commande n'est plus dans un état où une demande de modification est possible.",
  MODIFICATION_REQUEST_ALREADY_PENDING: () =>
    "Une demande de modification est déjà en cours pour cette commande — attendez la réponse du serveur avant d'en envoyer une nouvelle.",
  NO_CHANGES_REQUESTED: () => "Vous n'avez rien changé à votre commande.",
  MODIFICATION_REQUEST_NOT_FOUND: () => "Cette demande de modification n'existe plus.",
  MODIFICATION_REQUEST_ALREADY_RESOLVED: () => "Cette demande de modification a déjà reçu une réponse.",
  INCOMPLETE_RESOLUTION: () => "Répondez à chaque ligne de la demande avant d'envoyer votre réponse.",
  EMAIL_EXISTS: () => "Un compte existe déjà avec cet e-mail.",
  ACCOUNT_DISABLED: () => "Ce compte a été désactivé. Demandez à votre manager de le réactiver.",
  CSV_UNREADABLE: () =>
    "Ce fichier n'a pas pu être lu. Vérifiez qu'il contient une ligne d'en-tête avec au moins les colonnes « nom » et « prix ».",
  INVALID_PERIOD: () => "La date de début doit précéder la date de fin.",
  LAST_ACTIVE_MANAGER: () =>
    "C'est le dernier compte manager actif : créez ou réactivez un autre manager avant de le modifier, sinon plus personne ne pourrait gérer l'établissement.",
  // Sans entrée dédiée, ce code retombait sur le message générique
  // « Réessayez dans un instant » (S-2c, audit 2026-08-18) — qui invite à
  // réessayer tout de suite alors que la fenêtre est d'une minute pleine :
  // le client refusé enchaînait les tentatives, ce qui prolongeait le blocage
  // au lieu de le laisser retomber.
  RATE_LIMITED: () => "Trop de tentatives. Patientez une minute avant de réessayer.",
  // Sans entrée dédiée, un manager qui clique sur une fonctionnalité d'un
  // palier supérieur lisait le même message générique qu'un vrai bug —
  // l'inverse de ce qu'une offre à trois paliers doit donner envie de faire
  // (offre à trois paliers, 2026-08-18).
  UPGRADE_REQUIRED: (ctx) => {
    const label = TIER_LABELS[ctx.required_tier as string] ?? String(ctx.required_tier);
    return `Cette fonctionnalité demande le palier ${label} ou plus.`;
  },
  // Réseaux sociaux + avis Google (settings/social-links) — le lien est
  // affiché en href brut sur le menu public, d'où le filtrage http(s) côté
  // backend (tenants/router.py::_clean_social_url).
  INVALID_SOCIAL_URL: (ctx) => {
    const label = SOCIAL_FIELD_LABELS[ctx.field as string] ?? "Ce lien";
    return `Le lien ${label} doit commencer par http:// ou https://.`;
  },
  SOCIAL_URL_TOO_LONG: (ctx) => {
    const label = SOCIAL_FIELD_LABELS[ctx.field as string] ?? "Ce lien";
    return `Le lien ${label} est trop long (300 caractères maximum).`;
  },
};

const TIER_LABELS: Record<string, string> = { essentiel: "Essentiel", pro: "Pro", business: "Business" };

const SOCIAL_FIELD_LABELS: Record<string, string> = {
  facebook_url: "Facebook",
  instagram_url: "Instagram",
  tiktok_url: "TikTok",
  whatsapp_url: "WhatsApp",
  google_review_url: "avis Google",
};

export function toFrenchMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const translate = MESSAGES[error.code];
    if (translate) return translate(error.context);
  }
  return "Une erreur est survenue. Réessayez dans un instant.";
}

/**
 * Palier requis si `error` est un refus `UPGRADE_REQUIRED`, sinon `null`.
 *
 * Sert à distinguer, à l'endroit où chaque action gérée par palier échoue,
 * le cas « proposer de passer au palier supérieur » d'une vraie erreur —
 * sans dupliquer cette logique à chaque site d'appel (paiement en ligne du
 * passage à un palier supérieur, 2026-08-19).
 */
export function requiredTierFromError(error: unknown): "pro" | "business" | null {
  if (error instanceof ApiError && error.code === "UPGRADE_REQUIRED") {
    const tier = error.context.required_tier;
    if (tier === "pro" || tier === "business") return tier;
  }
  return null;
}

// Sous-ensemble des codes rencontrés côté parcours client (page
// /menu/[qrToken]) — les codes staff-only (FORBIDDEN, INVALID_CREDENTIALS...)
// n'ont pas besoin d'arabe, ce parcours ne les déclenche jamais.
// Exportées uniquement pour le test de parité des clés ci-dessous
// (errors.test.ts) — la régression EN corrigée le 2026-09-04 (voir
// commentaire sur EN_MESSAGES) est exactement ce qu'un futur code ajouté à
// l'une sans l'autre reproduirait en silence.
export const AR_MESSAGES: Record<string, (ctx: Record<string, unknown>) => string> = {
  INVALID_TABLE_CODE: () => "هاذا الكود ما ينجمش يتعرف على حتى طاولة. إسأل الجرسون يتأكد منه.",
  TABLE_NOT_FOUND: () => "هاذي الطاولة ما موجودة ش في هاذا المطعم.",
  ITEM_UNAVAILABLE: (ctx) => `« ${ctx.item_name} » ولات ماشي متوفرة ونحيناها من الطلبية. تنجم تأكد الباقي.`,
  ITEM_NOT_FOUND: () => "شي أكلة في طلبيتك ما عادش موجودة. المينيو تعاود تحميله.",
  EMPTY_ORDER: () => "زيد على الأقل أكلة وحدة قبل ما تأكد.",
  ORDER_NOT_FOUND: () => "هاذي الطلبية ما عادتش موجودة.",
  INVALID_TRANSITION: () => "هاذي الطلبية تبدل حالتها. الصفحة باش تتجدد.",
  ALREADY_PAID: () => "هاذي الطلبية تخلصت من قبل.",
  ORDER_CANCELLED: () => "هاذي الطلبية تلغات، ما عادش ممكن تخلصها.",
  NO_PENDING_CASH_PAYMENT: () => "ما فماش طلب خلاص كاش قاعد ينتظر لهاذي الطلبية.",
  ORDER_NOT_CONFIRMED: () => "لازم الجرسون يأكد الطلبية قبل ما تنجم تخلصها.",
  ORDER_NOT_MODIFIABLE: () => "الجرسون تو أكد الطلبية، ما تنجمش تبدلها مباشرة.",
  MODIFICATION_REQUEST_NOT_ALLOWED: () => "هاذي الطلبية ما عادش ممكن تطلب فيها تبديل.",
  MODIFICATION_REQUEST_ALREADY_PENDING: () => "عندك طلب تبديل قاعد ينتظر لهاذي الطلبية — استنى جواب الجرسون قبل ما تبعث طلب آخر.",
  NO_CHANGES_REQUESTED: () => "ما بدلتش حتى حاجة في طلبيتك.",
  RATE_LIMITED: () => "طلبت برشا مرات. استنى دقيقة وعاود جرب.",
  // Rare côté client : seul le paiement carte peut déclencher ce code ici,
  // les autres fonctionnalités par palier sont toutes côté dashboard manager.
  UPGRADE_REQUIRED: () => "الخلاص بالكارط ماشي متوفر هنا. خلص كاش.",
};

// Même sous-ensemble qu'AR_MESSAGES ci-dessus (parcours client uniquement,
// France — MARCHE_FRANCE.md F5/A9). Régression trouvée en vérifiant A9 en
// conditions réelles (2026-09-04) : `toLocalizedMessage` ne connaissait que
// `locale === "ar"`, tout le reste (donc "en" aussi, dès qu'il a existé)
// retombait sur `toFrenchMessage` — un client anglophone voyait la carte et
// les boutons en anglais, mais toutes les erreurs API en français.
export const EN_MESSAGES: Record<string, (ctx: Record<string, unknown>) => string> = {
  INVALID_TABLE_CODE: () => "This QR code doesn't match any table. Ask your waiter to check it.",
  TABLE_NOT_FOUND: () => "This table doesn't exist for this restaurant.",
  ITEM_UNAVAILABLE: (ctx) =>
    `"${ctx.item_name}" was just marked unavailable and has been removed from your order. You can still place the rest.`,
  ITEM_NOT_FOUND: () => "An item in your order no longer exists. The menu has been reloaded.",
  EMPTY_ORDER: () => "Add at least one item before placing your order.",
  ORDER_NOT_FOUND: () => "This order no longer exists.",
  INVALID_TRANSITION: () => "This order's status has already changed. The page will update.",
  ALREADY_PAID: () => "This order has already been paid.",
  ORDER_CANCELLED: () => "This order has been cancelled, payment is no longer possible.",
  NO_PENDING_CASH_PAYMENT: () => "No pending cash payment for this order.",
  ORDER_NOT_CONFIRMED: () => "This order must be confirmed by a waiter before it can be paid.",
  ORDER_NOT_MODIFIABLE: () => "The waiter just confirmed your order, it can no longer be edited directly.",
  MODIFICATION_REQUEST_NOT_ALLOWED: () => "This order is no longer in a state where a change request is possible.",
  MODIFICATION_REQUEST_ALREADY_PENDING: () =>
    "A change request is already pending for this order — wait for the waiter's response before sending another one.",
  NO_CHANGES_REQUESTED: () => "You haven't changed anything in your order.",
  RATE_LIMITED: () => "Too many attempts. Wait a minute before trying again.",
  // Rare côté client : seul le paiement carte peut déclencher ce code ici,
  // les autres fonctionnalités par palier sont toutes côté dashboard manager.
  UPGRADE_REQUIRED: () => "Card payment isn't available here. Please pay in cash.",
};

export function toLocalizedMessage(error: unknown, locale: string): string {
  if (locale === "ar") {
    if (error instanceof ApiError) {
      const translate = AR_MESSAGES[error.code];
      if (translate) return translate(error.context);
    }
    return "صار خطأ. عاود جرب من بعد شوية.";
  }
  if (locale === "en") {
    if (error instanceof ApiError) {
      const translate = EN_MESSAGES[error.code];
      if (translate) return translate(error.context);
    }
    return "Something went wrong. Please try again in a moment.";
  }
  return toFrenchMessage(error);
}
