"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Restaurant } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { clearToken } from "@/lib/auth";
import { TIERS } from "@/lib/offer";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import TawlaMark from "@/components/brand/TawlaMark";

/**
 * Écran BLOQUANT (pas une modale dismissible comme UpgradeModal) affiché à la
 * place du dashboard tant que `Restaurant.is_active`/`promo_gratuit` sont
 * tous les deux faux (2026-08-20) : Essentiel n'est jamais gratuit, y
 * compris pour un compte inscrit en self-service (voir CLAUDE.md et
 * backend app/modules/staff/router.py::register).
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

  const tier = TIERS.find((t) => t.id === "essentiel");
  // Offre de lancement (2026-08-21) : réduction figée à l'inscription de ce
  // restaurant (voir Restaurant.launch_promo_discount_percent) — jamais la
  // campagne en cours, qui a pu changer depuis. `is_active` est déjà faux
  // ici (sinon cet écran ne s'afficherait pas), donc la réduction s'applique
  // encore — même règle que essentiel_price_tnd() côté backend.
  const basePrice = tier?.priceDT ?? 50;
  const price =
    restaurant.launch_promo_discount_percent != null
      ? Math.round((basePrice * (100 - restaurant.launch_promo_discount_percent)) / 100)
      : basePrice;

  async function handlePay() {
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.startSubscriptionCheckout(restaurant.id, "essentiel");
      if (result.mode === "konnect" && result.pay_url) {
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
                  {basePrice} DT
                </span>
              )}
              <span className="text-2xl font-semibold tabular-nums" style={{ color: "var(--encre)" }}>
                {price} DT
              </span>
              <span className="text-sm" style={{ color: "var(--ink-soft)" }}> / mois</span>
            </p>
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
            {submitting ? "Paiement en cours…" : `Payer ${price} DT pour activer`}
          </Button>
          <Button variant="secondary" onClick={handleLogout} disabled={submitting}>
            Se déconnecter
          </Button>
        </div>
      </Card>
    </div>
  );
}
