"use client";

import { useState } from "react";
import { api, type Restaurant, type SubscriptionTier } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { TIERS } from "@/lib/offer";
import Button from "@/components/ui/Button";

/**
 * Écran d'incitation à passer au palier supérieur, affiché à la place du
 * simple bandeau d'erreur quand une action gérée par palier renvoie
 * `UPGRADE_REQUIRED` (paiement en ligne du passage à un palier supérieur,
 * 2026-08-19). Reprend la liste de fonctionnalités déjà écrite pour la page
 * tarifaire publique (`lib/offer.ts`) — c'est déjà l'« exemple rapide » de ce
 * que débloque le palier, pas la peine d'en inventer un second texte par
 * fonctionnalité bloquée.
 */
export default function UpgradeModal({
  restaurantId,
  requiredTier,
  onClose,
  onUpgraded,
}: {
  restaurantId: number;
  requiredTier: SubscriptionTier;
  onClose: () => void;
  onUpgraded: (restaurant: Restaurant) => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const tier = TIERS.find((t) => t.id === requiredTier);
  if (!tier) return null; // "essentiel" n'atterrit jamais ici (jamais un required_tier)

  async function handleUpgrade() {
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.startSubscriptionCheckout(restaurantId, requiredTier);
      if (result.mode === "konnect" && result.pay_url) {
        window.location.href = result.pay_url;
        return;
      }
      if (result.restaurant) onUpgraded(result.restaurant);
      onClose();
    } catch (e) {
      setError(toFrenchMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-sm rounded-xl bg-white p-5 shadow-lg">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--harissa)]">
          Palier {tier.name} requis
        </p>
        <h2 className="mt-1 text-lg font-semibold text-[var(--encre)]">{tier.tagline}</h2>
        <p className="mt-3">
          <span className="text-2xl font-semibold text-[var(--encre)] tabular-nums">{tier.priceDT} DT</span>
          <span className="text-sm text-[var(--ink-soft)]"> / mois</span>
        </p>
        <ul className="mt-3 space-y-1 text-sm text-[var(--ink-soft)]">
          {tier.features.map((feature) => (
            <li key={feature}>• {feature}</li>
          ))}
        </ul>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <div className="mt-5 flex flex-col gap-2">
          <Button onClick={handleUpgrade} disabled={submitting}>
            {submitting ? "Paiement en cours…" : `Passer à ${tier.name} — ${tier.priceDT} DT/mois`}
          </Button>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Plus tard
          </Button>
        </div>
      </div>
    </div>
  );
}
