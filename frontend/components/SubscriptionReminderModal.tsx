"use client";

import { useState } from "react";
import { api, type Restaurant } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import Button from "@/components/ui/Button";
import { TIERS } from "@/lib/offer";
import { currentMarket } from "@/lib/market";

function daysRemaining(periodEnd: string): number {
  const ms = new Date(periodEnd).getTime() - Date.now();
  return Math.max(0, Math.ceil(ms / (1000 * 60 * 60 * 24)));
}

/**
 * Rappel de paiement (offre de lancement, 2026-08-21) : affiché à CHAQUE
 * connexion tant que le restaurant profite d'un accès actif sans avoir
 * jamais payé (`has_paid_for_subscription` faux, que l'activation vienne de
 * l'offre de lancement ou d'une promo personnalisée posée par l'admin) —
 * jamais mémorisé en local, contrairement à une modale qu'on ferme
 * une fois pour toutes : Wassim veut un rappel flagrant, pas discret. Le
 * bouton payer doit fonctionner MÊME pendant le mois gratuit — voir
 * start_subscription_checkout, qui autorise désormais Essentiel à tout
 * moment (paiement anticipé = prolongation, jamais un refus).
 */
export default function SubscriptionReminderModal({
  restaurant,
  onPaid,
  onDismiss,
}: {
  restaurant: Restaurant;
  onPaid: (restaurant: Restaurant) => void;
  onDismiss: () => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const days = restaurant.subscription_period_end ? daysRemaining(restaurant.subscription_period_end) : null;
  const price = TIERS.find((t) => t.id === restaurant.subscription_tier)?.priceDT ?? 50;

  async function handlePay() {
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.startSubscriptionCheckout(restaurant.id, restaurant.subscription_tier);
      if (result.mode === "konnect" && result.pay_url) {
        window.location.href = result.pay_url;
        return;
      }
      if (result.restaurant) onPaid(result.restaurant);
    } catch (e) {
      setError(toFrenchMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-sm rounded-xl bg-white p-5 shadow-lg text-center">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--harissa)]">Offre de lancement</p>
        <h2 className="mt-1 text-lg font-semibold text-[var(--encre)]">
          {days !== null && days > 0
            ? `Il vous reste ${days} jour${days > 1 ? "s" : ""} de mois gratuit`
            : "Votre mois gratuit touche à sa fin"}
        </h2>
        <p className="mt-2 text-sm text-[var(--ink-soft)]">
          Passez au paiement maintenant pour ne jamais perdre l&apos;accès à votre carte, vos tables et vos
          commandes.
        </p>
        <p className="mt-3">
          <span className="text-2xl font-semibold text-[var(--encre)] tabular-nums">
            {price} {currentMarket.currency.symbol}
          </span>
          <span className="text-sm text-[var(--ink-soft)]"> / mois</span>
        </p>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <div className="mt-5 flex flex-col gap-2">
          <Button onClick={handlePay} disabled={submitting}>
            {submitting ? "Paiement en cours…" : "Payer maintenant"}
          </Button>
          <Button variant="secondary" onClick={onDismiss} disabled={submitting}>
            Plus tard
          </Button>
        </div>
      </div>
    </div>
  );
}
