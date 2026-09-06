"use client";

import { useState } from "react";
import { fr, type Dictionary } from "@/lib/i18n/fr";

/**
 * Demandé une fois par table (ROADMAP.md §Override — panier synchronisé
 * multi-appareils, extension) : combien de convives, et leurs prénoms
 * facultatifs — purement déclaratif, affiché ensuite dans SplitBill à la
 * place de "Personne N". Ne bloque jamais la commande : "Passer" à chaque
 * étape laisse la table sans déclaration, comme avant ce chantier.
 */
export default function PartyPrompt({
  suggestedSize,
  onSubmit,
  onSkip,
  t = fr,
}: {
  suggestedSize: number;
  onSubmit: (size: number, names: (string | null)[]) => void;
  onSkip: () => void;
  t?: Dictionary;
}) {
  const [step, setStep] = useState<"size" | "names">("size");
  const [size, setSize] = useState(() => Math.max(1, Math.min(20, suggestedSize || 2)));
  const [names, setNames] = useState<string[]>([]);

  function goToNames() {
    if (size <= 1) {
      onSubmit(1, [null]);
    } else {
      setStep("names");
    }
  }

  function submitNames() {
    const padded = Array.from({ length: size }, (_, i) => names[i]?.trim() || null);
    onSubmit(size, padded);
  }

  if (step === "names") {
    return (
      <div className="border border-[var(--line)] bg-[var(--semoule-raised)] rounded-[12px] p-3 space-y-2">
        <p className="text-sm font-semibold text-[var(--encre)]">{t.partyNamesHint}</p>
        <div className="space-y-2">
          {Array.from({ length: size }, (_, i) => (
            <input
              key={i}
              value={names[i] ?? ""}
              onChange={(e) =>
                setNames((prev) => {
                  const next = [...prev];
                  next[i] = e.target.value;
                  return next;
                })
              }
              placeholder={t.personLabel(i + 1)}
              maxLength={30}
              className="w-full bg-white border border-[var(--line)] rounded-[10px] px-3 py-1.5 text-sm text-[var(--encre)]"
            />
          ))}
        </div>
        <div className="flex items-center justify-between pt-1">
          <button type="button" onClick={onSkip} className="text-sm underline text-[var(--ink-soft)]">
            {t.partyPromptSkip}
          </button>
          <button
            type="button"
            onClick={submitNames}
            className="rounded-[10px] px-4 py-1.5 text-sm font-semibold bg-[var(--harissa)] text-[var(--semoule)]"
          >
            {t.partyContinue}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-[var(--line)] bg-[var(--semoule-raised)] rounded-[12px] p-3 space-y-2">
      <div className="flex items-center gap-2 text-sm text-[var(--encre)]">
        <label htmlFor="party-size" className="font-semibold">
          {t.partyPromptTitle}
        </label>
        <input
          id="party-size"
          type="number"
          min={1}
          max={20}
          value={size}
          onChange={(e) => setSize(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
          className="w-16 bg-white border border-[var(--line)] rounded-[10px] px-2 py-1"
        />
      </div>
      <div className="flex items-center justify-between pt-1">
        <button type="button" onClick={onSkip} className="text-sm underline text-[var(--ink-soft)]">
          {t.partyPromptSkip}
        </button>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onSubmit(1, [null])}
            className="rounded-[10px] px-3 py-1.5 text-sm border border-[var(--line)] bg-white text-[var(--encre)]"
          >
            {t.partyPromptJustMe}
          </button>
          <button
            type="button"
            onClick={goToNames}
            className="rounded-[10px] px-4 py-1.5 text-sm font-semibold bg-[var(--harissa)] text-[var(--semoule)]"
          >
            {t.partyContinue}
          </button>
        </div>
      </div>
    </div>
  );
}
