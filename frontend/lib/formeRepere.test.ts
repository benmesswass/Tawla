import { describe, expect, it } from "vitest";

import {
  Troncon,
  boiteEnglobante,
  contourUnion,
  tronconLePlusGrand,
  tronconSuivant,
  tronconVise,
} from "./formeRepere";

/** Le nombre de sommets d'un contour — c'est lui qui dit la forme : 4 pour un
 *  rectangle, 6 pour un L, 8 pour un U. */
function sommets(d: string): number {
  return d.split(/[ML]/).filter((m) => m.trim() && m.trim() !== "Z").length;
}

const BARRE: Troncon = { pos_x: 8, pos_y: 8, width: 36, height: 6 };
/** Le bras qui descend au bout droit de BARRE, chevauchant le coin. */
const BRAS: Troncon = { pos_x: 38, pos_y: 8, width: 6, height: 28 };
/** Le retour sous BARRE, qui referme le U. */
const RETOUR: Troncon = { pos_x: 8, pos_y: 30, width: 36, height: 6 };

describe("boiteEnglobante", () => {
  it("tient tout le comptoir, pas seulement son premier tronçon", () => {
    expect(boiteEnglobante([BARRE, BRAS])).toEqual({ left: 8, top: 8, width: 36, height: 28 });
  });
});

describe("contourUnion", () => {
  it("dessine un rectangle en quatre sommets", () => {
    expect(sommets(contourUnion([BARRE]))).toBe(4);
  });

  it("dessine un L en six sommets, sans couture au pli", () => {
    expect(sommets(contourUnion([BARRE, BRAS]))).toBe(6);
  });

  it("dessine un U en huit sommets", () => {
    expect(sommets(contourUnion([BARRE, BRAS, RETOUR]))).toBe(8);
  });

  it("soude deux tronçons bout à bout en un seul rectangle", () => {
    const gauche: Troncon = { pos_x: 10, pos_y: 10, width: 20, height: 6 };
    const droite: Troncon = { pos_x: 30, pos_y: 10, width: 20, height: 6 };

    // Un seul chemin, quatre sommets : la jonction ne laisse ni sommet inutile
    // ni trait au milieu du comptoir.
    expect(contourUnion([gauche, droite]).match(/M/g)).toHaveLength(1);
    expect(sommets(contourUnion([gauche, droite]))).toBe(4);
  });

  it("ne double pas les bords là où deux tronçons se chevauchent", () => {
    const a: Troncon = { pos_x: 10, pos_y: 10, width: 20, height: 6 };
    const b: Troncon = { pos_x: 20, pos_y: 10, width: 20, height: 6 };

    expect(sommets(contourUnion([a, b]))).toBe(4);
  });

  it("rend deux boucles quand un tronçon a été détaché des autres", () => {
    const isole: Troncon = { pos_x: 70, pos_y: 70, width: 10, height: 6 };

    expect(contourUnion([BARRE, isole]).match(/M/g)).toHaveLength(2);
  });
});

describe("tronconLePlusGrand", () => {
  it("désigne le tronçon qui portera l'étiquette, pas le premier posé", () => {
    expect(tronconLePlusGrand([{ pos_x: 0, pos_y: 0, width: 4, height: 4 }, BARRE])).toBe(1);
  });
});

describe("tronconVise", () => {
  it("suit le dernier appui", () => {
    expect(tronconVise([BARRE, BRAS], 1)).toBe(1);
  });

  it("retombe sur le plus large quand rien n'a été touché", () => {
    expect(tronconVise([{ pos_x: 0, pos_y: 0, width: 4, height: 4 }, BARRE], null)).toBe(1);
  });

  it("retombe sur le plus large quand le tronçon visé a été retiré", () => {
    expect(tronconVise([BARRE], 2)).toBe(0);
  });
});

describe("tronconSuivant", () => {
  const bornes = { longueur: 20, min: 2, max: 90 };

  it("replie un comptoir posé en haut vers la salle, pas vers le mur", () => {
    const suivant = tronconSuivant([BARRE], 0, bornes);

    expect(suivant.pos_y).toBe(BARRE.pos_y);
    expect(suivant.height).toBeGreaterThan(BARRE.height);
    expect(suivant.width).toBe(BARRE.height);
  });

  it("part de l'extrémité la plus éloignée du reste du comptoir", () => {
    // BARRE est seule : le repli s'accroche au bout le plus loin du centre du
    // plan, donc à gauche.
    expect(tronconSuivant([BARRE], 0, bornes).pos_x).toBe(BARRE.pos_x);
  });

  it("referme un L en U — le troisième tronçon revient vers les deux autres", () => {
    const suivant = tronconSuivant([BARRE, BRAS], 1, bornes);

    // Perpendiculaire au bras vertical, accroché à son bout bas, et tourné
    // vers BARRE (donc vers la gauche) : c'est un U, sans rien à choisir.
    expect(suivant.height).toBe(BRAS.width);
    expect(suivant.pos_y + suivant.height).toBe(BRAS.pos_y + BRAS.height);
    expect(suivant.pos_x).toBeLessThan(BRAS.pos_x);
  });

  it("ne fait jamais sortir un tronçon du plan", () => {
    const contreLeMur: Troncon = { pos_x: 88, pos_y: 8, width: 10, height: 6 };
    const suivant = tronconSuivant([contreLeMur], 0, { longueur: 60, min: 2, max: 90 });

    expect(suivant.pos_x).toBeGreaterThanOrEqual(0);
    expect(suivant.pos_y).toBeGreaterThanOrEqual(0);
    expect(suivant.pos_x + suivant.width).toBeLessThanOrEqual(100);
    expect(suivant.pos_y + suivant.height).toBeLessThanOrEqual(100);
  });
});
