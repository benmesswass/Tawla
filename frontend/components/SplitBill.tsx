"use client";

import { useState } from "react";
import type { Order } from "@/lib/api";
import { fr, type Dictionary } from "@/lib/i18n/fr";
import { UtensilsIcon } from "@/components/icons";

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
  const [assignments, setAssignments] = useState<Record<number, number[]>>(() =>
    Object.fromEntries(order.items.map((it) => [it.id, it.shared_with ?? []]))
  );

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="text-sm underline text-neutral-600">
        {t.splitBillToggle}
      </button>
    );
  }

  const shares = computeShares(order, mode, peopleCount, assignments);

  return (
    <div className="border rounded-lg p-3 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">{t.splitBillTitle}</p>
        <button onClick={() => setOpen(false)} className="text-sm text-neutral-500 underline">
          {t.close}
        </button>
      </div>

      <div className="flex gap-2 text-sm">
        <button
          onClick={() => setMode("equal")}
          className={`flex-1 rounded-lg py-1.5 border ${mode === "equal" ? "bg-neutral-900 text-white" : ""}`}
        >
          {t.splitModeEqual}
        </button>
        <button
          onClick={() => setMode("items")}
          className={`flex-1 rounded-lg py-1.5 border ${mode === "items" ? "bg-neutral-900 text-white" : ""}`}
        >
          {t.splitModeByItem}
        </button>
      </div>

      <div className="flex items-center gap-2 text-sm">
        <label htmlFor="split-people-count">{t.peopleCountLabel}</label>
        <input
          id="split-people-count"
          type="number"
          min={2}
          max={12}
          value={peopleCount}
          onChange={(e) => setPeopleCount(Math.max(2, Math.min(12, Number(e.target.value) || 2)))}
          className="w-16 border rounded px-2 py-1"
        />
      </div>

      {mode === "items" && (
        <div className="space-y-3">
          {order.items.map((it) => {
            const places = assignments[it.id] ?? [];
            return (
              <div key={it.id} className="text-sm">
                <div>
                  {it.quantity}× {it.menu_item_name}
                  {it.is_shared && (
                    <span className="text-amber-700 inline-flex items-center gap-1 align-middle">
                      · <UtensilsIcon className="w-3.5 h-3.5 shrink-0" /> {t.sharedTag}
                    </span>
                  )}
                </div>
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
                            const actuel = prev[it.id] ?? [];
                            return {
                              ...prev,
                              [it.id]: actuel.includes(p)
                                ? actuel.filter((x) => x !== p)
                                : [...actuel, p].sort((a, b) => a - b),
                            };
                          })
                        }
                        className={`rounded-full border px-2.5 py-1 text-xs ${
                          choisi ? "bg-neutral-900 text-white border-neutral-900" : ""
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
          <p className="text-xs text-neutral-400">{t.unassignedSharedNote}</p>
        </div>
      )}

      <div className="pt-2 border-t space-y-1 text-sm">
        {shares.map((amount, i) => (
          <div key={i} className="flex justify-between">
            <span>{t.personLabel(i + 1)}</span>
            <span className="font-medium">
              {amount.toFixed(2)} {t.currency}
            </span>
          </div>
        ))}
      </div>

      <p className="text-xs text-neutral-500">{t.splitBillDisclaimer}</p>
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
  assignments: Record<number, number[]>
): number[] {
  if (mode === "equal") {
    return Array(peopleCount).fill(order.total_amount / peopleCount);
  }

  const totals = Array(peopleCount).fill(0);
  for (const item of order.items) {
    const lineTotal = item.unit_price * item.quantity;
    // Personne de désigné = partagé par toute la table : c'est le sens d'un
    // plat « à partager » sans précision, et le comportement d'avant.
    const places = (assignments[item.id] ?? []).filter((p) => p >= 1 && p <= peopleCount);
    const entreQui = places.length > 0 ? places : Array.from({ length: peopleCount }, (_, i) => i + 1);
    const part = lineTotal / entreQui.length;
    for (const place of entreQui) {
      totals[place - 1] += part;
    }
  }
  return totals;
}
