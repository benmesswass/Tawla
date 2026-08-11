"use client";

import { useState } from "react";
import type { Order } from "@/lib/api";

type SplitMode = "equal" | "items";

/**
 * Calculateur indicatif — n'affecte pas le paiement réel : la table règle
 * toujours l'addition en une fois (carte ou espèces), quel que soit le
 * partage affiché ici. Un vrai paiement séparé par personne demanderait de
 * refondre le modèle de paiement (un statut par personne au lieu d'un seul
 * par commande) — reporté tant qu'un pilote resto réel n'en confirme pas le
 * besoin (cf. philosophie KISS/YAGNI du projet).
 */
export default function SplitBill({ order }: { order: Order }) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<SplitMode>("equal");
  const [peopleCount, setPeopleCount] = useState(2);
  const [assignments, setAssignments] = useState<Record<number, number>>({});

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="text-sm underline text-neutral-600">
        Partager l&apos;addition entre plusieurs personnes
      </button>
    );
  }

  const shares = computeShares(order, mode, peopleCount, assignments);

  return (
    <div className="border rounded-lg p-3 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Partager l&apos;addition</p>
        <button onClick={() => setOpen(false)} className="text-sm text-neutral-500 underline">
          Fermer
        </button>
      </div>

      <div className="flex gap-2 text-sm">
        <button
          onClick={() => setMode("equal")}
          className={`flex-1 rounded-lg py-1.5 border ${mode === "equal" ? "bg-neutral-900 text-white" : ""}`}
        >
          Équitable
        </button>
        <button
          onClick={() => setMode("items")}
          className={`flex-1 rounded-lg py-1.5 border ${mode === "items" ? "bg-neutral-900 text-white" : ""}`}
        >
          Par plat
        </button>
      </div>

      <div className="flex items-center gap-2 text-sm">
        <label htmlFor="split-people-count">Nombre de personnes</label>
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
        <div className="space-y-2">
          {order.items.map((it) => (
            <div key={it.id} className="flex items-center justify-between text-sm gap-2">
              <span className="flex-1">
                {it.quantity}× {it.menu_item_name}
              </span>
              <select
                value={assignments[it.id] ?? 0}
                onChange={(e) => setAssignments((prev) => ({ ...prev, [it.id]: Number(e.target.value) }))}
                className="border rounded px-2 py-1"
              >
                <option value={0}>Partagé</option>
                {Array.from({ length: peopleCount }, (_, i) => i + 1).map((p) => (
                  <option key={p} value={p}>
                    Personne {p}
                  </option>
                ))}
              </select>
            </div>
          ))}
          <p className="text-xs text-neutral-400">Les plats non attribués sont partagés équitablement.</p>
        </div>
      )}

      <div className="pt-2 border-t space-y-1 text-sm">
        {shares.map((amount, i) => (
          <div key={i} className="flex justify-between">
            <span>Personne {i + 1}</span>
            <span className="font-medium">{amount.toFixed(2)} DT</span>
          </div>
        ))}
      </div>

      <p className="text-xs text-neutral-500">
        Indicatif — le paiement se fait pour l&apos;addition complète, une seule fois pour la table.
      </p>
    </div>
  );
}

function computeShares(
  order: Order,
  mode: SplitMode,
  peopleCount: number,
  assignments: Record<number, number>
): number[] {
  if (mode === "equal") {
    return Array(peopleCount).fill(order.total_amount / peopleCount);
  }

  const totals = Array(peopleCount).fill(0);
  let sharedTotal = 0;
  for (const item of order.items) {
    const lineTotal = item.unit_price * item.quantity;
    const person = assignments[item.id];
    if (person >= 1 && person <= peopleCount) {
      totals[person - 1] += lineTotal;
    } else {
      sharedTotal += lineTotal;
    }
  }
  const sharedPerPerson = sharedTotal / peopleCount;
  return totals.map((t) => t + sharedPerPerson);
}
