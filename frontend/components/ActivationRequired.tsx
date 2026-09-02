"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Restaurant } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { clearToken } from "@/lib/auth";
import { TIERS } from "@/lib/offer";
import { currentMarket } from "@/lib/market";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import TawlaMark from "@/components/brand/TawlaMark";

/**
 * Écran BLOQUANT (pas une modale dismissible comme UpgradeModal) affiché à la
 * place du dashboard tant que `Restaurant.is_active` est faux (2026-08-20) :
 * Essentiel n'est jamais gratuit, y compris pour un compte inscrit en
 * self-service (voir CLAUDE.md et backend app/modules/staff/router.py::register).
 */
export default function ActivationRequired({
  restaurant,
  onActivated,
}: {
  restaurant: Restaurant;
  onActivated: (restaurant: Restaurant) => void;
}) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const tier = TIERS.find((t) => t.id === restaurant.subscription_tier);
  // Offre de lancement (2026-08-21) : réduction figée à l'inscription de ce
  // restaurant (voir Restaurant.launch_promo_discount_percent), pour le
  // palier qu'il avait choisi À CE MOMENT-LÀ (`restaurant.subscription_tier`)
  // — jamais la campagne en cours, qui a pu changer depuis. `is_active` est
  // déjà faux ici (sinon cet écran ne s'afficherait pas), donc la réduction
  // s'applique encore — même règle que tier_price_tnd() côté backend.
  const basePrice = tier?.priceDT ?? 50;
  const price =
    restaurant.launch_promo_discount_percent != null
      ? Math.round((basePrice * (100 - restaurant.launch_promo_discount_percent)) / 100)
      : basePrice;

  async function handlePay() {
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.startSubscriptionCheckout(restaurant.id, restaurant.subscription_tier);
      if (result.pay_url) {
        window.location.href = result.pay_url;
        return;
      }
      if (result.restaurant) onActivated(result.restaurant);
    } catch (e) {
      setError(toFrenchMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: "var(--semoule)" }}>
      <Card padding="md" className="w-full max-w-sm text-center">
        <div className="flex justify-center mb-3">
          <TawlaMark size={40} />
        </div>
        <h1 className="text-lg font-semibold" style={{ color: "var(--encre)" }}>
          Activez {restaurant.name}
        </h1>
        <p className="mt-2 text-sm" style={{ color: "var(--ink-soft)" }}>
          Votre établissement n&apos;est pas encore actif. La carte, les tables et les commandes restent bloquées
          tant que l&apos;abonnement n&apos;est pas payé.
        </p>

        {tier && (
          <>
            <p className="mt-4">
              {price < basePrice && (
                <span className="text-sm line-through me-2" style={{ color: "var(--ink-soft)" }}>
                  {basePrice} {currentMarket.currency.symbol}
                </span>
              )}
              <span className="text-2xl font-semibold tabular-nums" style={{ color: "var(--encre)" }}>
                {price} {currentMarket.currency.symbol}
              </span>
              <span className="text-sm" style={{ color: "var(--ink-soft)" }}> / mois</span>
            </p>
            {restaurant.is_demo ? (
              // Établissement de démo : jamais un vrai prélèvement, même ici
              // après une résiliation simulée (retour utilisateur,
              // 2026-09-02 bis : "active tout même pour la démo").
              <p className="text-xs mt-1" style={{ color: "var(--ink-soft)" }}>
                Simulation — aucun prélèvement réel en démo.
              </p>
            ) : (
              currentMarket.paymentProvider === "stripe" && (
                // Abonnement RÉCURRENT (mode Netflix, 2026-09-02) — même
                // divulgation que UpgradeModal/SubscriptionReminderModal.
                <p className="text-xs mt-1" style={{ color: "var(--ink-soft)" }}>
                  Prélevé automatiquement chaque mois, résiliable à tout moment depuis votre portail
                  d&apos;abonnement.
                </p>
              )
            )}
            <ul className="mt-3 space-y-1 text-sm text-left" style={{ color: "var(--ink-soft)" }}>
              {tier.features.map((feature) => (
                <li key={feature}>• {feature}</li>
              ))}
            </ul>
          </>
        )}

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <div className="mt-5 flex flex-col gap-2">
          <Button onClick={handlePay} disabled={submitting}>
            {submitting
              ? "Paiement en cours…"
              : restaurant.is_demo
                ? "Simuler l'activation"
                : `Payer ${price} ${currentMarket.currency.symbol} pour activer`}
          </Button>
          <Button variant="secondary" onClick={handleLogout} disabled={submitting}>
            Se déconnecter
          </Button>
        </div>
      </Card>
    </div>
  );
}
