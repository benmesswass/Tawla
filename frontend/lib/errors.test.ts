import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { AR_MESSAGES, EN_MESSAGES, toLocalizedMessage } from "./errors";

// Régression trouvée en vérifiant A9 (anglais côté client) en conditions
// réelles, 2026-09-04 : `toLocalizedMessage` ne savait router que "ar",
// tout le reste — donc "en" aussi, dès qu'il a existé — retombait sur le
// français. Un client anglophone voyait la carte et les boutons traduits,
// mais toute erreur API (paiement refusé, article indisponible...) en
// français. Un test par langue, pour que ça ne se reproduise jamais en
// silence à la prochaine langue ajoutée.
function orderNotConfirmedError(): ApiError {
  return new ApiError("ORDER_NOT_CONFIRMED", "order not confirmed", {});
}

describe("toLocalizedMessage", () => {
  it("routes to French for the fr locale", () => {
    expect(toLocalizedMessage(orderNotConfirmedError(), "fr")).toMatch(/confirmée par un serveur/);
  });

  it("routes to Arabic for the ar locale", () => {
    expect(toLocalizedMessage(orderNotConfirmedError(), "ar")).toMatch(/الجرسون/);
  });

  it("routes to English for the en locale (France, F5/A9)", () => {
    expect(toLocalizedMessage(orderNotConfirmedError(), "en")).toBe(
      "This order must be confirmed by a waiter before it can be paid."
    );
  });

  it("falls back to French for any other locale, never leaves the message untranslated", () => {
    expect(toLocalizedMessage(orderNotConfirmedError(), "xx")).toMatch(/confirmée par un serveur/);
  });

  it("returns a generic message per locale for an error with no dedicated translation", () => {
    const unknown = new ApiError("SOME_UNMAPPED_CODE", "boom", {});
    expect(toLocalizedMessage(unknown, "en")).toBe("Something went wrong. Please try again in a moment.");
    expect(toLocalizedMessage(unknown, "ar")).toBe("صار خطأ. عاود جرب من بعد شوية.");
    expect(toLocalizedMessage(unknown, "fr")).toBe("Une erreur est survenue. Réessayez dans un instant.");
  });

  it("keeps AR_MESSAGES and EN_MESSAGES in sync — same client-facing code subset", () => {
    // La régression EN corrigée le 2026-09-04 était exactement ça : un code
    // ajouté à AR_MESSAGES (ou l'inverse) sans son pendant dans l'autre
    // langue retombe en silence sur le message générique de CETTE langue,
    // jamais sur une erreur visible en dev. Ce test échoue fort à la
    // prochaine divergence au lieu d'attendre une vérification manuelle.
    expect(Object.keys(EN_MESSAGES).sort()).toEqual(Object.keys(AR_MESSAGES).sort());
  });
});
