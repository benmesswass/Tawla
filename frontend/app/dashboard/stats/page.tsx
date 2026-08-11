"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, DashboardStats, Order, OrderStatus } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import { clearToken } from "@/lib/auth";
import Skeleton from "@/components/ui/Skeleton";

const STATUS_LABELS: Record<OrderStatus, string> = {
  pending_confirmation: "En attente de confirmation",
  confirmed: "Confirmée",
  sent_to_kitchen: "En cuisine",
  in_preparation: "En préparation",
  ready: "Prête",
  served: "Servie",
  cancelled: "Annulée",
};

const ACTIVE_STATUS_ORDER: OrderStatus[] = [
  "pending_confirmation",
  "confirmed",
  "sent_to_kitchen",
  "in_preparation",
  "ready",
];

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  const minutes = Math.round(seconds / 60);
  if (minutes < 1) return `${Math.round(seconds)} s`;
  if (minutes < 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function csvEscape(value: string | number): string {
  const s = String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

// Export volontairement limité aux stats déjà calculées côté serveur pour
// LA journée affichée — aucun nouvel endpoint : tout est déjà chargé dans
// `stats`, on ne fait que le reformater en CSV pour Excel/Sheets.
function statsToCsv(stats: DashboardStats): string {
  const lines: string[] = [];
  const row = (...cells: (string | number)[]) => lines.push(cells.map(csvEscape).join(","));

  row("Statistiques Tawla", stats.date);
  lines.push("");

  row("Commandes en cours", stats.active_orders_count);
  lines.push("");

  row("Temps moyen par étape", "Secondes");
  row("Envoyée → confirmée", stats.timing.avg_wait_confirmation_seconds ?? "");
  row("Confirmée → cuisine", stats.timing.avg_confirmation_to_kitchen_seconds ?? "");
  row("Cuisine → servie", stats.timing.avg_kitchen_to_served_seconds ?? "");
  lines.push("");

  row("Serveur", "Commandes prises en charge");
  stats.staff_performance.forEach((p) => row(p.staff_name, p.orders_taken));
  lines.push("");

  row("Plat", "Quantité vendue");
  stats.top_items.forEach((i) => row(i.menu_item_name, i.quantity));
  lines.push("");

  row("Heure", "Commandes");
  stats.orders_by_hour.forEach((h) => row(h.hour, h.count));

  return lines.join("\n");
}

function downloadCsv(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function DashboardStatsPage() {
  const router = useRouter();
  const { staff, loading: staffLoading } = useCurrentStaff(["manager"]);
  const [date, setDate] = useState(todayIso());
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activeOrders, setActiveOrders] = useState<Order[]>([]);
  const [error, setError] = useState<string | null>(null);

  const restaurantId = staff?.restaurant_id ?? null;

  const load = useCallback(async () => {
    if (!restaurantId) return;
    try {
      const [statsRes, ordersRes] = await Promise.all([
        api.getDashboardStats(restaurantId, date),
        api.listActiveOrders(restaurantId),
      ]);
      setStats(statsRes);
      setActiveOrders(ordersRes);
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }, [restaurantId, date]);

  useEffect(() => {
    if (restaurantId) load();
  }, [restaurantId, load]);

  function logout() {
    clearToken();
    router.push("/login");
  }

  if (staffLoading || !staff) {
    return (
      <div className="p-4 max-w-4xl mx-auto space-y-3">
        <Skeleton className="h-6 w-56" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  const ordersByStatus = ACTIVE_STATUS_ORDER.map((status) => ({
    status,
    orders: activeOrders.filter((o) => o.status === status),
  }));

  const maxItemQty = Math.max(1, ...(stats?.top_items.map((i) => i.quantity) ?? [1]));
  const maxHourCount = Math.max(1, ...(stats?.orders_by_hour.map((h) => h.count) ?? [1]));
  const hourByValue = new Map((stats?.orders_by_hour ?? []).map((h) => [h.hour, h.count]));

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <h1 className="text-lg font-semibold">Suivi de l&apos;activité</h1>
        <div className="flex items-center gap-4 text-sm">
          <Link href="/dashboard" className="underline">
            Gérer le menu
          </Link>
          <button onClick={logout} className="text-neutral-500 underline">
            Se déconnecter
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-6 flex-wrap">
        <label htmlFor="date" className="text-sm text-neutral-500">
          Journée
        </label>
        <input
          id="date"
          type="date"
          value={date}
          max={todayIso()}
          onChange={(e) => setDate(e.target.value)}
          className="border rounded px-2 py-1 text-sm"
        />
        <button
          onClick={() => stats && downloadCsv(`tawla-stats-${stats.date}.csv`, statsToCsv(stats))}
          disabled={!stats}
          className="text-sm border border-neutral-300 rounded-lg px-3 py-1 disabled:opacity-50"
        >
          Exporter en CSV
        </button>
      </div>

      {error && <div className="mb-4 text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">{error}</div>}

      {!stats ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section className="border rounded-lg p-4">
            <h2 className="font-semibold mb-3">
              Commandes en cours <span className="text-neutral-400 font-normal">({stats.active_orders_count})</span>
            </h2>
            <div className="space-y-2">
              {ordersByStatus.map(({ status, orders }) => (
                <div key={status} className="flex justify-between text-sm">
                  <span className="text-neutral-600">{STATUS_LABELS[status]}</span>
                  <span className="font-medium">{orders.length}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="border rounded-lg p-4">
            <h2 className="font-semibold mb-3">Temps moyen par étape</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-neutral-600">Envoyée → confirmée</span>
                <span className="font-medium">{formatDuration(stats.timing.avg_wait_confirmation_seconds)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-neutral-600">Confirmée → cuisine</span>
                <span className="font-medium">
                  {formatDuration(stats.timing.avg_confirmation_to_kitchen_seconds)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-neutral-600">Cuisine → servie</span>
                <span className="font-medium">{formatDuration(stats.timing.avg_kitchen_to_served_seconds)}</span>
              </div>
            </div>
          </section>

          <section className="border rounded-lg p-4">
            <h2 className="font-semibold mb-3">Commandes prises en charge par serveur</h2>
            {stats.staff_performance.length === 0 && <p className="text-sm text-neutral-500">Aucune donnée pour cette journée.</p>}
            <div className="space-y-2">
              {stats.staff_performance.map((p) => (
                <div key={p.staff_id} className="flex justify-between text-sm">
                  <span className="text-neutral-600">{p.staff_name}</span>
                  <span className="font-medium">{p.orders_taken}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="border rounded-lg p-4">
            <h2 className="font-semibold mb-3">Plats les plus vendus</h2>
            {stats.top_items.length === 0 && <p className="text-sm text-neutral-500">Aucune commande pour cette journée.</p>}
            <div className="space-y-2">
              {stats.top_items.map((item) => (
                <div key={item.menu_item_name}>
                  <div className="flex justify-between text-sm mb-0.5">
                    <span className="text-neutral-600">{item.menu_item_name}</span>
                    <span className="font-medium">{item.quantity}</span>
                  </div>
                  <div className="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-amber-700 rounded-full"
                      style={{ width: `${(item.quantity / maxItemQty) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="border rounded-lg p-4 lg:col-span-2">
            <h2 className="font-semibold mb-3">Heures de pointe</h2>
            {stats.orders_by_hour.length === 0 ? (
              <p className="text-sm text-neutral-500">Aucune commande pour cette journée.</p>
            ) : (
              <div className="flex items-end gap-1 h-28">
                {Array.from({ length: 24 }, (_, hour) => hour).map((hour) => {
                  const count = hourByValue.get(hour) ?? 0;
                  return (
                    <div key={hour} className="flex-1 flex flex-col items-center justify-end h-full" title={`${hour}h — ${count} commande(s)`}>
                      <div
                        className="w-full bg-amber-700 rounded-t"
                        style={{ height: count ? `${(count / maxHourCount) * 100}%` : "1px" }}
                      />
                      {hour % 3 === 0 && <span className="text-[10px] text-neutral-400 mt-1">{hour}h</span>}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
