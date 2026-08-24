"use client";

import { useState } from "react";
import type { Order } from "@/lib/api";
import { fr, type Dictionary } from "@/lib/i18n/fr";
import { UtensilsIcon } from "@/components/icons";
import { formatAmount } from "@/lib/market";

type SplitMode = "equal" | "items";

/**
 * Calculateur indicatif — n'affecte pas le paiement réel : la table règle
 * toujours l'addition en une fois (carte ou espèces), quel que soit le
 * partage affiché ici. Un vrai paiement séparé par personne demanderait de
 * refondre le modèle de paiement (un statut par personne au lieu d'un seul
 * par commande) — reporté tant qu'un pilote resto réel n'en confirme pas le
 * besoin (cf. philosophie KISS/YAGNI du projet).
 */
export default function SplitBill({ order, t = fr }: { order: Order; t?: Dictionary }) {
  const [open, setOpen] = useState(false);
  // Par plat, et non à parts égales : c'est ce que la table demande dès qu'un
  // convive a pris une entrée et l'autre un plat du jour. Et comme le client a
  // déjà dit qui partageait quoi en commandant, la répartition arrive
  // pré-remplie au lieu de lui reposer la question (retour du premier service).
  const [mode, setMode] = useState<SplitMode>("items");
  const [peopleCount, setPeopleCount] = useState(() => convivesDeLaCommande(order));
  // Clé composée ("item:3" / "formula:3") : `OrderItem.id` et `OrderFormula.id`
  // viennent de deux tables distinctes et peuvent coïncider (F5-A3).
  const [assignments, setAssignments] = useState<Record<string, number[]>>(() => ({
    ...Object.fromEntries(order.items.map((it) => [`item:${it.id}`, it.shared_with ?? []])),
    ...Object.fromEntries(order.formulas.map((f) => [`formula:${f.id}`, f.shared_with ?? []])),
  }));

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="text-sm underline text-[var(--laiton)]">
        {t.splitBillToggle}
      </button>
    );
  }

  const shares = computeShares(order, mode, peopleCount, assignments);

  return (
    <div className="border border-[var(--line)] bg-[var(--semoule-raised)] rounded-[12px] p-3 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-[var(--encre)]">{t.splitBillTitle}</p>
        <button onClick={() => setOpen(false)} className="text-sm text-[var(--ink-soft)] underline">
          {t.close}
        </button>
      </div>

      <div className="flex gap-2 text-sm">
        <button
          onClick={() => setMode("equal")}
          className={`flex-1 rounded-[10px] py-1.5 border ${
            mode === "equal"
              ? "bg-[var(--harissa)] text-[var(--semoule)] border-[var(--harissa)]"
              : "border-[var(--line)] bg-white text-[var(--encre)]"
          }`}
        >
          {t.splitModeEqual}
        </button>
        <button
          onClick={() => setMode("items")}
          className={`flex-1 rounded-[10px] py-1.5 border ${
            mode === "items"
              ? "bg-[var(--harissa)] text-[var(--semoule)] border-[var(--harissa)]"
              : "border-[var(--line)] bg-white text-[var(--encre)]"
          }`}
        >
          {t.splitModeByItem}
        </button>
      </div>

      <div className="flex items-center gap-2 text-sm text-[var(--encre)]">
        <label htmlFor="split-people-count">{t.peopleCountLabel}</label>
        <input
          id="split-people-count"
          type="number"
          min={2}
          max={12}
          value={peopleCount}
          onChange={(e) => setPeopleCount(Math.max(2, Math.min(12, Number(e.target.value) || 2)))}
          className="w-16 bg-white border border-[var(--line)] rounded-[10px] px-2 py-1"
        />
      </div>

      {mode === "items" && (
        <div className="space-y-3">
          {[
            ...order.items.map((it) => ({
              key: `item:${it.id}`,
              label: it.menu_item_name,
              quantity: it.quantity,
              isShared: it.is_shared,
              detail: it.selected_options.map((opt) => opt.choice_name).join(", "),
            })),
            ...order.formulas.map((f) => ({
              key: `formula:${f.id}`,
              label: f.formula_name,
              quantity: f.quantity,
              isShared: f.is_shared,
              detail: f.selections.map((s) => s.menu_item_name).join(", "),
            })),
          ].map((line) => {
            const places = assignments[line.key] ?? [];
            return (
              <div key={line.key} className="text-sm">
                <div className="text-[var(--encre)]">
                  {line.quantity}× {line.label}
                  {line.isShared && (
                    <span className="text-[var(--laiton)] inline-flex items-center gap-1 align-middle">
                      · <UtensilsIcon className="w-3.5 h-3.5 shrink-0" /> {t.sharedTag}
                    </span>
                  )}
                </div>
                {line.detail && <div className="text-xs text-[var(--ink-soft)]">{line.detail}</div>}
                {/* Des pastilles plutôt qu'une liste déroulante : un plat peut
                    être partagé entre deux convives sans l'être par toute la
                    table, ce qu'un choix unique ne savait pas dire. */}
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {Array.from({ length: peopleCount }, (_, i) => i + 1).map((p) => {
                    const choisi = places.includes(p);
                    return (
                      <button
                        key={p}
                        type="button"
                        aria-pressed={choisi}
                        onClick={() =>
                          setAssignments((prev) => {
                            const actuel = prev[line.key] ?? [];
                            return {
                              ...prev,
                              [line.key]: actuel.includes(p)
                                ? actuel.filter((x) => x !== p)
                                : [...actuel, p].sort((a, b) => a - b),
                            };
                          })
                        }
                        className={`rounded-full border px-2.5 py-1 text-xs ${
                          choisi
                            ? "bg-[var(--harissa)] text-[var(--semoule)] border-[var(--harissa)]"
                            : "border-[var(--line)] bg-white text-[var(--encre)]"
                        }`}
                      >
                        {t.personLabel(p)}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
          <p className="text-xs text-[var(--ink-faint)]">{t.unassignedSharedNote}</p>
        </div>
      )}

      <div className="pt-2 border-t border-[var(--line)] space-y-1 text-sm text-[var(--encre)]">
        {shares.map((amount, i) => (
          <div key={i} className="flex justify-between">
            <span>{t.personLabel(i + 1)}</span>
            <span className="font-semibold tabular-nums">{formatAmount(amount)}</span>
          </div>
        ))}
      </div>

      <p className="text-xs text-[var(--ink-soft)]">{t.splitBillDisclaimer}</p>
    </div>
  );
}

/**
 * Nombre de convives déduit de la commande : la plus grande place citée par un
 * plat partagé. Le client l'a déjà indiqué en commandant, redemander « vous
 * êtes combien ? » juste après serait de l'amnésie.
 */
function convivesDeLaCommande(order: Order): number {
  const places = order.items.flatMap((it) => it.shared_with ?? []);
  return Math.max(2, ...places);
}

function computeShares(
  order: Order,
  mode: SplitMode,
  peopleCount: number,
  assignments: Record<string, number[]>
): number[] {
  if (mode === "equal") {
    return Array(peopleCount).fill(order.total_amount / peopleCount);
  }

  const totals = Array(peopleCount).fill(0);
  const lines = [
    ...order.items.map((it) => ({ key: `item:${it.id}`, lineTotal: it.unit_price * it.quantity })),
    // F5-A3 : une formule non répartie manuellement doit quand même être
    // payée par quelqu'un — sans cette ligne, son prix disparaissait du
    // calcul « par plat » alors qu'il reste dû sur l'addition réelle.
    ...order.formulas.map((f) => ({ key: `formula:${f.id}`, lineTotal: f.unit_price * f.quantity })),
  ];
  for (const line of lines) {
    // Personne de désigné = partagé par toute la table : c'est le sens d'un
    // plat « à partager » sans précision, et le comportement d'avant.
    const places = (assignments[line.key] ?? []).filter((p) => p >= 1 && p <= peopleCount);
    const entreQui = places.length > 0 ? places : Array.from({ length: peopleCount }, (_, i) => i + 1);
    const part = line.lineTotal / entreQui.length;
    for (const place of entreQui) {
      totals[place - 1] += part;
    }
  }
  return totals;
}
