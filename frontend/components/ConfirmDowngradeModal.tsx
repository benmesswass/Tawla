"use client";

import { type SubscriptionTier } from "@/lib/api";
import { TIERS } from "@/lib/offer";
import { lalezar } from "@/lib/fonts";
import Button from "@/components/ui/Button";

/**
 * Confirmation avant de programmer une rétrogradation — remplace le
 * `window.confirm()` natif du navigateur (retour utilisateur, 2026-09-02 :
 * "on peut pas plutôt créer une modale propre à Tawla ?"), même famille
 * visuelle que WelcomeTierModal/UpgradeModal plutôt qu'un style figé par le
 * navigateur.
 */
export default function ConfirmDowngradeModal({
  tier,
  periodEndLabel,
  isDemo = false,
  submitting,
  onConfirm,
  onCancel,
}: {
  tier: SubscriptionTier;
  // Déjà formatée (formatDate côté appelant) — cette modale n'a pas besoin
  // de connaître le format de date de la page qui l'ouvre.
  periodEndLabel: string;
  // Établissement de démo : appliqué immédiatement (2026-09-02 bis, "active
  // tout même pour la démo") — jamais le texte "effectif à la prochaine
  // échéance", qui décrirait un délai qui n'existe pas en simulation.
  isDemo?: boolean;
  submitting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const info = TIERS.find((t) => t.id === tier);
  if (!info) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--laiton)]">Rétrogradation</p>
        <h2 className={`${lalezar.className} mt-1 text-2xl text-[var(--encre)]`}>
          {isDemo ? `Simuler ${info.name} ?` : `Passer à ${info.name} ?`}
        </h2>
        <p className="mt-2 text-sm text-[var(--ink-soft)]">
          {isDemo ? (
            "Simulation — appliqué immédiatement, aucun prélèvement réel."
          ) : (
            <>
              Effectif à la prochaine échéance, le <strong>{periodEndLabel}</strong> — vous gardez votre palier
              actuel et tous ses avantages jusque-là, aucun remboursement à calculer. Vous pouvez changer d&apos;avis
              à tout moment avant cette date.
            </>
          )}
        </p>

        <div className="mt-5 flex flex-col gap-2">
          <Button variant="laiton" onClick={onConfirm} disabled={submitting}>
            {submitting
              ? "En cours…"
              : isDemo
                ? `Simuler ${info.name}`
                : `Confirmer — ${info.name} à partir du ${periodEndLabel}`}
          </Button>
          <Button variant="secondary" onClick={onCancel} disabled={submitting}>
            Annuler
          </Button>
        </div>
      </div>
    </div>
  );
}
