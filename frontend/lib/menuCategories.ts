import { currentMarket } from "@/lib/market";

// Liste fermée proposée dans le formulaire du dashboard manager
// (frontend/app/dashboard/page.tsx) — la valeur stockée en base reste le
// libellé français ci-dessous (pas de migration de schéma), seul l'AFFICHAGE
// côté client change de langue. Un item déjà en base avec une autre valeur
// (donnée historique) s'affiche simplement tel quel, sans traduction.
const CATEGORIES_TN = ["Entrées", "Plats", "Desserts", "Boissons", "Ftour", "Autre"] as const;
// F5 (MARCHE_FRANCE.md §3.2, Annexe A) : « Ftour » n'a aucun sens hors
// Ramadan tunisien ; « Vins » n'existe pas côté carte tunisienne. Les
// formules (entrée + plat + dessert) sont un modèle séparé depuis F5-A3,
// pas une catégorie d'article — pas de doublon à ajouter ici.
const CATEGORIES_FR = ["Entrées", "Plats", "Desserts", "Boissons", "Vins", "Autre"] as const;

export function menuCategories(): readonly string[] {
  return currentMarket().code === "fr" ? CATEGORIES_FR : CATEGORIES_TN;
}

type MenuCategory = (typeof CATEGORIES_TN)[number] | (typeof CATEGORIES_FR)[number];

// L'arabe ne se charge que sous le marché tunisien (voir lib/i18n/ar.ts) :
// "Vins", propre au marché français, n'a donc jamais besoin d'y figurer.
const AR_LABELS: Partial<Record<MenuCategory, string>> = {
  Entrées: "المقبلات",
  Plats: "الأطباق الرئيسية",
  Desserts: "الحلويات",
  Boissons: "المشروبات",
  Ftour: "الفطور",
  Autre: "أخرى",
};

export function menuCategoryLabel(category: string, locale: string): string {
  if (locale === "ar") {
    return AR_LABELS[category as MenuCategory] ?? category;
  }
  return category;
}
