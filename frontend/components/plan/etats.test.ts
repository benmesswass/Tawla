import { describe, expect, it } from "vitest";

import { construireEtats, SourceEtats } from "./etats";
import { ETAT_LIBRE } from "./types";

function source(overrides: Partial<SourceEtats> = {}): SourceEtats {
  return {
    tablesOccupees: new Set(),
    aPrendre: [],
    aServir: [],
    additions: [],
    appels: [],
    enCuisine: [],
    ...overrides,
  };
}

describe("construireEtats", () => {
  it("une table absente de toutes les listes est libre", () => {
    expect(construireEtats(source())[1]).toBeUndefined();
  });

  it("une table occupée sans rien d'autre en cours passe occupee, pas libre", () => {
    const etats = construireEtats(source({ tablesOccupees: new Set([1]) }));
    expect(etats[1].urgence).toBe("occupee");
  });

  it("une urgence réelle prend le pas sur la simple occupation", () => {
    const etats = construireEtats(
      source({
        tablesOccupees: new Set([1]),
        appels: [{ table_id: 1, depuis: "2026-09-09T10:00:00Z" }],
      })
    );
    expect(etats[1].urgence).toBe("appel");
  });

  it("l'occupation ne redescend jamais une urgence déjà posée, quel que soit l'ordre", () => {
    // enCuisine est traité après le seed d'occupation dans construireEtats :
    // il ne doit pas non plus faire redescendre une urgence plus haute.
    const etats = construireEtats(
      source({
        tablesOccupees: new Set([1]),
        enCuisine: [{ table_id: 1 }],
        appels: [{ table_id: 1, depuis: "2026-09-09T10:00:00Z" }],
      })
    );
    expect(etats[1].urgence).toBe("appel");
  });

  it("ETAT_LIBRE reste le repli explicite pour une table non occupée", () => {
    const etats = construireEtats(source());
    expect(etats[1] ?? ETAT_LIBRE).toEqual(ETAT_LIBRE);
  });
});
