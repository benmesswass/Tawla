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
};

export function toFrenchMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const translate = MESSAGES[error.code];
    if (translate) return translate(error.context);
  }
  return "Une erreur est survenue. Réessayez dans un instant.";
}
