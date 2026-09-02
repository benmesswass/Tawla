"use client";

import { useState } from "react";
import { api, type Restaurant, type SubscriptionTier } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { trackEvent } from "@/lib/analytics";
import { TIERS, estimateUpgradeProration } from "@/lib/offer";
import { currentMarket } from "@/lib/market";
import { sessionDemo } from "@/lib/visite/etat";
import { useSubscriptionCheckout } from "@/lib/useSubscriptionCheckout";
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
  restaurant,
  onClose,
  onUpgraded,
}: {
  restaurantId: number;
  requiredTier: SubscriptionTier;
  // Facultatif : sert uniquement à estimer le prorata d'un upgrade EN COURS
  // d'abonnement (retour utilisateur, 2026-09-02) — absent, la modale reste
  // utilisable telle quelle (premier abonnement, prix plein).
  restaurant?: Restaurant;
  onClose: () => void;
  onUpgraded: (restaurant: Restaurant) => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Avant le `if (!tier) return null;` ci-dessous : un hook ne peut pas
  // être appelé après un retour anticipé (Rules of Hooks).
  const { openPaymentTab, goToPayment } = useSubscriptionCheckout(
    restaurantId,
    (r) => {
      onUpgraded(r);
      onClose();
    },
    (e) => setError(toFrenchMessage(e))
  );

  const tier = TIERS.find((t) => t.id === requiredTier);
  if (!tier) return null; // "essentiel" n'atterrit jamais ici (jamais un required_tier)

  const currentTier = restaurant && TIERS.find((t) => t.id === restaurant.subscription_tier);
  const proration =
    restaurant?.stripe_subscription_active && restaurant.subscription_period_end && currentTier
      ? estimateUpgradeProration(currentTier.priceDT, tier.priceDT, restaurant.subscription_period_end)
      : null;
  // `restaurant` est facultatif (voir sa docstring) — absent depuis
  // dashboard/equipe et dashboard/preuve, qui n'ont que le `restaurantId`.
  // `sessionDemo()` (déjà lu plus bas pour le tracking) reste le seul signal
  // disponible dans ce cas — retour utilisateur, 2026-09-02 bis : "active
  // tout même pour la démo" ne doit pas dépendre de QUEL écran a ouvert
  // cette modale.
  const isDemo = restaurant ? Boolean(restaurant.is_demo) : Boolean(sessionDemo());

  async function handleUpgrade() {
    trackEvent("upgrade_clicked", { target_tier: requiredTier, is_demo: Boolean(sessionDemo()) });
    setSubmitting(true);
    setError(null);
    const paymentTab = openPaymentTab();
    try {
      const result = await api.startSubscriptionCheckout(restaurantId, requiredTier);
      if (result.pay_url) {
        goToPayment(paymentTab, result.pay_url);
        return;
      }
      paymentTab?.close();
      if (result.restaurant) onUpgraded(result.restaurant);
      onClose();
    } catch (e) {
      paymentTab?.close();
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
          <span className="text-2xl font-semibold text-[var(--encre)] tabular-nums">
            {tier.priceDT} {currentMarket.currency.symbol}
          </span>
          <span className="text-sm text-[var(--ink-soft)]"> / mois</span>
        </p>
        {proration !== null && (
          // Argument de vente (retour utilisateur, 2026-09-02 : "c'est bien
          // pour vendre") : l'upgrade ne recommence pas le mois, il ne
          // facture QUE le prorata des jours restants — un manager qui voit
          // "89€/mois" en fin de cycle peut hésiter à tort en pensant payer
          // ce plein tarif dès aujourd'hui.
          <p
            className="mt-1.5 text-sm font-medium rounded px-2 py-1 inline-block"
            style={{ backgroundColor: "rgba(31,107,79,.1)", color: "var(--menthe)" }}
          >
            Vous ne payez que ~{proration} {currentMarket.currency.symbol} aujourd&apos;hui (le prorata des jours
            restants) — {tier.priceDT} {currentMarket.currency.symbol}/mois à partir du prochain prélèvement.
          </p>
        )}
        {isDemo ? (
          // Établissement de démo (jetable, purgé sous 2h) : le backend
          // force le mode simulé quel que soit PAYMENT_MODE (retour
          // utilisateur, 2026-09-02) — jamais le texte de prélèvement réel
          // ci-dessous, qui décrirait un engagement qui n'a pas lieu.
          <p className="text-xs text-[var(--ink-soft)] mt-1">Simulation — aucun prélèvement réel en démo.</p>
        ) : (
          currentMarket.paymentProvider === "stripe" && (
            // Abonnement RÉCURRENT (mode Netflix, 2026-09-02) : le prélèvement
            // se répète tout seul chaque mois jusqu'à annulation — jamais
            // laisser croire à un paiement unique, un manager pourrait
            // s'engager sans le savoir (retour utilisateur, 2026-09-02 :
            // "ça peut coûter de l'argent ce genre d'erreur").
            <p className="text-xs text-[var(--ink-soft)] mt-1">
              Prélevé automatiquement chaque mois, résiliable à tout moment depuis votre portail d&apos;abonnement.
            </p>
          )
        )}
        <ul className="mt-3 space-y-1 text-sm text-[var(--ink-soft)]">
          {tier.features.map((feature) => (
            <li key={feature}>• {feature}</li>
          ))}
        </ul>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <div className="mt-5 flex flex-col gap-2">
          <Button onClick={handleUpgrade} disabled={submitting}>
            {submitting
              ? "Paiement en cours…"
              : isDemo
                ? `Simuler ${tier.name}`
                : proration !== null
                  ? `Passer à ${tier.name} — ${proration} ${currentMarket.currency.symbol} aujourd'hui`
                  : currentMarket.paymentProvider === "stripe"
                    ? `S'abonner à ${tier.name} — ${tier.priceDT} ${currentMarket.currency.symbol}/mois`
                    : `Passer à ${tier.name} — ${tier.priceDT} ${currentMarket.currency.symbol}/mois`}
          </Button>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Plus tard
          </Button>
        </div>
      </div>
    </div>
  );
}
