// Les 14 catégories d'allergènes du règlement européen INCO (UE 1169/2011,
// annexe II) — obligatoires en France (F5-A6, MARCHE_FRANCE.md §3.2 A6).
//
// Liste fermée côté client seulement, comme `menuCategories.ts` : la colonne
// `MenuItem.allergen_codes` reste une chaîne libre côté base (codes séparés
// par une virgule), pas un enum SQL — un nouvel allergène réglementaire
// n'exigerait qu'une entrée ici, jamais une migration.
export const INCO_ALLERGEN_CODES = [
  "gluten",
  "crustaceans",
  "eggs",
  "fish",
  "peanuts",
  "soybeans",
  "milk",
  "nuts",
  "celery",
  "mustard",
  "sesame",
  "sulphites",
  "lupin",
  "molluscs",
] as const;

export type AllergenCode = (typeof INCO_ALLERGEN_CODES)[number];

const LABELS_FR: Record<AllergenCode, string> = {
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

const LABELS_EN: Record<AllergenCode, string> = {
  gluten: "Gluten",
  crustaceans: "Crustaceans",
  eggs: "Eggs",
  fish: "Fish",
  peanuts: "Peanuts",
  soybeans: "Soybeans",
  milk: "Milk",
  nuts: "Tree nuts",
  celery: "Celery",
  mustard: "Mustard",
  sesame: "Sesame",
  sulphites: "Sulphites",
  lupin: "Lupin",
  molluscs: "Molluscs",
};

export function allergenLabel(code: string, locale: string): string {
  const key = code as AllergenCode;
  if (locale === "en" && key in LABELS_EN) return LABELS_EN[key];
  if (key in LABELS_FR) return LABELS_FR[key];
  return code;
}

/** "gluten,eggs,milk" -> ["gluten", "eggs", "milk"], entrées inconnues filtrées. */
export function parseAllergenCodes(value: string | null | undefined): AllergenCode[] {
  if (!value) return [];
  const known = new Set<string>(INCO_ALLERGEN_CODES);
  return value
    .split(",")
    .map((code) => code.trim())
    .filter((code): code is AllergenCode => known.has(code));
}

export function formatAllergenCodes(codes: string[]): string {
  return codes.join(",");
}
