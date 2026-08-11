// Liste fermée proposée dans le formulaire du dashboard manager
// (frontend/app/dashboard/page.tsx) — la valeur stockée en base reste le
// libellé français ci-dessous (pas de migration de schéma), seul l'AFFICHAGE
// côté client change de langue. Un item déjà en base avec une autre valeur
// (donnée historique) s'affiche simplement tel quel, sans traduction.
export const MENU_CATEGORIES = ["Entrées", "Plats", "Desserts", "Boissons", "Ftour", "Autre"] as const;

type MenuCategory = (typeof MENU_CATEGORIES)[number];

const AR_LABELS: Record<MenuCategory, string> = {
  Entrées: "المقبلات",
  Plats: "الأطباق الرئيسية",
  Desserts: "الحلويات",
  Boissons: "المشروبات",
  Ftour: "الفطور",
  Autre: "أخرى",
};

export function menuCategoryLabel(category: string, locale: string): string {
  if (locale === "ar" && category in AR_LABELS) {
    return AR_LABELS[category as MenuCategory];
  }
  return category;
}
