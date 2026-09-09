"use client";

import { useCallback, useEffect, useState } from "react";
import EnteteManager from "@/components/EnteteManager";
import { api, ForcedTableRelease, OrderInProgressStatus } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import Skeleton from "@/components/ui/Skeleton";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";

/**
 * Écran manager « Libérations forcées » (2026-09-09, demande de Wassim).
 *
 * Une table libérée alors qu'une commande était encore en cours (n'importe
 * quelle étape, y compris servie mais pas encore encaissée) est tracée côté
 * backend avec une note obligatoire écrite par le serveur/manager sur le
 * moment (`ModaleLibererTable`, `tables/service.py::release_table`). Cette
 * page est le seul endroit où le manager retrouve qui, quand, quelle table,
 * à quelle étape, et pourquoi — une libération normale (commande terminée et
 * payée, ou aucune) n'y apparaît jamais : ce n'est pas un journal de toutes
 * les libérations, seulement de celles qui méritent un regard.
 */

const ETAPE_LABELS: Record<OrderInProgressStatus, string> = {
  pending_confirmation: "en attente de confirmation",
  confirmed: "confirmée, pas encore envoyée en cuisine",
  sent_to_kitchen: "envoyée en cuisine",
  in_preparation: "en préparation",
  ready: "prête à servir",
  served_unpaid: "servie, addition pas encore encaissée",
};

function formatDateHeure(iso: string): string {
  return new Date(iso).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function LiberationsForceesPage() {
  const { staff, loading: staffLoading } = useCurrentStaff(["manager"]);
  const [releases, setReleases] = useState<ForcedTableRelease[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const restaurantId = staff?.restaurant_id ?? null;

  const load = useCallback(async () => {
    if (!restaurantId) return;
    setError(null);
    try {
      setReleases(await api.listForcedReleases(restaurantId));
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }, [restaurantId]);

  useEffect(() => {
    if (restaurantId) load();
  }, [restaurantId, load]);

  if (staffLoading || !staff) {
    return (
      <div className="p-4 md:p-6 space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6">
      <EnteteManager
        titre="Libérations forcées"
        sousTitre="Tables libérées alors qu'une commande était encore en cours — avec la note écrite sur le moment par qui l'a fait. Une libération normale (commande terminée et payée, ou aucune) n'apparaît jamais ici."
      />

      {error && (
        <Card tone="danger" padding="sm" className="mb-4 text-sm text-[var(--harissa)]">
          {error}
        </Card>
      )}

      {!releases ? (
        <Skeleton className="h-48 w-full" />
      ) : releases.length === 0 ? (
        <EmptyState message="Aucune libération forcée — chaque table a toujours été libérée sans commande en cours, ou déjà réglée." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[var(--ink-soft)] border-b border-[var(--line)]">
                <th className="py-2 pr-3 font-medium">Table</th>
                <th className="py-2 pr-3 font-medium">Libérée par</th>
                <th className="py-2 pr-3 font-medium">Quand</th>
                <th className="py-2 pr-3 font-medium">Étape de la commande</th>
                <th className="py-2 font-medium">Note</th>
              </tr>
            </thead>
            <tbody>
              {releases.map((r) => (
                <tr key={r.id} className="border-b border-[var(--line)] align-top">
                  <td className="py-2 pr-3 whitespace-nowrap font-medium text-[var(--encre)]">{r.table_label}</td>
                  <td className="py-2 pr-3 whitespace-nowrap">{r.released_by_name}</td>
                  <td className="py-2 pr-3 whitespace-nowrap tabular-nums">{formatDateHeure(r.released_at)}</td>
                  <td className="py-2 pr-3 whitespace-nowrap">
                    <span className="inline-flex items-center text-xs font-medium text-[var(--harissa-dark)] bg-[rgba(214,64,30,.1)] rounded-full px-2 py-0.5">
                      {ETAPE_LABELS[r.order_status_snapshot] ?? r.order_status_snapshot}
                    </span>
                  </td>
                  <td className="py-2 text-[var(--ink-soft)]">{r.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
