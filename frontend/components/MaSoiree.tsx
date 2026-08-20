import { MyShift } from "@/lib/api";
import { duree } from "@/lib/duree";
import { lalezar } from "@/lib/fonts";

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
export default function MaSoiree({ shift, tablesEnCharge }: { shift: MyShift | null; tablesEnCharge: number }) {
  if (!shift) return null;

  // « 1min42 » et pas « 1,7 min » : le serveur ne convertit pas des dixièmes de
  // minute en tête, il lit un temps.
  const delai = shift.avg_seconds_to_claim === null ? "—" : duree(shift.avg_seconds_to_claim);

  const tuiles = [
    { valeur: String(tablesEnCharge), libelle: "Tables en charge" },
    { valeur: String(shift.orders_taken), libelle: "Commandes servies" },
    { valeur: `${shift.total_amount_handled.toFixed(3)} DT`, libelle: "Encaissé ce soir" },
    { valeur: delai, libelle: "Attente moyenne" },
  ];

  return (
    <div className="flex flex-wrap gap-4 pb-1">
      {tuiles.map((tuile) => (
        <div
          key={tuile.libelle}
          className="flex-1 min-w-[150px] rounded-xl border border-[var(--line)] bg-[var(--semoule-raised)] px-[14px] py-3"
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--laiton)]">
            {tuile.libelle}
          </p>
          <p className={`${lalezar.className} text-[27px] leading-none tabular-nums text-[var(--encre)] mt-1.5`}>
            {tuile.valeur}
          </p>
        </div>
      ))}
    </div>
  );
}
