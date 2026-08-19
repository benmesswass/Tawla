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
};

const TIER_LABELS: Record<string, string> = { essentiel: "Essentiel", pro: "Pro", business: "Business" };

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
const AR_MESSAGES: Record<string, (ctx: Record<string, unknown>) => string> = {
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
  RATE_LIMITED: () => "طلبت برشا مرات. استنى دقيقة وعاود جرب.",
  // Rare côté client : seul le paiement carte peut déclencher ce code ici,
  // les autres fonctionnalités par palier sont toutes côté dashboard manager.
  UPGRADE_REQUIRED: () => "الخلاص بالكارط ماشي متوفر هنا. خلص كاش.",
};

export function toLocalizedMessage(error: unknown, locale: string): string {
  if (locale !== "ar") return toFrenchMessage(error);
  if (error instanceof ApiError) {
    const translate = AR_MESSAGES[error.code];
    if (translate) return translate(error.context);
  }
  return "صار خطأ. عاود جرب من بعد شوية.";
}
