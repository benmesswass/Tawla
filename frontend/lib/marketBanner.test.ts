import { describe, expect, it } from "vitest";
import { selecteurAutorise } from "./marketBanner";

describe("selecteurAutorise", () => {
  it("interdit tout ce qui touche le parcours client (/menu)", () => {
    expect(selecteurAutorise("/menu")).toBe(false);
    expect(selecteurAutorise("/menu/abc123")).toBe(false);
    expect(selecteurAutorise("/menu/abc123?visite=1")).toBe(false);
  });

  it("interdit aussi le hub lui-même (redondant avec son propre choix)", () => {
    expect(selecteurAutorise("/choisir-pays")).toBe(false);
  });

  it("autorise le reste du site", () => {
    expect(selecteurAutorise("/")).toBe(true);
    expect(selecteurAutorise("/dashboard")).toBe(true);
    expect(selecteurAutorise("/menu-du-jour")).toBe(true); // ne doit pas matcher par préfixe hors "/menu/"
    expect(selecteurAutorise("/choisir-pays-vraiment")).toBe(true); // égalité stricte, pas un préfixe
  });
});
