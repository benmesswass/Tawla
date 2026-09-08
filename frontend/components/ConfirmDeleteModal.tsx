"use client";

import { lalezar } from "@/lib/fonts";
import Button from "@/components/ui/Button";

/**
 * Confirmation avant une suppression destructive — remplace le
 * `window.confirm()` natif du navigateur, même raison que
 * ConfirmDowngradeModal (retour utilisateur, 2026-09-02 puis 2026-09-07 :
 * repéré cette fois sur la suppression d'une table). Générique (titre +
 * message) plutôt qu'un modal dédié par type d'objet supprimé : contrairement
 * à ConfirmDowngradeModal, qui a besoin de connaître la mécanique des
 * paliers, une confirmation de suppression n'a besoin de rien de plus qu'un
 * texte.
 */
export default function ConfirmDeleteModal({
  title,
  message,
  confirmLabel = "Supprimer",
  submitting = false,
  onConfirm,
  onCancel,
}: {
  title: string;
  message?: string;
  confirmLabel?: string;
  submitting?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--harissa)]">Suppression</p>
        <h2 className={`${lalezar.className} mt-1 text-2xl text-[var(--encre)]`}>{title}</h2>
        {message && <p className="mt-2 text-sm text-[var(--ink-soft)]">{message}</p>}

        <div className="mt-5 flex flex-col gap-2">
          <Button variant="danger" onClick={onConfirm} disabled={submitting}>
            {submitting ? "Suppression..." : confirmLabel}
          </Button>
          <Button variant="secondary" onClick={onCancel} disabled={submitting}>
            Annuler
          </Button>
        </div>
      </div>
    </div>
  );
}
