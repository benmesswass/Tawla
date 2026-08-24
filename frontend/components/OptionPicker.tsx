"use client";

import { useMemo, useState } from "react";
import type { MenuItem } from "@/lib/api";
import { formatAmount } from "@/lib/market";
import type { Dictionary } from "@/lib/i18n/fr";

export type PickedOption = { id: number; groupName: string; name: string; priceDelta: number };

/**
 * F5-A2 (MARCHE_FRANCE.md) — écran de choix des options d'un article
 * (cuisson, accompagnement, taille…) avant ajout au panier. Ouvert
 * uniquement pour un article qui porte au moins un groupe d'options
 * (`item.option_groups`, voir menu/[qrToken]/page.tsx::renderItem) — un
 * article sans options garde le simple bouton "+" d'aujourd'hui.
 *
 * Validation stricte côté serveur à la commande (jamais confiance au client,
 * CLAUDE.md) — ce picker ne fait que guider l'UX, désactiver "Ajouter" tant
 * qu'un groupe requis n'a pas de choix.
 */
export default function OptionPicker({
  item,
  t,
  onClose,
  onConfirm,
}: {
  item: MenuItem;
  t: Dictionary;
  onClose: () => void;
  onConfirm: (selected: PickedOption[]) => void;
}) {
  const [selectedByGroup, setSelectedByGroup] = useState<Record<number, number[]>>({});

  const missingRequired = useMemo(
    () => item.option_groups.some((g) => g.is_required && (selectedByGroup[g.id]?.length ?? 0) === 0),
    [item.option_groups, selectedByGroup]
  );

  function toggle(groupId: number, choiceId: number, allowMultiple: boolean) {
    setSelectedByGroup((prev) => {
      const current = prev[groupId] ?? [];
      if (allowMultiple) {
        return {
          ...prev,
          [groupId]: current.includes(choiceId) ? current.filter((id) => id !== choiceId) : [...current, choiceId],
        };
      }
      return { ...prev, [groupId]: current.includes(choiceId) ? [] : [choiceId] };
    });
  }

  const totalDelta = item.option_groups
    .flatMap((g) => g.choices)
    .filter((c) => Object.values(selectedByGroup).flat().includes(c.id))
    .reduce((sum, c) => sum + c.price_delta, 0);

  function confirm() {
    const selected: PickedOption[] = item.option_groups.flatMap((g) =>
      (selectedByGroup[g.id] ?? []).map((choiceId) => {
        const choice = g.choices.find((c) => c.id === choiceId)!;
        return { id: choice.id, groupName: g.name, name: choice.name, priceDelta: choice.price_delta };
      })
    );
    onConfirm(selected);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40" role="dialog" aria-modal="true">
      <div className="w-full sm:max-w-sm sm:rounded-xl rounded-t-2xl bg-[var(--semoule-raised)] max-h-[85vh] overflow-y-auto p-4">
        <div className="flex items-start justify-between gap-3 mb-3">
          <h2 className="text-[15px] font-bold text-[var(--encre)]">{item.name}</h2>
          <button type="button" onClick={onClose} aria-label={t.closeErrorAria} className="text-[var(--ink-soft)]">
            ✕
          </button>
        </div>

        <div className="space-y-4">
          {item.option_groups.map((group) => (
            <div key={group.id}>
              <p className="text-sm font-semibold text-[var(--encre)]">
                {group.name}
                {group.is_required && <span className="text-[var(--harissa)]"> *</span>}
              </p>
              <div className="mt-1.5 flex flex-col gap-1.5">
                {group.choices.map((choice) => {
                  const checked = (selectedByGroup[group.id] ?? []).includes(choice.id);
                  return (
                    <label
                      key={choice.id}
                      className="flex items-center justify-between gap-2 rounded-lg border border-[var(--line)] bg-white px-3 py-2 text-sm cursor-pointer"
                    >
                      <span className="flex items-center gap-2">
                        <input
                          type={group.allow_multiple ? "checkbox" : "radio"}
                          name={`group-${group.id}`}
                          checked={checked}
                          onChange={() => toggle(group.id, choice.id, group.allow_multiple)}
                        />
                        {choice.name}
                      </span>
                      {choice.price_delta > 0 && (
                        <span className="text-[var(--ink-soft)] tabular-nums">
                          +{formatAmount(choice.price_delta)}
                        </span>
                      )}
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        <button
          type="button"
          disabled={missingRequired}
          onClick={confirm}
          className="mt-5 w-full rounded-full bg-[var(--harissa)] text-[var(--semoule)] py-3 text-sm font-bold disabled:opacity-45 disabled:cursor-not-allowed"
        >
          {t.addToCartAria(item.name)} — {formatAmount(item.price + totalDelta)}
        </button>
      </div>
    </div>
  );
}
