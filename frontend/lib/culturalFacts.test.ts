import { describe, expect, it } from "vitest";
import { culturalFactsFor } from "./culturalFacts";

describe("culturalFactsFor — Tunisia", () => {
  it("returns the French list for locale fr", () => {
    const facts = culturalFactsFor("fr", false, "tn");
    expect(facts.length).toBeGreaterThan(0);
    expect(facts[0]).toContain("couscous");
  });

  it("returns the Arabic list for locale ar", () => {
    const facts = culturalFactsFor("ar", false, "tn");
    expect(facts.length).toBeGreaterThan(0);
  });

  it("falls back to French for any other locale (e.g. en, not spoken in Tunisia)", () => {
    expect(culturalFactsFor("en", false, "tn")).toEqual(culturalFactsFor("fr", false, "tn"));
  });

  it("ignores isCafeMode — Tunisia doesn't split content by establishment type", () => {
    expect(culturalFactsFor("fr", true, "tn")).toEqual(culturalFactsFor("fr", false, "tn"));
  });
});

describe("culturalFactsFor — France", () => {
  it("returns restaurant-specific French content when isCafeMode is false", () => {
    const facts = culturalFactsFor("fr", false, "fr");
    expect(facts.length).toBeGreaterThan(0);
    // Contenu propre à la France, jamais une trace du contenu tunisien.
    expect(facts.join(" ")).not.toContain("couscous");
  });

  it("returns café-specific French content when isCafeMode is true", () => {
    const facts = culturalFactsFor("fr", true, "fr");
    expect(facts.length).toBeGreaterThan(0);
  });

  it("returns a genuinely different set for restaurant vs café mode", () => {
    expect(culturalFactsFor("fr", false, "fr")).not.toEqual(culturalFactsFor("fr", true, "fr"));
  });

  it("returns English content for locale en, mirroring the French set length", () => {
    const fr = culturalFactsFor("fr", false, "fr");
    const en = culturalFactsFor("en", false, "fr");
    expect(en.length).toBe(fr.length);
    expect(en[0]).not.toBe(fr[0]);
  });

  it("also translates the café set to English", () => {
    const fr = culturalFactsFor("fr", true, "fr");
    const en = culturalFactsFor("en", true, "fr");
    expect(en.length).toBe(fr.length);
  });

  it("falls back to French for any other locale (e.g. ar, not offered in France)", () => {
    expect(culturalFactsFor("ar", false, "fr")).toEqual(culturalFactsFor("fr", false, "fr"));
  });
});
