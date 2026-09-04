import { describe, expect, it } from "vitest";
import { currentMarket, getMarket } from "./market";

describe("getMarket", () => {
  it("defaults to Tunisia when no NEXT_PUBLIC_MARKET is set", () => {
    expect(currentMarket.code).toBe("tn");
  });

  it("resolves the France market shape", () => {
    const fr = getMarket("fr");
    expect(fr.code).toBe("fr");
    expect(fr.currency).toEqual({ code: "EUR", symbol: "€", decimals: 2, decimalSeparator: "," });
  });

  it("keeps the Tunisia market shape unchanged", () => {
    const tn = getMarket("tn");
    expect(tn.currency).toEqual({ code: "TND", symbol: "DT", decimals: 3, decimalSeparator: "." });
  });

  it("is case-insensitive", () => {
    expect(getMarket("FR").code).toBe("fr");
  });

  it("throws on an unknown market code", () => {
    expect(() => getMarket("xx")).toThrow();
  });
});

describe("culturalFactsEnabled", () => {
  it("stays on for Tunisia — the kitchen-wait anecdotes are Tunisian content", () => {
    expect(getMarket("tn").culturalFactsEnabled).toBe(true);
  });

  it("is off for France — the content (couscous, harissa...) doesn't translate", () => {
    expect(getMarket("fr").culturalFactsEnabled).toBe(false);
  });
});

describe("menuCategories", () => {
  it("keeps Ftour for Tunisia, without any French-only category", () => {
    const tn = getMarket("tn");
    expect(tn.menuCategories).toContain("Ftour");
    expect(tn.menuCategories).not.toContain("Formules");
    expect(tn.menuCategories).not.toContain("Vins");
  });

  it("replaces Ftour with French menu categories for France", () => {
    const fr = getMarket("fr");
    expect(fr.menuCategories).not.toContain("Ftour");
    expect(fr.menuCategories).toEqual(
      expect.arrayContaining(["Entrées", "Plats", "Desserts", "Boissons", "Formules", "Vins", "À emporter", "Autre"])
    );
  });
});
