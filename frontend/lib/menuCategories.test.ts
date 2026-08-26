import { describe, expect, it } from "vitest";
import { menuCategoryLabel } from "./menuCategories";
import { getMarket } from "./market";

describe("menuCategoryLabel", () => {
  it("returns the category unchanged in French", () => {
    expect(menuCategoryLabel("Plats", "fr")).toBe("Plats");
  });

  it("translates every Tunisia category to Arabic", () => {
    for (const category of getMarket("tn").menuCategories) {
      expect(menuCategoryLabel(category, "ar")).not.toBe(category);
    }
  });

  it("translates every France category to Arabic", () => {
    for (const category of getMarket("fr").menuCategories) {
      expect(menuCategoryLabel(category, "ar")).not.toBe(category);
    }
  });

  it("falls back to the raw value for a historical category outside the closed list", () => {
    expect(menuCategoryLabel("Menu enfant", "ar")).toBe("Menu enfant");
  });
});
