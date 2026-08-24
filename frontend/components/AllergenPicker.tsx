import { AllergenCode, INCO_ALLERGEN_CODES, allergenLabel } from "@/lib/allergens";

/**
 * Les 14 allergènes INCO (F5-A6, MARCHE_FRANCE.md) + les trois marqueurs
 * positifs — même formulaire pour la création et l'édition d'un article
 * (`app/dashboard/page.tsx`), pour ne pas dupliquer dix-sept cases à cocher.
 * Toujours affiché en français dans le dashboard, comme le reste du
 * back-office (voir fr.ts) — seul le parcours client traduit.
 */
export default function AllergenPicker({
  selectedCodes,
  onToggleCode,
  isVegetarian,
  isVegan,
  isGlutenFree,
  onChangeVegetarian,
  onChangeVegan,
  onChangeGlutenFree,
}: {
  selectedCodes: string[];
  onToggleCode: (code: AllergenCode) => void;
  isVegetarian: boolean;
  isVegan: boolean;
  isGlutenFree: boolean;
  onChangeVegetarian: (value: boolean) => void;
  onChangeVegan: (value: boolean) => void;
  onChangeGlutenFree: (value: boolean) => void;
}) {
  return (
    <div className="border rounded px-2 py-2 text-sm">
      <p className="text-xs text-neutral-500 mb-1.5">Allergènes (obligatoire en France)</p>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mb-2">
        {INCO_ALLERGEN_CODES.map((code) => (
          <label key={code} className="flex items-center gap-1.5 whitespace-nowrap">
            <input
              type="checkbox"
              checked={selectedCodes.includes(code)}
              onChange={() => onToggleCode(code)}
            />
            {allergenLabel(code, "fr")}
          </label>
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 pt-2 border-t">
        <label className="flex items-center gap-1.5 whitespace-nowrap">
          <input type="checkbox" checked={isVegetarian} onChange={(e) => onChangeVegetarian(e.target.checked)} />
          Végétarien
        </label>
        <label className="flex items-center gap-1.5 whitespace-nowrap">
          <input type="checkbox" checked={isVegan} onChange={(e) => onChangeVegan(e.target.checked)} />
          Vegan
        </label>
        <label className="flex items-center gap-1.5 whitespace-nowrap">
          <input
            type="checkbox"
            checked={isGlutenFree}
            onChange={(e) => onChangeGlutenFree(e.target.checked)}
          />
          Sans gluten
        </label>
      </div>
    </div>
  );
}
