"use client";

import { useState, useEffect } from "react";
import { type SubscriptionTier } from "@/lib/api";
import { TIERS } from "@/lib/offer";
import { lalezar } from "@/lib/fonts";
import Button from "@/components/ui/Button";
import { GiftIcon } from "@/components/icons";
import CelebrationOverlay from "@/components/CelebrationOverlay";

/**
 * Écran de bienvenue affiché juste après qu'un paiement de palier (ou son
 * équivalent démo) vient d'aboutir — remplace le simple message discret
 * (`flash()`) qui passait inaperçu (retour utilisateur, 2026-09-02). Reprend
 * la même liste de fonctionnalités que `UpgradeModal` (`lib/offer.ts`),
 * cette fois pour confirmer ce qui vient d'être débloqué plutôt que pour
 * inciter à l'achat — même ton festif que le badge "Palier activé", pas la
 * simple carte tarifaire réutilisée telle quelle (retour utilisateur,
 * 2026-09-02 : « côté design c'est très basique »). `CelebrationOverlay` et
 * `.animate-celebration-pop` existaient déjà (confettis de récompense
 * fidélité, `menu/[qrToken]/page.tsx`) — les réutiliser ici plutôt qu'écrire
 * une deuxième animation de célébration.
 */
export default function WelcomeTierModal({ tier, onClose }: { tier: SubscriptionTier; onClose: () => void }) {
  const info = TIERS.find((t) => t.id === tier);
  const [showConfetti, setShowConfetti] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setShowConfetti(false), 1800);
    return () => clearTimeout(timer);
  }, []);

  if (!info) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      {showConfetti && <CelebrationOverlay />}
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl text-center animate-celebration-pop">
        <div className="mx-auto w-16 h-16 rounded-full flex items-center justify-center border border-[rgba(31,107,79,.45)] bg-[rgba(31,107,79,.12)]">
          <GiftIcon className="w-8 h-8 text-[var(--menthe)]" />
        </div>
        <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-[var(--menthe)]">Palier activé</p>
        <h2 className={`${lalezar.className} mt-1 text-3xl text-[var(--encre)]`}>Bienvenue dans {info.name} !</h2>
        <p className="mt-2 text-sm text-[var(--ink-soft)]">Voici ce que vous pouvez faire dès maintenant :</p>

        <ul className="mt-4 space-y-2 text-left">
          {info.features.map((feature) => (
            <li key={feature} className="flex items-start gap-2 text-sm text-[var(--encre)]">
              <svg
                viewBox="0 0 24 24"
                className="w-4 h-4 mt-0.5 shrink-0 text-[var(--menthe)]"
                fill="none"
                stroke="currentColor"
                strokeWidth={3}
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M4 12l5 5L20 6" />
              </svg>
              <span>{feature}</span>
            </li>
          ))}
        </ul>

        <Button onClick={onClose} className="mt-6 w-full">
          C&apos;est parti
        </Button>
      </div>
    </div>
  );
}
