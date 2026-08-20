"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import Skeleton from "@/components/ui/Skeleton";
import {
  clearAdminToken,
  getAdminToken,
  platformAdminApi,
  PlatformAdminApiError,
  type PlatformOverview,
  type SubscriptionTier,
} from "@/lib/platformAdmin";

const TIER_LABELS: Record<SubscriptionTier, string> = {
  essentiel: "Essentiel",
  pro: "Pro",
  business: "Business",
};

function formatMoney(amount: number): string {
  return `${amount.toFixed(2)} DT`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function formatWeekLabel(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });
}

function errorMessage(): string {
  return "Une erreur est survenue. Réessayez dans un instant.";
}

function WeeklyBarChart({
  title,
  points,
  valueOf,
  color,
  emptyMessage,
}: {
  title: string;
  points: PlatformOverview["weekly"];
  valueOf: (p: PlatformOverview["weekly"][number]) => number;
  color: string;
  emptyMessage: string;
}) {
  const max = Math.max(1, ...points.map(valueOf));
  const isEmpty = points.every((p) => valueOf(p) === 0);
  return (
    <Card padding="md">
      <h2 className="font-semibold mb-3">{title}</h2>
      {isEmpty ? (
        <EmptyState message={emptyMessage} />
      ) : (
        <div className="flex items-end gap-1 h-28">
          {points.map((p) => {
            const value = valueOf(p);
            return (
              <div
                key={p.week_start}
                className="flex-1 flex flex-col items-center justify-end h-full"
                title={`Semaine du ${formatWeekLabel(p.week_start)} — ${value}`}
              >
                <div
                  className="w-full rounded-t"
                  style={{ height: value ? `${(value / max) * 100}%` : "1px", background: color }}
                />
                <span className="text-[10px] mt-1" style={{ color: "var(--ink-soft)" }}>
                  {formatWeekLabel(p.week_start)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

export default function PlatformAdminPage() {
  const router = useRouter();
  const [overview, setOverview] = useState<PlatformOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checkedAuth, setCheckedAuth] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await platformAdminApi.getOverview();
      setOverview(data);
    } catch (err) {
      // Session invalide (jamais configurée, expirée après 12h) : le client
      // a déjà effacé le token, il ne reste qu'à repartir sur l'écran de
      // connexion — pas la peine d'afficher une erreur qui va disparaître.
      if (err instanceof PlatformAdminApiError && (err.code === "NOT_AUTHENTICATED" || err.code === "INVALID_TOKEN")) {
        router.replace("/admin/login");
        return;
      }
      setError(errorMessage());
    }
  }, [router]);

  useEffect(() => {
    if (!getAdminToken()) {
      router.replace("/admin/login");
      return;
    }
    setCheckedAuth(true);
    load();
  }, [router, load]);

  function handleLogout() {
    clearAdminToken();
    router.replace("/admin/login");
  }

  if (!checkedAuth || (!overview && !error)) {
    return (
      <div className="p-4 max-w-5xl mx-auto space-y-3">
        <Skeleton className="h-8 w-72" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 max-w-5xl mx-auto">
      <div className="flex items-start justify-between gap-4 mb-6 flex-wrap">
        <div>
          <h1 className="text-xl font-semibold" style={{ color: "var(--encre)" }}>
            Tableau de bord plateforme
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--ink-soft)" }}>
            Tous les restaurants clients, vue d&apos;ensemble.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={handleLogout}>
          Se déconnecter
        </Button>
      </div>

      {error && (
        <Card tone="danger" padding="sm" className="mb-4 text-sm text-red-700">
          {error}
        </Card>
      )}

      {overview && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <Card padding="md">
              <div className="text-xs uppercase tracking-wide" style={{ color: "var(--ink-soft)" }}>
                Restaurants clients
              </div>
              <div className="text-2xl font-semibold mt-1">{overview.restaurants_total}</div>
              <div className="flex flex-wrap gap-1 mt-2">
                {(Object.keys(TIER_LABELS) as SubscriptionTier[]).map((tier) => (
                  <Badge key={tier} tone="neutral">
                    {TIER_LABELS[tier]} · {overview.restaurants_by_tier[tier] ?? 0}
                  </Badge>
                ))}
              </div>
            </Card>

            <Card padding="md">
              <div className="text-xs uppercase tracking-wide" style={{ color: "var(--ink-soft)" }}>
                Nouveaux restaurants (30j)
              </div>
              <div className="text-2xl font-semibold mt-1">{overview.restaurants_created_last_30d}</div>
            </Card>

            <Card padding="md">
              <div className="text-xs uppercase tracking-wide" style={{ color: "var(--ink-soft)" }}>
                Commandes
              </div>
              <div className="text-2xl font-semibold mt-1">{overview.orders_total}</div>
              <div className="text-sm mt-1" style={{ color: "var(--ink-soft)" }}>
                {overview.orders_last_30d} sur les 30 derniers jours
              </div>
            </Card>

            <Card padding="md">
              <div className="text-xs uppercase tracking-wide" style={{ color: "var(--ink-soft)" }}>
                Recette totale
              </div>
              <div className="text-2xl font-semibold mt-1">{formatMoney(overview.revenue_total_tnd)}</div>
              <div className="text-sm mt-1" style={{ color: "var(--ink-soft)" }}>
                {formatMoney(overview.revenue_last_30d_tnd)} sur les 30 derniers jours
              </div>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <WeeklyBarChart
              title="Nouveaux restaurants par semaine"
              points={overview.weekly}
              valueOf={(p) => p.restaurants_created}
              color="var(--menthe)"
              emptyMessage="Aucune inscription sur les 12 dernières semaines."
            />
            <WeeklyBarChart
              title="Commandes par semaine"
              points={overview.weekly}
              valueOf={(p) => p.orders_count}
              color="var(--harissa)"
              emptyMessage="Aucune commande sur les 12 dernières semaines."
            />
          </div>

          <Card padding="md">
            <h2 className="font-semibold mb-3">Par restaurant</h2>
            {overview.restaurants.length === 0 ? (
              <EmptyState message="Aucun restaurant client pour l'instant." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left" style={{ color: "var(--ink-soft)" }}>
                      <th className="font-normal pb-2 pr-3">Restaurant</th>
                      <th className="font-normal pb-2 pr-3">Palier</th>
                      <th className="font-normal pb-2 pr-3">Inscrit le</th>
                      <th className="font-normal pb-2 pr-3">Commandes</th>
                      <th className="font-normal pb-2 pr-3">Recette</th>
                      <th className="font-normal pb-2">Dernière commande</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.restaurants.map((r) => (
                      <tr key={r.id} className="border-t" style={{ borderColor: "var(--line)" }}>
                        <td className="py-2 pr-3 font-medium">{r.name}</td>
                        <td className="py-2 pr-3">
                          <Badge tone="neutral">{TIER_LABELS[r.subscription_tier]}</Badge>
                        </td>
                        <td className="py-2 pr-3">{formatDate(r.created_at)}</td>
                        <td className="py-2 pr-3">{r.orders_count}</td>
                        <td className="py-2 pr-3">{formatMoney(r.revenue_tnd)}</td>
                        <td className="py-2">{r.last_order_at ? formatDate(r.last_order_at) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
