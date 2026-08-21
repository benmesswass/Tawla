"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError, type AdminRestaurant } from "@/lib/api";
import { getAdminSecret, setAdminSecret, clearAdminSecret } from "@/lib/adminAuth";
import { toFrenchMessage } from "@/lib/errors";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import TawlaMark from "@/components/brand/TawlaMark";

const TIER_LABELS: Record<string, string> = { essentiel: "Essentiel", pro: "Pro", business: "Business" };

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" });
}

/**
 * Écran admin (2026-08-20) : Wassim seul, secret unique partagé (voir
 * lib/adminAuth.ts et backend app/modules/admin/router.py). Pas un compte,
 * pas un rôle — juste un mot de passe qu'il garde pour lui. Sert à poser une
 * dérogation `promo_gratuit` sur un restaurant précis, le seul moyen d'avoir
 * un accès gratuit à Tawla maintenant qu'Essentiel n'est plus jamais offert
 * par défaut à l'inscription.
 */
export default function AdminPage() {
  const [secretInput, setSecretInput] = useState("");
  const [secret, setSecret] = useState<string | null>(null);
  const [restaurants, setRestaurants] = useState<AdminRestaurant[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);

  useEffect(() => {
    setSecret(getAdminSecret());
  }, []);

  const load = useCallback(async (s: string) => {
    setLoading(true);
    setError(null);
    try {
      const list = await api.adminListRestaurants(s);
      setRestaurants(list);
    } catch (e) {
      if (e instanceof ApiError && e.code === "INVALID_ADMIN_SECRET") {
        clearAdminSecret();
        setSecret(null);
        setError("Secret incorrect.");
      } else {
        setError(toFrenchMessage(e));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (secret) load(secret);
  }, [secret, load]);

  function handleSubmitSecret(e: FormEvent) {
    e.preventDefault();
    const trimmed = secretInput.trim();
    if (!trimmed) return;
    setAdminSecret(trimmed);
    setSecret(trimmed);
  }

  async function togglePromo(restaurant: AdminRestaurant) {
    if (!secret) return;
    setSavingId(restaurant.id);
    setError(null);
    try {
      const updated = await api.adminSetPromo(secret, restaurant.id, !restaurant.promo_gratuit);
      setRestaurants((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    } catch (e) {
      setError(toFrenchMessage(e));
    } finally {
      setSavingId(null);
    }
  }

  if (!secret) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "var(--semoule)" }}>
        <form
          onSubmit={handleSubmitSecret}
          className="w-full max-w-sm rounded-xl p-6 space-y-3"
          style={{ background: "var(--semoule-raised)", border: "1px solid var(--line)" }}
        >
          <div className="flex flex-col items-center gap-2 pb-1">
            <TawlaMark size={36} />
            <h1 className="text-base font-semibold" style={{ color: "var(--encre)" }}>
              Admin Tawla
            </h1>
          </div>
          {error && <p className="text-sm text-red-600 text-center">{error}</p>}
          <input
            type="password"
            required
            autoFocus
            value={secretInput}
            onChange={(e) => setSecretInput(e.target.value)}
            placeholder="Secret admin"
            className="w-full rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-[var(--harissa)]/40"
            style={{ border: "1px solid var(--line)", background: "white" }}
          />
          <Button type="submit" className="w-full">
            Entrer
          </Button>
        </form>
      </div>
    );
  }

  return (
    <div className="p-4 max-w-4xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold" style={{ color: "var(--encre)" }}>
          Restaurants
        </h1>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            clearAdminSecret();
            setSecret(null);
          }}
        >
          Se déconnecter
        </Button>
      </div>

      {error && (
        <Card tone="danger" padding="sm" className="text-sm text-red-700">
          {error}
        </Card>
      )}

      {loading && restaurants.length === 0 ? (
        <p className="text-sm" style={{ color: "var(--ink-soft)" }}>
          Chargement…
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left border-b" style={{ borderColor: "var(--line)" }}>
                <th className="py-2 pe-3">Établissement</th>
                <th className="py-2 pe-3">Palier</th>
                <th className="py-2 pe-3">Échéance</th>
                <th className="py-2 pe-3">Statut</th>
                <th className="py-2 pe-3">Promo</th>
                <th className="py-2 pe-3"></th>
              </tr>
            </thead>
            <tbody>
              {restaurants.map((r) => (
                <tr key={r.id} className="border-b" style={{ borderColor: "var(--line)" }}>
                  <td className="py-2 pe-3">
                    <div className="font-medium" style={{ color: "var(--encre)" }}>
                      {r.name}
                    </div>
                    <div className="text-xs" style={{ color: "var(--ink-soft)" }}>
                      {r.slug}
                    </div>
                  </td>
                  <td className="py-2 pe-3">{TIER_LABELS[r.subscription_tier] ?? r.subscription_tier}</td>
                  <td className="py-2 pe-3">
                    {r.subscription_period_end ? formatDate(r.subscription_period_end) : "—"}
                  </td>
                  <td className="py-2 pe-3">
                    <Badge tone={r.is_active || r.promo_gratuit ? "success" : "danger"}>
                      {r.is_active || r.promo_gratuit ? "Actif" : "Bloqué"}
                    </Badge>
                  </td>
                  <td className="py-2 pe-3">
                    <Badge tone={r.promo_gratuit ? "info" : "neutral"}>{r.promo_gratuit ? "Oui" : "Non"}</Badge>
                  </td>
                  <td className="py-2 pe-3">
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={savingId === r.id}
                      onClick={() => togglePromo(r)}
                    >
                      {r.promo_gratuit ? "Retirer la promo" : "Offrir"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
