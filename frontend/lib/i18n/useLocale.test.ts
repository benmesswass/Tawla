import { describe, expect, it } from "vitest";
import { nextLocaleOf } from "./useLocale";

// `nextLocaleOf` prend en second paramètre une liste explicite plutôt que de
// dépendre implicitement du marché du process (comme `AVAILABLE_LOCALES`,
// figé une fois pour toutes à `NEXT_PUBLIC_MARKET` chargé) — c'est ce qui
// rend les deux formes réellement testables ici, TN et FR, dans le même
// process de test (voir market.test.ts::getMarket pour le même principe).
describe("nextLocaleOf", () => {
  it("cycles fr -> ar -> fr on the Tunisia language pair", () => {
    const tn = ["fr", "ar"];
    expect(nextLocaleOf("fr", tn)).toBe("ar");
    expect(nextLocaleOf("ar", tn)).toBe("fr");
  });

  it("cycles fr -> en -> fr on the France language pair (F5/A9)", () => {
    // Régression réelle : avant A9, le marché français continuait à
    // proposer l'arabe tunisien (derja) au bascule — jamais l'anglais —
    // parce que le dictionnaire était codé en dur (`{ fr, ar }`), sans lien
    // avec `Market.languages`.
    const fr = ["fr", "en"];
    expect(nextLocaleOf("fr", fr)).toBe("en");
    expect(nextLocaleOf("en", fr)).toBe("fr");
  });

  it("falls back to the first locale when the current one is unknown", () => {
    expect(nextLocaleOf("xx", ["fr", "en"])).toBe("fr");
  });
});
