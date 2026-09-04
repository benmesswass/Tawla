"use client";

import { currentMarket } from "@/lib/market";

// Même vocabulaire fixe que ALLERGEN_CODES côté backend (menu/models.py, UE
// règlement 1169/2011) — une divergence romprait silencieusement la
// validation (422 sur un code que ce composant propose mais que l'API
// refuse). Coexiste avec le champ libre `allergens` de Draft, affiché à côté
// dans les deux formulaires.
const ALLERGEN_LABELS: Record<string, string> = {
  gluten: "Gluten",
  crustaceans: "Crustacés",
  eggs: "Œufs",
  fish: "Poisson",
  peanuts: "Arachides",
  soybeans: "Soja",
  milk: "Lait",
  nuts: "Fruits à coque",
  celery: "Céleri",
  mustard: "Moutarde",
  sesame: "Sésame",
  sulphites: "Sulfites",
  lupin: "Lupin",
  molluscs: "Mollusques",
};
export const ALLERGEN_CODES = Object.keys(ALLERGEN_LABELS);

// Mêmes clés que Market.vatRates (lib/market.ts) — jamais le taux lui-même en
// dur ici, seulement le libellé humain de la clé ; le taux affiché à côté de
// chaque option vient de currentMarket.vatRates au moment du rendu.
const VAT_CATEGORY_LABELS: Record<string, string> = {
  sur_place: "Sur place",
  a_emporter: "À emporter",
  alcool: "Alcool",
};

// Un simple Math.round() afficherait "6 %" pour le taux réel de 5,5 % (à
// emporter) — trompeur sur un chiffre à valeur légale. Une décimale suffit :
// aucun taux de `Market.vatRates` n'en a plus d'une.
function formatVatRate(rate: number): string {
  const percent = (rate * 100).toFixed(1).replace(/\.0$/, "");
  return percent.replace(".", currentMarket.currency.decimalSeparator);
}

/**
 * TVA (France uniquement — `currentMarket.vatRates` vaut `null` en Tunisie,
 * où le backend rejette toute valeur non nulle) et allergènes UE (les deux
 * marchés, le backend ne restreint pas ce champ par marché). Bloc partagé
 * entre le formulaire d'édition et celui de création d'un article : un
 * vocabulaire de 14 allergènes dupliqué à deux endroits finit par diverger
 * silencieusement.
 */
export default function ChampsVatAllergenes({
  vatCategory,
  allergenCodes,
  onVatCategoryChange,
  onAllergenCodesChange,
}: {
  vatCategory: string;
  allergenCodes: string[];
  onVatCategoryChange: (value: string) => void;
  onAllergenCodesChange: (codes: string[]) => void;
}) {
  const vatRates = currentMarket.vatRates;

  function toggleAllergen(code: string) {
    onAllergenCodesChange(
      allergenCodes.includes(code) ? allergenCodes.filter((c) => c !== code) : [...allergenCodes, code]
    );
  }

  return (
    <div className="mt-2 space-y-2">
      {vatRates && (
        <select
          value={vatCategory}
          onChange={(e) => onVatCategoryChange(e.target.value)}
          className="border rounded px-2 py-1 text-sm"
        >
          <option value="">TVA — Sur place par défaut</option>
          {Object.keys(vatRates).map((key) => (
            <option key={key} value={key}>
              {(VAT_CATEGORY_LABELS[key] ?? key) + ` (${formatVatRate(vatRates[key])} %)`}
            </option>
          ))}
        </select>
      )}
      <div className="flex flex-wrap gap-1.5">
        {ALLERGEN_CODES.map((code) => {
          const selected = allergenCodes.includes(code);
          return (
            <button
              key={code}
              type="button"
              onClick={() => toggleAllergen(code)}
              aria-pressed={selected}
              className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                selected
                  ? "bg-[var(--harissa)] text-white border-[var(--harissa)]"
                  : "border-[var(--line)] text-neutral-600 hover:bg-[var(--semoule)]"
              }`}
            >
              {ALLERGEN_LABELS[code]}
            </button>
          );
        })}
      </div>
    </div>
  );
}
