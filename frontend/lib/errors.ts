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
};

export function toFrenchMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const translate = MESSAGES[error.code];
    if (translate) return translate(error.context);
  }
  return "Une erreur est survenue. Réessayez dans un instant.";
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
};

export function toLocalizedMessage(error: unknown, locale: string): string {
  if (locale !== "ar") return toFrenchMessage(error);
  if (error instanceof ApiError) {
    const translate = AR_MESSAGES[error.code];
    if (translate) return translate(error.context);
  }
  return "صار خطأ. عاود جرب من بعد شوية.";
}
