import { describe, expect, it } from "vitest";

import { construireEtats, construireReglements } from "./etats";

/**
 * Le règlement est un SECOND canal, jamais une urgence de plus.
 *
 * L'invariant tenu ici est celui qui coûterait le plus cher à casser : une
 * table qui a payé et qui appelle doit continuer d'afficher son appel. Ranger
 * « réglée » dans `URGENCES` aurait suffi à faire disparaître l'appel, puisque
 * la tuile ne montre que son état le plus urgent.
 */

function reglement(overrides: Partial<Parameters<typeof construireReglements>[0][number]> = {}) {
  return { table_id: 1, amount_paid: 0, fully_paid: false, ...overrides };
}

describe("construireReglements", () => {
  it("une table sans règlement connu n'a pas de marque", () => {
    expect(construireReglements([])[1]).toBeUndefined();
  });

  it("une table entièrement réglée porte la marque totale", () => {
    const marques = construireReglements([reglement({ amount_paid: 84, fully_paid: true })]);
    expect(marques[1]).toBe("total");
  });

  it("une table qui a réglé une partie porte la marque partielle", () => {
    const marques = construireReglements([reglement({ amount_paid: 42 })]);
    expect(marques[1]).toBe("partiel");
  });

  it("une table qui n'a encore rien réglé ne porte aucune marque", () => {
    const marques = construireReglements([reglement()]);
    expect(marques[1]).toBe("aucun");
  });

  it("chaque table garde sa propre marque", () => {
    const marques = construireReglements([
      reglement({ table_id: 3, amount_paid: 84, fully_paid: true }),
      reglement({ table_id: 5, amount_paid: 20 }),
    ]);
    expect(marques[3]).toBe("total");
    expect(marques[5]).toBe("partiel");
  });

  it("une table réglée qui appelle affiche l'appel, pas le règlement", () => {
    const etats = construireEtats({
      tablesOccupees: new Set([7]),
      aPrendre: [],
      aServir: [],
      additions: [],
      appels: [{ table_id: 7, depuis: "2026-09-10T19:00:00Z" }],
      enCuisine: [],
    });
    const marques = construireReglements([reglement({ table_id: 7, amount_paid: 84, fully_paid: true })]);

    // Les deux canaux coexistent : la couleur dit ce que la table attend, la
    // pastille dit qu'il n'y a plus rien à encaisser.
    expect(etats[7].urgence).toBe("appel");
    expect(marques[7]).toBe("total");
  });
});
