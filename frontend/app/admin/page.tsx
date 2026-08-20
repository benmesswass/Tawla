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

function formatPercent(rate: number | null): string {
  return rate === null ? "—" : `${(rate * 100).toFixed(0)} %`;
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

function KpiTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card padding="md">
      <div className="text-xs uppercase tracking-wide" style={{ color: "var(--ink-soft)" }}>
        {label}
      </div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
      {sub && (
        <div className="text-sm mt-1" style={{ color: "var(--ink-soft)" }}>
          {sub}
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
      // Session invalide (jamais configurée, expirée après 12h, compte
      // désactivé) : le client a déjà effacé le token, il ne reste qu'à
      // repartir sur l'écran de connexion.
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
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    );
  }

  const maxWeeklySignups = Math.max(1, ...(overview?.weekly_signups.map((w) => w.restaurants_created) ?? [1]));

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
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <KpiTile
              label="Restaurants clients"
              value={String(overview.restaurants_total)}
              sub={`${overview.restaurants_created_last_30d} nouveaux sur 30 jours`}
            />

            <Card padding="md">
              <div className="text-xs uppercase tracking-wide" style={{ color: "var(--ink-soft)" }}>
                Répartition par palier
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {(Object.keys(TIER_LABELS) as SubscriptionTier[]).map((tier) => (
                  <Badge key={tier} tone="neutral">
                    {TIER_LABELS[tier]} · {overview.restaurants_by_tier[tier] ?? 0}
                  </Badge>
                ))}
              </div>
            </Card>

            <KpiTile
              label="MRR réel"
              value={formatMoney(overview.mrr_tnd)}
              sub={`${overview.paying_restaurants_count} restaurant(s) payant(s) en ligne`}
            />

            <KpiTile
              label="Rétention (7j)"
              value={String(overview.dashboard_views_last_7d)}
              sub={`${overview.restaurants_active_last_7d}/${overview.restaurants_total} restaurant(s) ont ouvert leur dashboard`}
            />

            <KpiTile
              label="Commandes (7j)"
              value={String(overview.orders_last_7d)}
              sub={`${formatMoney(overview.gmv_last_7d_tnd)} de GMV payé`}
            />

            <KpiTile
              label="Commandes perdues (7j)"
              value={formatPercent(overview.lost_orders_rate_last_7d)}
              sub="Même définition que côté manager"
            />
          </div>

          <div className="mb-6">
            <Card padding="md">
              <h2 className="font-semibold mb-3">Nouveaux restaurants par semaine</h2>
              {overview.weekly_signups.every((w) => w.restaurants_created === 0) ? (
                <EmptyState message="Aucune inscription sur les 12 dernières semaines." />
              ) : (
                <div className="flex items-end gap-1 h-28">
                  {overview.weekly_signups.map((w) => (
                    <div
                      key={w.week_start}
                      className="flex-1 flex flex-col items-center justify-end h-full"
                      title={`Semaine du ${formatWeekLabel(w.week_start)} — ${w.restaurants_created} restaurant(s)`}
                    >
                      <div
                        className="w-full bg-[var(--menthe)] rounded-t"
                        style={{
                          height: w.restaurants_created
                            ? `${(w.restaurants_created / maxWeeklySignups) * 100}%`
                            : "1px",
                        }}
                      />
                      <span className="text-[10px] mt-1" style={{ color: "var(--ink-soft)" }}>
                        {formatWeekLabel(w.week_start)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
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
                      <th className="font-normal pb-2 pr-3">Dernière commande</th>
                      <th className="font-normal pb-2">Ouvertures (7j)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.restaurants.map((r) => (
                      <tr key={r.id} className="border-t" style={{ borderColor: "var(--line)" }}>
                        <td className="py-2 pr-3 font-medium">{r.name}</td>
                        <td className="py-2 pr-3">
                          <Badge tone="neutral">{TIER_LABELS[r.effective_tier]}</Badge>
                        </td>
                        <td className="py-2 pr-3">{formatDate(r.created_at)}</td>
                        <td className="py-2 pr-3">{r.orders_count}</td>
                        <td className="py-2 pr-3">{formatMoney(r.revenue_tnd)}</td>
                        <td className="py-2 pr-3">{r.last_order_at ? formatDate(r.last_order_at) : "—"}</td>
                        <td className="py-2">
                          {r.dashboard_views_last_7d === 0 ? (
                            <Badge tone="warning">Inactif</Badge>
                          ) : (
                            r.dashboard_views_last_7d
                          )}
                        </td>
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
