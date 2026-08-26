import { describe, expect, it } from "vitest";
import { selecteurAutorise } from "./marketBanner";

describe("selecteurAutorise", () => {
  it("interdit tout ce qui touche le parcours client (/menu)", () => {
    expect(selecteurAutorise("/menu")).toBe(false);
    expect(selecteurAutorise("/menu/abc123")).toBe(false);
    expect(selecteurAutorise("/menu/abc123?visite=1")).toBe(false);
  });

  it("autorise le reste du site", () => {
    expect(selecteurAutorise("/")).toBe(true);
    expect(selecteurAutorise("/dashboard")).toBe(true);
    expect(selecteurAutorise("/choisir-pays")).toBe(true);
    expect(selecteurAutorise("/menu-du-jour")).toBe(true); // ne doit pas matcher par préfixe hors "/menu/"
  });
});
