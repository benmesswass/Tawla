import { describe, expect, it } from "vitest";
import { ETAPES } from "./etapes";
import { currentMarket } from "@/lib/market";

// `ETAPES` est un tableau figé au chargement du module — construit avec
// `currentMarket` résolu une fois, comme `core/markets.py::current_market`
// côté backend. Ces tests vérifient donc un invariant (le prix affiché suit
// toujours la couche marché, jamais une valeur recopiée à la main), pas
// littéralement les deux marchés dans le même run : ils passent aussi bien
// sous `NEXT_PUBLIC_MARKET=tn` (défaut ici) que `=fr`, sans modification.

describe("visite guidée — exactitude par marché", () => {
  it("n'affiche jamais un prix de palier resté en dur (étape 8)", () => {
    const essentiel = ETAPES.find((e) => e.id === "tarif-essentiel")!;
    const pro = ETAPES.find((e) => e.id === "tarif-pro")!;
    const business = ETAPES.find((e) => e.id === "tarif-business")!;

    expect(essentiel.titre).toContain(`${currentMarket.tierPrices.essentiel} ${currentMarket.currency.symbol}`);
    expect(pro.titre).toContain(`${currentMarket.tierPrices.pro} ${currentMarket.currency.symbol}`);
    expect(business.titre).toContain(`${currentMarket.tierPrices.business} ${currentMarket.currency.symbol}`);
  });

  it("ne promet l'arabe côté client que si le marché l'offre réellement", () => {
    const clientCarte = ETAPES.find((e) => e.id === "client-carte")!;
    expect(clientCarte.corps.includes("en arabe")).toBe(currentMarket.languages.includes("ar"));
  });
});
