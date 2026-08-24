"use client";

import { useMemo, useState } from "react";
import type { MenuFormula, MenuFormulaSlotItem } from "@/lib/api";
import { formatAmount } from "@/lib/market";
import type { Dictionary } from "@/lib/i18n/fr";

export type PickedFormulaSelection = { slotId: number; item: MenuFormulaSlotItem };

/**
 * F5-A3 (MARCHE_FRANCE.md) — écran de choix d'une formule (entrée + plat +
 * dessert…) avant ajout au panier. Une étape par groupe de choix, toujours
 * exactement un article par étape — contrairement à `OptionPicker`, aucune
 * étape n'est facultative ni à choix multiple dans cette première version.
 *
 * Validation stricte côté serveur à la commande (jamais confiance au client,
 * CLAUDE.md) — ce picker ne fait que guider l'UX, désactiver "Ajouter" tant
 * qu'une étape n'a pas de choix.
 */
export default function FormulaPicker({
  formula,
  t,
  onClose,
  onConfirm,
}: {
  formula: MenuFormula;
  t: Dictionary;
  onClose: () => void;
  onConfirm: (selections: PickedFormulaSelection[]) => void;
}) {
  const [selectedBySlot, setSelectedBySlot] = useState<Record<number, number>>({});

  const missingSlot = useMemo(
    () => formula.slots.some((slot) => selectedBySlot[slot.id] === undefined),
    [formula.slots, selectedBySlot]
  );

  function choose(slotId: number, itemId: number) {
    setSelectedBySlot((prev) => ({ ...prev, [slotId]: itemId }));
  }

  function confirm() {
    const selections: PickedFormulaSelection[] = formula.slots.map((slot) => {
      const itemId = selectedBySlot[slot.id];
      const item = slot.items.find((i) => i.id === itemId)!;
      return { slotId: slot.id, item };
    });
    onConfirm(selections);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40" role="dialog" aria-modal="true">
      <div className="w-full sm:max-w-sm sm:rounded-xl rounded-t-2xl bg-[var(--semoule-raised)] max-h-[85vh] overflow-y-auto p-4">
        <div className="flex items-start justify-between gap-3 mb-3">
          <h2 className="text-[15px] font-bold text-[var(--encre)]">{formula.name}</h2>
          <button type="button" onClick={onClose} aria-label={t.closeErrorAria} className="text-[var(--ink-soft)]">
            ✕
          </button>
        </div>

        <div className="space-y-4">
          {formula.slots.map((slot) => (
            <div key={slot.id}>
              <p className="text-sm font-semibold text-[var(--encre)]">
                {slot.name}
                <span className="text-[var(--harissa)]"> *</span>
              </p>
              <div className="mt-1.5 flex flex-col gap-1.5">
                {slot.items.map((item) => {
                  const checked = selectedBySlot[slot.id] === item.id;
                  return (
                    <label
                      key={item.id}
                      className="flex items-center justify-between gap-2 rounded-lg border border-[var(--line)] bg-white px-3 py-2 text-sm cursor-pointer"
                    >
                      <span className="flex items-center gap-2">
                        <input
                          type="radio"
                          name={`formula-slot-${slot.id}`}
                          checked={checked}
                          onChange={() => choose(slot.id, item.id)}
                        />
                        {item.name}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        <button
          type="button"
          disabled={missingSlot}
          onClick={confirm}
          className="mt-5 w-full rounded-full bg-[var(--harissa)] text-[var(--semoule)] py-3 text-sm font-bold disabled:opacity-45 disabled:cursor-not-allowed"
        >
          {t.addToCartAria(formula.name)} — {formatAmount(formula.price)}
        </button>
      </div>
    </div>
  );
}
