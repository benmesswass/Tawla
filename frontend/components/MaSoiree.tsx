import { MyShift } from "@/lib/api";

/**
 * Les chiffres du serveur, sur l'écran du serveur (Phase 17.3).
 *
 * Raison d'être : c'est lui qui fournit le téléphone, la batterie et le
 * forfait, et c'est son temps de prise en charge qui est mesuré. Sans rien
 * pour lui, il a raison de contourner l'outil — et un outil contourné en salle
 * fait résilier le patron sans qu'il dise jamais pourquoi.
 *
 * **Aucune comparaison avec les collègues, aucun classement.** Le rapport
 * d'équipe reste un document de direction (Phase 14.2). L'API elle-même
 * n'envoie que ses chiffres à lui : ce qui n'est pas transmis ne peut pas
 * fuiter dans une évolution future de cet écran.
 */
export default function MaSoiree({ shift }: { shift: MyShift | null }) {
  if (!shift) return null;

  const minutes =
    shift.avg_seconds_to_claim === null ? null : Math.round(shift.avg_seconds_to_claim / 6) / 10;

  return (
    <div className="mb-4 rounded-xl border border-[var(--line)] bg-white px-4 py-3">
      <p className="text-xs text-[var(--ink-soft)] mb-2">Ma soirée</p>
      <div className="flex flex-wrap gap-x-8 gap-y-2">
        <div>
          <p className="text-2xl font-semibold tabular-nums leading-none">{shift.orders_taken}</p>
          <p className="text-xs text-[var(--ink-soft)] mt-1">
            commande{shift.orders_taken > 1 ? "s" : ""} prise{shift.orders_taken > 1 ? "s" : ""}
          </p>
        </div>
        <div>
          <p className="text-2xl font-semibold tabular-nums leading-none">
            {shift.total_amount_handled.toFixed(2)} DT
          </p>
          <p className="text-xs text-[var(--ink-soft)] mt-1">servis</p>
        </div>
        {minutes !== null && (
          <div>
            <p className="text-2xl font-semibold tabular-nums leading-none">{minutes} min</p>
            <p className="text-xs text-[var(--ink-soft)] mt-1">pour prendre une table</p>
          </div>
        )}
      </div>
    </div>
  );
}
