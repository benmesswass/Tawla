"use client";

import { useState } from "react";
import EnteteManager from "@/components/EnteteManager";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import { currentMarket } from "@/lib/market";
import Skeleton from "@/components/ui/Skeleton";
import Card from "@/components/ui/Card";

/**
 * Simulation de palier pour les démos commerciales (retour démo 2026-08-31,
 * point 1 remanié) : ne touche à rien du vrai produit — aucun appel API,
 * aucune donnée de restaurant réelle. Un manager choisit un palier, l'écran
 * grise/dévérouille les mêmes cartes que le vrai Réglages pour ce palier.
 *
 * Volontairement pas dans EnteteManager.PAGES : outil de vente pour Wassim,
 * pas une page que les restaurateurs doivent découvrir.
 *
 * Respecte le marché comme le vrai Réglages (dashboard/page.tsx) : le mode
 * Ramadan n'existe pas hors Tunisie, le paiement carte reste "Bientôt
 * disponible" tant que currentMarket.paymentProvider n'est pas "konnect" —
 * simuler un palier ne doit jamais faire apparaître une feature que le
 * marché a déjà exclue.
 */

type Tier = "essentiel" | "pro" | "business";

const TIER_RANK: Record<Tier, number> = { essentiel: 0, pro: 1, business: 2 };
const TIER_LABELS: Record<Tier, string> = {
  essentiel: "Essentiel (simulé)",
  pro: "Pro (simulé)",
  business: "Business (simulé)",
};

function LockBadge({ locked }: { locked: boolean }) {
  if (locked) {
    return (
      <span className="absolute top-2.5 right-2.5 flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full bg-[var(--encre)] text-[var(--semoule)]">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <rect x="5" y="11" width="14" height="9" rx="1.5" />
          <path d="M8 11V8a4 4 0 0 1 8 0v3" />
        </svg>
        Pro
      </span>
    );
  }
  return (
    <span className="absolute top-2.5 right-2.5 flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full bg-[#1f6b4f] text-white">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 12l5 5L20 6" />
      </svg>
      Inclus
    </span>
  );
}

function GatedCard({
  locked,
  children,
}: {
  locked: boolean;
  children: React.ReactNode;
}) {
  return (
    <Card tone="warning" padding="sm" className={`relative mb-3 transition-opacity ${locked ? "opacity-50 grayscale" : ""}`}>
      <LockBadge locked={locked} />
      {children}
    </Card>
  );
}

export default function DemoPaliersPage() {
  const { staff, loading: staffLoading } = useCurrentStaff(["manager"]);
  const [tier, setTier] = useState<Tier>("essentiel");

  if (staffLoading || !staff) {
    return (
      <div className="p-4 max-w-4xl mx-auto space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  const rank = TIER_RANK[tier];
  const proLocked = rank < 1;

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <EnteteManager
        titre="Démo paliers"
        sousTitre="Réglages tel que le voit un restaurateur, pour montrer en direct ce que chaque palier débloque."
      />

      <div className="border border-dashed border-[var(--harissa)] bg-[rgba(214,64,30,.08)] rounded-xl p-4 mb-6 flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wide text-[var(--harissa-dark)]">
            Mode démo — visible seulement ici
          </p>
          <p className="text-sm text-[var(--ink-soft)] mt-0.5">
            Choisissez un palier pour montrer au client ce qu&apos;il débloque. Rien ici ne change son vrai abonnement.
          </p>
        </div>
        <div className="flex bg-white border border-[var(--line)] rounded-lg p-0.5 gap-0.5">
          {(["essentiel", "pro", "business"] as Tier[]).map((t) => (
            <button
              key={t}
              onClick={() => setTier(t)}
              className={`px-4 py-2 rounded-md text-sm font-semibold ${
                tier === t ? "bg-[var(--harissa)] text-white" : "text-[var(--ink-soft)]"
              }`}
            >
              {t === "essentiel" ? "Essentiel" : t === "pro" ? "Pro" : "Business"}
            </button>
          ))}
        </div>
      </div>

      {currentMarket.ramadanModeAvailable && (
        <GatedCard locked={proLocked}>
          <label className="flex items-center gap-2 font-medium text-[#8a6420]">
            <input type="checkbox" disabled />
            Mode Ramadan
          </label>
          <p className="text-xs text-[#8a6420] mt-2">
            Une fois activé, les clients peuvent pré-commander pour l&apos;iftar depuis le menu.
          </p>
        </GatedCard>
      )}

      <Card tone="warning" padding="sm" className="mb-3">
        <label className="flex items-center gap-2 font-medium text-[#8a6420]">
          <input type="checkbox" disabled />
          Mode café simplifié
        </label>
        <p className="text-xs text-[#8a6420] mt-2">
          Pour un établissement qui ne sert que des boissons : le menu client s&apos;affiche en liste simple.
        </p>
      </Card>

      <Card padding="sm" className="mb-3">
        <label className="flex items-center gap-2 font-medium">
          <input type="checkbox" disabled />
          Retour sonore en cuisine
        </label>
        <p className="text-xs text-neutral-500 mt-2">
          Un bip se joue sur l&apos;écran cuisine à chaque nouvelle commande envoyée.
        </p>
      </Card>

      <Card padding="sm" className="mb-3">
        <div className="flex items-center justify-between">
          <span className="font-medium">Palier d&apos;abonnement</span>
          <span className="bg-[var(--line)] text-[var(--encre)] text-xs font-semibold px-2.5 py-1 rounded-full">
            {TIER_LABELS[tier]}
          </span>
        </div>
        <p className="text-xs text-neutral-500 mt-2">
          Le paiement carte, la fidélité, le plan de salle visuel, les photos
          {currentMarket.ramadanModeAvailable ? ", le mode Ramadan" : ""}, l&apos;import CSV et la page de preuve
          demandent Pro ou plus ; le rapport d&apos;équipe et les notifications push demandent Business.
        </p>
      </Card>

      {currentMarket.paymentProvider === "konnect" ? (
        <GatedCard locked={proLocked}>
          <span className="font-medium">Paiement carte de vos clients</span>
          <p className="text-xs text-[#8a6420] mt-2 mb-3">
            Sans compte Konnect connecté, le paiement carte reste en mode démonstration. Une fois connecté, vos
            clients règlent directement votre propre compte.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-[2fr_2fr_auto] gap-2">
            <input disabled placeholder="Clé API Konnect" className="border rounded px-2 py-1 bg-white" />
            <input disabled placeholder="ID du portefeuille" className="border rounded px-2 py-1 bg-white" />
            <span className="bg-[var(--harissa)] text-white text-sm font-semibold px-4 py-2 rounded text-center">
              Connecter
            </span>
          </div>
        </GatedCard>
      ) : (
        <Card padding="sm">
          <div className="flex items-center justify-between">
            <span className="font-medium">Paiement carte de vos clients</span>
            <span className="bg-[var(--line)] text-[var(--ink-soft)] text-[11px] font-bold uppercase tracking-wide px-2.5 py-1 rounded-full">
              Bientôt disponible
            </span>
          </div>
          <p className="text-xs text-neutral-500 mt-2">
            Le paiement carte en ligne arrive bientôt pour la France, quel que soit le palier. En attendant, vos
            clients règlent en espèces ou par terminal physique.
          </p>
        </Card>
      )}
    </div>
  );
}
