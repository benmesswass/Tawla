"use client";

import { useState } from "react";
import { OrderInProgressStatus } from "@/lib/api";
import Button from "@/components/ui/Button";

/**
 * Confirmation avant de libérer une table (2026-09-09, demande de Wassim).
 *
 * Deux modales, pas une seule avec un état conditionnel discret : le risque
 * n'est pas le même. Sans commande en cours (ou déjà servie et payée), un
 * simple aller-retour suffit. Une commande encore ouverte — n'importe quelle
 * étape, y compris servie mais pas encore encaissée — exige une explication
 * écrite avant de pouvoir confirmer : c'est elle que le manager retrouvera
 * dans « Libérations forcées ».
 */

const ETAPE_LABELS: Record<OrderInProgressStatus, string> = {
  pending_confirmation: "en attente de confirmation",
  confirmed: "confirmée, pas encore envoyée en cuisine",
  sent_to_kitchen: "envoyée en cuisine",
  in_preparation: "en préparation",
  ready: "prête à servir",
  served_unpaid: "servie, addition pas encore encaissée",
};

const NOTE_MAX_LENGTH = 500;

export default function ModaleLibererTable({
  tableLabel,
  commandeEnCours,
  onConfirm,
  onClose,
}: {
  tableLabel: string;
  /** `null` = rien en cours (ou déjà terminée et payée) : modale "safe". */
  commandeEnCours: OrderInProgressStatus | null;
  onConfirm: (note?: string) => Promise<void>;
  onClose: () => void;
}) {
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const danger = commandeEnCours !== null;
  const noteInvalide = danger && note.trim().length === 0;

  async function confirmer() {
    if (noteInvalide) return;
    setSubmitting(true);
    setError(null);
    try {
      await onConfirm(danger ? note.trim() : undefined);
    } catch (e) {
      // L'appelant (staff/page.tsx) traduit déjà l'erreur backend
      // (toFrenchMessage) et la relance ici — jamais perdue, et la note déjà
      // tapée reste dans le formulaire au lieu d'être effacée.
      setError(e instanceof Error ? e.message : "La libération a échoué. Réessayez.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-sm rounded-xl bg-white p-5 shadow-lg">
        {danger ? (
          <>
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--harissa)]">
              Commande en cours
            </p>
            <h2 className="mt-1 text-lg font-semibold text-[var(--encre)]">
              {tableLabel} a une commande {ETAPE_LABELS[commandeEnCours]}
            </h2>
            <p className="mt-2 text-sm text-[var(--ink-soft)]">
              Libérer cette table maintenant sera enregistré pour le manager, avec votre nom, l&apos;heure et
              l&apos;étape de la commande. Expliquez pourquoi.
            </p>
            <label htmlFor="note-liberation" className="mt-3 block text-xs font-medium text-[var(--ink-soft)]">
              Note (obligatoire)
            </label>
            <textarea
              id="note-liberation"
              value={note}
              onChange={(e) => setNote(e.target.value.slice(0, NOTE_MAX_LENGTH))}
              rows={3}
              placeholder="Ex : client parti sans prévenir, plat pas encore en cuisine."
              className="mt-1 w-full rounded-lg border border-[var(--line)] p-2 text-sm"
              autoFocus
            />
            <p className="mt-1 text-xs text-[var(--ink-faint)] text-end">{note.length}/{NOTE_MAX_LENGTH}</p>
          </>
        ) : (
          <>
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--menthe)]">Table libre</p>
            <h2 className="mt-1 text-lg font-semibold text-[var(--encre)]">
              Libérer {tableLabel} ?
            </h2>
            <p className="mt-2 text-sm text-[var(--ink-soft)]">
              Aucune commande en cours — ou déjà servie et payée. Le panier et les convives déclarés seront
              remis à zéro pour la prochaine tablée.
            </p>
          </>
        )}

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <div className="mt-5 flex flex-col gap-2">
          <Button onClick={confirmer} disabled={submitting || noteInvalide}>
            {submitting ? "Libération…" : "Confirmer la libération"}
          </Button>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Retour
          </Button>
        </div>
      </div>
    </div>
  );
}
