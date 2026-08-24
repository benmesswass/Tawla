"use client";

import { useState } from "react";
import { api, type MenuItem } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { formatAmount } from "@/lib/market";
import Button from "@/components/ui/Button";

type EditableChoice = { name: string; priceDelta: string };
type EditableGroup = { name: string; isRequired: boolean; allowMultiple: boolean; choices: EditableChoice[] };

function fromItem(item: MenuItem): EditableGroup[] {
  return item.option_groups.map((g) => ({
    name: g.name,
    isRequired: g.is_required,
    allowMultiple: g.allow_multiple,
    choices: g.choices.map((c) => ({ name: c.name, priceDelta: String(c.price_delta) })),
  }));
}

/**
 * F5-A2 (MARCHE_FRANCE.md) — options et suppléments d'un article (cuisson,
 * accompagnement, taille…). Modale plutôt qu'un formulaire inline : la liste
 * d'articles est déjà dense, et cette édition reste rare (une fois par plat,
 * pas à chaque service) — voir `UpgradeModal` pour le même choix.
 */
export default function MenuItemOptionsEditor({
  item,
  onClose,
  onSaved,
}: {
  item: MenuItem;
  onClose: () => void;
  onSaved: (item: MenuItem) => void;
}) {
  const [groups, setGroups] = useState<EditableGroup[]>(() => fromItem(item));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function addGroup() {
    setGroups((g) => [...g, { name: "", isRequired: false, allowMultiple: false, choices: [{ name: "", priceDelta: "0" }] }]);
  }

  function updateGroup(index: number, patch: Partial<EditableGroup>) {
    setGroups((g) => g.map((group, i) => (i === index ? { ...group, ...patch } : group)));
  }

  function removeGroup(index: number) {
    setGroups((g) => g.filter((_, i) => i !== index));
  }

  function addChoice(groupIndex: number) {
    setGroups((g) =>
      g.map((group, i) =>
        i === groupIndex ? { ...group, choices: [...group.choices, { name: "", priceDelta: "0" }] } : group
      )
    );
  }

  function updateChoice(groupIndex: number, choiceIndex: number, patch: Partial<EditableChoice>) {
    setGroups((g) =>
      g.map((group, i) =>
        i === groupIndex
          ? { ...group, choices: group.choices.map((c, j) => (j === choiceIndex ? { ...c, ...patch } : c)) }
          : group
      )
    );
  }

  function removeChoice(groupIndex: number, choiceIndex: number) {
    setGroups((g) =>
      g.map((group, i) =>
        i === groupIndex ? { ...group, choices: group.choices.filter((_, j) => j !== choiceIndex) } : group
      )
    );
  }

  async function save() {
    setSubmitting(true);
    setError(null);
    try {
      // Groupes/choix sans nom retirés silencieusement plutôt que bloqués :
      // une ligne laissée vide en cours d'édition n'est pas une erreur.
      const payload = groups
        .filter((g) => g.name.trim())
        .map((g) => ({
          name: g.name.trim(),
          is_required: g.isRequired,
          allow_multiple: g.allowMultiple,
          choices: g.choices
            .filter((c) => c.name.trim())
            .map((c) => ({ name: c.name.trim(), price_delta: Number(c.priceDelta) || 0 })),
        }))
        .filter((g) => g.choices.length > 0);
      const updated = await api.setMenuItemOptions(item.id, payload);
      onSaved(updated);
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
        <h2 className="text-lg font-semibold mb-1">Options — {item.name}</h2>
        <p className="text-sm text-neutral-500 mb-4">
          Cuisson, accompagnement, taille… Un groupe requis oblige le client à choisir avant d&apos;ajouter au panier.
        </p>

        <div className="space-y-4">
          {groups.map((group, groupIndex) => (
            <div key={groupIndex} className="border rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <input
                  value={group.name}
                  onChange={(e) => updateGroup(groupIndex, { name: e.target.value })}
                  placeholder="Nom du groupe (ex : Cuisson)"
                  className="flex-1 border rounded px-2 py-1 text-sm"
                />
                <button type="button" onClick={() => removeGroup(groupIndex)} className="text-sm text-red-600 px-1">
                  Supprimer
                </button>
              </div>
              <div className="flex gap-3 mb-2 text-sm">
                <label className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={group.isRequired}
                    onChange={(e) => updateGroup(groupIndex, { isRequired: e.target.checked })}
                  />
                  Obligatoire
                </label>
                <label className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={group.allowMultiple}
                    onChange={(e) => updateGroup(groupIndex, { allowMultiple: e.target.checked })}
                  />
                  Plusieurs choix possibles
                </label>
              </div>
              <div className="space-y-1.5">
                {group.choices.map((choice, choiceIndex) => (
                  <div key={choiceIndex} className="flex items-center gap-2">
                    <input
                      value={choice.name}
                      onChange={(e) => updateChoice(groupIndex, choiceIndex, { name: e.target.value })}
                      placeholder="Ex : Saignant"
                      className="flex-1 border rounded px-2 py-1 text-sm"
                    />
                    <input
                      value={choice.priceDelta}
                      onChange={(e) => updateChoice(groupIndex, choiceIndex, { priceDelta: e.target.value })}
                      placeholder="0"
                      inputMode="decimal"
                      className="w-20 border rounded px-2 py-1 text-sm"
                      title="Supplément de prix (0 si aucun)"
                    />
                    <button
                      type="button"
                      onClick={() => removeChoice(groupIndex, choiceIndex)}
                      className="text-sm text-red-600 px-1"
                    >
                      ✕
                    </button>
                  </div>
                ))}
                <button type="button" onClick={() => addChoice(groupIndex)} className="text-sm underline">
                  + Ajouter un choix
                </button>
              </div>
            </div>
          ))}
        </div>

        <button type="button" onClick={addGroup} className="mt-3 text-sm underline">
          + Ajouter un groupe d&apos;options
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
        <p className="mt-3 text-xs text-neutral-400">
          Exemple d&apos;affichage client : {formatAmount(1.5, { decimals: 2 })} pour un supplément fromage.
        </p>
      </div>
    </div>
  );
}
