import { describe, expect, it } from "vitest";
import { localeSwitchLabel, nextLocaleOf } from "./useLocale";

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

// Avant A9bis, ce libellé était codé en dur dans CHAQUE dictionnaire
// (fr.ts/en.ts/ar.ts) — `currentMarket.languages.includes("en") ? "English"
// : "عربي"` côté fr.ts — correct uniquement parce qu'aucun marché n'a
// jamais eu plus de deux langues. `localeSwitchLabel` dérive le libellé de
// `nextLocaleOf`, la même source de vérité pour les deux marchés, plutôt que
// son propre calcul par dictionnaire.
describe("localeSwitchLabel", () => {
  it("shows the language name of the target locale, not the current one", () => {
    const tn = ["fr", "ar"];
    expect(localeSwitchLabel("fr", tn)).toBe("عربي");
    expect(localeSwitchLabel("ar", tn)).toBe("Français");
  });

  it("works the same way on the France language pair (F5/A9)", () => {
    const fr = ["fr", "en"];
    expect(localeSwitchLabel("fr", fr)).toBe("English");
    expect(localeSwitchLabel("en", fr)).toBe("Français");
  });
});
