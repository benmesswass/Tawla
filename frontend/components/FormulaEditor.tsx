"use client";

import { useState } from "react";
import { api, type MenuFormula, type MenuItem } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import Button from "@/components/ui/Button";

type EditableSlot = { name: string; itemIds: number[] };

function fromFormula(formula: MenuFormula | null): { name: string; price: string; isAvailable: boolean; slots: EditableSlot[] } {
  if (!formula) {
    return { name: "", price: "", isAvailable: true, slots: [{ name: "Entrée", itemIds: [] }, { name: "Plat", itemIds: [] }, { name: "Dessert", itemIds: [] }] };
  }
  return {
    name: formula.name,
    price: String(formula.price),
    isAvailable: formula.is_available,
    slots: formula.slots.map((s) => ({ name: s.name, itemIds: s.items.map((i) => i.id) })),
  };
}

/**
 * F5-A3 (MARCHE_FRANCE.md) — formules (entrée + plat + dessert, formule
 * midi) : un prix fixe pour un repas composé d'un choix par étape. Modale
 * plutôt qu'un formulaire inline, même choix que `MenuItemOptionsEditor`
 * pour la même raison (édition rare, liste déjà dense).
 */
export default function FormulaEditor({
  restaurantId,
  formula,
  menuItems,
  onClose,
  onSaved,
}: {
  restaurantId: number;
  formula: MenuFormula | null;
  menuItems: MenuItem[];
  onClose: () => void;
  onSaved: (formula: MenuFormula) => void;
}) {
  const [name, setName] = useState(() => fromFormula(formula).name);
  const [price, setPrice] = useState(() => fromFormula(formula).price);
  const [isAvailable, setIsAvailable] = useState(() => fromFormula(formula).isAvailable);
  const [slots, setSlots] = useState<EditableSlot[]>(() => fromFormula(formula).slots);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function addSlot() {
    setSlots((s) => [...s, { name: "", itemIds: [] }]);
  }

  function updateSlotName(index: number, slotName: string) {
    setSlots((s) => s.map((slot, i) => (i === index ? { ...slot, name: slotName } : slot)));
  }

  function toggleSlotItem(index: number, itemId: number) {
    setSlots((s) =>
      s.map((slot, i) =>
        i === index
          ? { ...slot, itemIds: slot.itemIds.includes(itemId) ? slot.itemIds.filter((id) => id !== itemId) : [...slot.itemIds, itemId] }
          : slot
      )
    );
  }

  function removeSlot(index: number) {
    setSlots((s) => s.filter((_, i) => i !== index));
  }

  async function save() {
    setSubmitting(true);
    setError(null);
    try {
      const payloadSlots = slots
        .filter((s) => s.name.trim() && s.itemIds.length > 0)
        .map((s) => ({ name: s.name.trim(), item_ids: s.itemIds }));
      if (!name.trim() || !price || payloadSlots.length === 0) {
        setError("Nom, prix et au moins une étape avec un article sont obligatoires.");
        setSubmitting(false);
        return;
      }
      const saved = formula
        ? await api.updateFormula(formula.id, { name: name.trim(), price: Number(price), is_available: isAvailable, slots: payloadSlots })
        : await api.createFormula({ restaurant_id: restaurantId, name: name.trim(), price: Number(price), slots: payloadSlots });
      onSaved(saved);
      onClose();
    } catch (e) {
      setError(toFrenchMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-xl bg-white p-5 shadow-lg">
        <h2 className="text-lg font-semibold mb-1">{formula ? `Formule — ${formula.name}` : "Nouvelle formule"}</h2>
        <p className="text-sm text-neutral-500 mb-4">
          Un prix fixe pour un repas composé d&apos;un choix par étape (entrée, plat, dessert…). Le client choisit
          exactement un article par étape.
        </p>

        <div className="flex gap-2 mb-4">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nom (ex : Formule Midi)"
            className="flex-1 border rounded px-2 py-1 text-sm"
          />
          <input
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="Prix"
            inputMode="decimal"
            className="w-24 border rounded px-2 py-1 text-sm"
          />
        </div>

        {formula && (
          <label className="flex items-center gap-1.5 text-sm mb-4">
            <input type="checkbox" checked={isAvailable} onChange={(e) => setIsAvailable(e.target.checked)} />
            Disponible
          </label>
        )}

        <div className="space-y-4">
          {slots.map((slot, slotIndex) => (
            <div key={slotIndex} className="border rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <input
                  value={slot.name}
                  onChange={(e) => updateSlotName(slotIndex, e.target.value)}
                  placeholder="Nom de l'étape (ex : Entrée)"
                  className="flex-1 border rounded px-2 py-1 text-sm"
                />
                <button type="button" onClick={() => removeSlot(slotIndex)} className="text-sm text-red-600 px-1">
                  Supprimer
                </button>
              </div>
              <p className="text-xs text-neutral-500 mb-1.5">Articles proposés pour cette étape :</p>
              <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
                {menuItems.length === 0 && <p className="text-xs text-neutral-400">Ajoutez d&apos;abord des articles à la carte.</p>}
                {menuItems.map((item) => (
                  <label key={item.id} className="flex items-center gap-1.5 text-sm">
                    <input
                      type="checkbox"
                      checked={slot.itemIds.includes(item.id)}
                      onChange={() => toggleSlotItem(slotIndex, item.id)}
                    />
                    {item.name}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>

        <button type="button" onClick={addSlot} className="mt-3 text-sm underline">
          + Ajouter une étape
        </button>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <div className="mt-5 flex gap-2">
          <Button onClick={save} disabled={submitting}>
            {submitting ? "Enregistrement…" : "Enregistrer"}
          </Button>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Annuler
          </Button>
        </div>
      </div>
    </div>
  );
}
