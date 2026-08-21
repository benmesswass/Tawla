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
  type LaunchCampaign,
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
  const [campaign, setCampaign] = useState<LaunchCampaign | null>(null);
  const [discountInput, setDiscountInput] = useState("");
  const [maxGrantsInput, setMaxGrantsInput] = useState("");
  const [savingCampaign, setSavingCampaign] = useState(false);
  const [savingPromoId, setSavingPromoId] = useState<number | null>(null);
  const [promoDrafts, setPromoDrafts] = useState<Record<number, { discount: string; days: string }>>({});
  const [error, setError] = useState<string | null>(null);
  const [checkedAuth, setCheckedAuth] = useState(false);
  const [newAdminEmail, setNewAdminEmail] = useState("");
  const [newAdminName, setNewAdminName] = useState("");
  const [newAdminPassword, setNewAdminPassword] = useState("");
  const [savingNewAdmin, setSavingNewAdmin] = useState(false);
  const [newAdminMessage, setNewAdminMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [data, campaignData] = await Promise.all([
        platformAdminApi.getOverview(),
        platformAdminApi.getLaunchCampaign(),
      ]);
      setOverview(data);
      setCampaign(campaignData);
      setDiscountInput(String(campaignData.discount_percent));
      setMaxGrantsInput(String(campaignData.max_grants));
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

  async function handleSaveCampaign() {
    const discount = Number(discountInput);
    const maxGrants = Number(maxGrantsInput);
    if (!Number.isInteger(discount) || discount < 0 || discount > 100) return;
    if (!Number.isInteger(maxGrants) || maxGrants < 0) return;
    setSavingCampaign(true);
    setError(null);
    try {
      const updated = await platformAdminApi.setLaunchCampaign(discount, maxGrants);
      setCampaign(updated);
    } catch {
      setError(errorMessage());
    } finally {
      setSavingCampaign(false);
    }
  }

  async function handleSetPromo(restaurantId: number, discountPercent: number, durationDays: number) {
    setSavingPromoId(restaurantId);
    setError(null);
    try {
      await platformAdminApi.setRestaurantPromo(restaurantId, discountPercent, durationDays);
      await load();
    } catch {
      setError(errorMessage());
    } finally {
      setSavingPromoId(null);
    }
  }

  function handleGrantPromo(restaurantId: number) {
    const draft = promoDrafts[restaurantId];
    const discount = Number(draft?.discount ?? "100");
    const days = Number(draft?.days ?? "30");
    if (!Number.isInteger(discount) || discount < 0 || discount > 100) return;
    if (!Number.isInteger(days) || days < 1) return;
    handleSetPromo(restaurantId, discount, days);
  }

  function handleLogout() {
    clearAdminToken();
    router.replace("/admin/login");
  }

  async function handleCreateAdmin() {
    if (!newAdminEmail.trim() || !newAdminName.trim() || newAdminPassword.length < 8) return;
    setSavingNewAdmin(true);
    setNewAdminMessage(null);
    setError(null);
    try {
      const created = await platformAdminApi.createAdmin(newAdminEmail.trim(), newAdminName.trim(), newAdminPassword);
      setNewAdminMessage(`Compte créé : ${created.email}`);
      setNewAdminEmail("");
      setNewAdminName("");
      setNewAdminPassword("");
    } catch {
      setError(errorMessage());
    } finally {
      setSavingNewAdmin(false);
    }
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

          {campaign && (
            <div className="mb-6">
              <Card padding="md">
                <div className="flex items-start justify-between gap-4 flex-wrap mb-3">
                  <div>
                    <h2 className="font-semibold">Offre de lancement</h2>
                    <p className="text-sm mt-1" style={{ color: "var(--ink-soft)" }}>
                      Réduction automatique sur le premier mois Essentiel, pour les N premières inscriptions.
                    </p>
                  </div>
                  <Badge tone="neutral">{campaign.grants_used}/{campaign.max_grants} déjà utilisés</Badge>
                </div>
                <div className="flex items-end gap-4 flex-wrap">
                  <div className="space-y-1">
                    <label htmlFor="discountPercent" className="text-xs font-medium block" style={{ color: "var(--ink-soft)" }}>
                      Réduction (%)
                    </label>
                    <input
                      id="discountPercent"
                      type="range"
                      min={0}
                      max={100}
                      step={5}
                      value={discountInput}
                      onChange={(e) => setDiscountInput(e.target.value)}
                      className="w-40 align-middle"
                    />
                    <span className="ms-2 text-sm font-medium tabular-nums">{discountInput}%</span>
                  </div>
                  <div className="space-y-1">
                    <label htmlFor="maxGrants" className="text-xs font-medium block" style={{ color: "var(--ink-soft)" }}>
                      Nombre de restaurants
                    </label>
                    <input
                      id="maxGrants"
                      type="number"
                      min={0}
                      value={maxGrantsInput}
                      onChange={(e) => setMaxGrantsInput(e.target.value)}
                      className="w-24 rounded-lg px-2 py-1 text-sm"
                      style={{ border: "1px solid var(--line)" }}
                    />
                  </div>
                  <Button size="sm" onClick={handleSaveCampaign} disabled={savingCampaign}>
                    {savingCampaign ? "Enregistrement…" : "Enregistrer"}
                  </Button>
                </div>
                <p className="text-xs mt-3" style={{ color: "var(--ink-soft)" }}>
                  S&apos;applique aux prochaines inscriptions — n&apos;affecte jamais un restaurant déjà inscrit.
                </p>
              </Card>
            </div>
          )}

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
                      <th className="font-normal pb-2 pr-3">Statut</th>
                      <th className="font-normal pb-2 pr-3">Inscrit le</th>
                      <th className="font-normal pb-2 pr-3">Commandes</th>
                      <th className="font-normal pb-2 pr-3">Recette</th>
                      <th className="font-normal pb-2 pr-3">Dernière commande</th>
                      <th className="font-normal pb-2 pr-3">Ouvertures (7j)</th>
                      <th className="font-normal pb-2">Promo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.restaurants.map((r) => (
                      <tr key={r.id} className="border-t" style={{ borderColor: "var(--line)" }}>
                        <td className="py-2 pr-3 font-medium">{r.name}</td>
                        <td className="py-2 pr-3">
                          <Badge tone="neutral">{TIER_LABELS[r.effective_tier]}</Badge>
                        </td>
                        <td className="py-2 pr-3">
                          <div className="flex flex-wrap gap-1">
                            <Badge tone={r.is_active ? "success" : "danger"}>
                              {r.is_active ? "Actif" : "Bloqué"}
                            </Badge>
                            {!r.has_paid_for_subscription && <Badge tone="info">Jamais payé</Badge>}
                          </div>
                        </td>
                        <td className="py-2 pr-3">{formatDate(r.created_at)}</td>
                        <td className="py-2 pr-3">{r.orders_count}</td>
                        <td className="py-2 pr-3">{formatMoney(r.revenue_tnd)}</td>
                        <td className="py-2 pr-3">{r.last_order_at ? formatDate(r.last_order_at) : "—"}</td>
                        <td className="py-2 pr-3">
                          {r.dashboard_views_last_7d === 0 ? (
                            <Badge tone="warning">Inactif</Badge>
                          ) : (
                            r.dashboard_views_last_7d
                          )}
                        </td>
                        <td className="py-2">
                          {r.custom_promo_discount_percent !== null && r.custom_promo_ends_at ? (
                            <div className="flex items-center gap-2">
                              <Badge tone="info">
                                {r.custom_promo_discount_percent}% jusqu&apos;au {formatDate(r.custom_promo_ends_at)}
                              </Badge>
                              <Button
                                variant="secondary"
                                size="sm"
                                disabled={savingPromoId === r.id}
                                onClick={() => handleSetPromo(r.id, 0, 0)}
                              >
                                Retirer
                              </Button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1">
                              <input
                                type="number"
                                min={0}
                                max={100}
                                aria-label={`Réduction (%) — ${r.name}`}
                                className="w-14 rounded px-1 py-0.5 text-sm"
                                style={{ border: "1px solid var(--line)" }}
                                value={promoDrafts[r.id]?.discount ?? "100"}
                                onChange={(e) =>
                                  setPromoDrafts((d) => ({
                                    ...d,
                                    [r.id]: { discount: e.target.value, days: d[r.id]?.days ?? "30" },
                                  }))
                                }
                              />
                              <span className="text-xs" style={{ color: "var(--ink-soft)" }}>%</span>
                              <input
                                type="number"
                                min={1}
                                aria-label={`Durée (jours) — ${r.name}`}
                                className="w-14 rounded px-1 py-0.5 text-sm"
                                style={{ border: "1px solid var(--line)" }}
                                value={promoDrafts[r.id]?.days ?? "30"}
                                onChange={(e) =>
                                  setPromoDrafts((d) => ({
                                    ...d,
                                    [r.id]: { discount: d[r.id]?.discount ?? "100", days: e.target.value },
                                  }))
                                }
                              />
                              <span className="text-xs" style={{ color: "var(--ink-soft)" }}>j</span>
                              <Button
                                size="sm"
                                disabled={savingPromoId === r.id}
                                onClick={() => handleGrantPromo(r.id)}
                              >
                                Offrir
                              </Button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <div className="mt-6">
            <Card padding="md">
              <h2 className="font-semibold mb-1">Comptes admin</h2>
              <p className="text-sm mb-3" style={{ color: "var(--ink-soft)" }}>
                Ouvre l&apos;accès à ce tableau de bord à quelqu&apos;un d&apos;autre — jamais un compte
                restaurateur, seulement l&apos;opérateur de la plateforme.
              </p>
              {newAdminMessage && (
                <Card tone="success" padding="sm" className="mb-3 text-sm">
                  {newAdminMessage}
                </Card>
              )}
              <div className="flex items-end gap-3 flex-wrap">
                <div className="space-y-1">
                  <label htmlFor="newAdminEmail" className="text-xs font-medium block" style={{ color: "var(--ink-soft)" }}>
                    E-mail
                  </label>
                  <input
                    id="newAdminEmail"
                    type="email"
                    value={newAdminEmail}
                    onChange={(e) => setNewAdminEmail(e.target.value)}
                    className="rounded-lg px-2 py-1 text-sm"
                    style={{ border: "1px solid var(--line)" }}
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="newAdminName" className="text-xs font-medium block" style={{ color: "var(--ink-soft)" }}>
                    Nom
                  </label>
                  <input
                    id="newAdminName"
                    type="text"
                    value={newAdminName}
                    onChange={(e) => setNewAdminName(e.target.value)}
                    className="rounded-lg px-2 py-1 text-sm"
                    style={{ border: "1px solid var(--line)" }}
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="newAdminPassword" className="text-xs font-medium block" style={{ color: "var(--ink-soft)" }}>
                    Mot de passe
                  </label>
                  <input
                    id="newAdminPassword"
                    type="password"
                    value={newAdminPassword}
                    onChange={(e) => setNewAdminPassword(e.target.value)}
                    className="rounded-lg px-2 py-1 text-sm"
                    style={{ border: "1px solid var(--line)" }}
                  />
                </div>
                <Button size="sm" disabled={savingNewAdmin} onClick={handleCreateAdmin}>
                  {savingNewAdmin ? "Création…" : "Créer"}
                </Button>
              </div>
              <p className="text-xs mt-3" style={{ color: "var(--ink-soft)" }}>
                8 caractères minimum. Un e-mail déjà utilisé met juste à jour le mot de passe et le nom.
              </p>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
