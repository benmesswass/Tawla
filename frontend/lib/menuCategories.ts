// Liste fermée proposée dans le formulaire du dashboard manager
// (frontend/app/dashboard/page.tsx) — la valeur stockée en base reste le
// libellé français ci-dessous (pas de migration de schéma), seul l'AFFICHAGE
// côté client change de langue. Un item déjà en base avec une autre valeur
// (donnée historique, ou catégorie d'un autre marché après bascule) s'affiche
// simplement tel quel, sans traduction.
//
// La liste elle-même vit dans la couche marché (lib/market.ts::currentMarket
// .menuCategories, France, phase F3) — ce fichier ne fait plus que la
// traduction arabe, commune aux deux marchés.
const AR_LABELS: Record<string, string> = {
  Entrées: "المقبلات",
  Plats: "الأطباق الرئيسية",
  Desserts: "الحلويات",
  Boissons: "المشروبات",
  Ftour: "الفطور",
  Formules: "الوجبات المقترحة",
  Vins: "النبيذ",
  "À emporter": "طلبات خارجية",
  Autre: "أخرى",
};

export function menuCategoryLabel(category: string, locale: string): string {
  if (locale === "ar" && category in AR_LABELS) {
    return AR_LABELS[category];
  }
  return category;
}
