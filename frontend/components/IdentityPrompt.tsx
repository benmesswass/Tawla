"use client";

import { useState } from "react";
import { fr, type Dictionary } from "@/lib/i18n/fr";
import { lalezar } from "@/lib/fonts";
import Button from "@/components/ui/Button";

/**
 * Modale bloquante affichée dès le scan (ROADMAP.md §Override — identité de
 * table) : identifie ce téléphone à un prénom pour toute la commande, jusqu'au
 * paiement. Remplace l'ancien `PartyPrompt` ("vous êtes combien à table ?"),
 * posé une fois pour toute la tablée — ici chaque téléphone répond pour
 * lui-même, jamais pour les autres. Un prénom laissé vide (ou "Passer") reste
 * un choix valide : le serveur assigne alors "PersoN" à la place.
 */
export default function IdentityPrompt({
  restaurantName,
  tableLabel,
  onSubmit,
  t = fr,
}: {
  restaurantName?: string;
  tableLabel?: string;
  onSubmit: (name: string) => void;
  t?: Dictionary;
}) {
  const [name, setName] = useState("");
  const eyebrow = [restaurantName, tableLabel].filter(Boolean).join(" · ");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl text-center">
        {eyebrow && (
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[var(--ink-soft)]">{eyebrow}</p>
        )}
        <h1 className={`${lalezar.className} mt-2 text-2xl text-[var(--encre)]`}>{t.identityPromptTitle}</h1>
        <p className="mt-2 text-sm text-[var(--ink-soft)]">{t.identityPromptSubtitle}</p>

        <div className="mt-5 text-left">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t.identityInputPlaceholder}
            maxLength={30}
            autoFocus
            className="w-full border-[1.5px] border-[var(--line)] rounded-[14px] px-4 py-3 text-base text-[var(--encre)]"
          />
          <p className="mt-1.5 text-[11.5px] text-[var(--ink-faint)]">{t.identityInputCaption}</p>
        </div>

        <Button onClick={() => onSubmit(name)} className="mt-4 w-full">
          {t.identityContinue}
        </Button>
        <button
          type="button"
          onClick={() => onSubmit("")}
          className="mt-3 text-sm text-[var(--ink-soft)] underline"
        >
          {t.identityPromptSkip}
        </button>
      </div>
    </div>
  );
}
