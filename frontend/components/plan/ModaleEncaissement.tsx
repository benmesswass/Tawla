"use client";

import { useState } from "react";
import { PaymentMethod } from "@/lib/api";
import { formatAmount, formatMoney, parseAmountInput } from "@/lib/currency";
import { LIBELLE_MOYEN } from "@/lib/moyenDePaiement";
import Button from "@/components/ui/Button";

/**
 * Le serveur déclare avoir encaissé, sans que la table ait rien demandé
 * depuis son téléphone.
 *
 * C'est le geste qui manquait : les trois moyens de paiement partaient tous
 * d'une demande du client, et une table qui règle en espèces au comptoir — le
 * cas ordinaire en salle — n'avait aucun chemin pour être enregistrée. Sa
 * commande restait « non payée » pour toujours, la libération réclamait une
 * note, et la recette du patron ne voyait rien passer.
 *
 * Une modale plutôt que deux boutons dans le panneau d'action : le montant est
 * modifiable (une table peut régler une partie en espèces et le reste
 * autrement) et le moyen doit être choisi. Deux boutons « Encaisser espèces »
 * et « Encaisser carte » auraient tenu dans le panneau, mais auraient rendu
 * tout encaissement partiel impossible, et cassé la règle du seul harissa
 * cliquable par zone de décision.
 */

const MOYENS: Extract<PaymentMethod, "cash" | "card_terminal">[] = ["cash", "card_terminal"];

// Un dinar se divise en 1000 millimes : la tolérance doit rester en dessous du
// millime, sinon « il reste 1 millime » deviendrait « rien à encaisser ». Même
// seuil que le backend (`orders/reglement.py::TOLERANCE`).
const TOLERANCE = 0.005;

export default function ModaleEncaissement({
  tableLabel,
  restant,
  onConfirm,
  onClose,
}: {
  tableLabel: string;
  /** Ce qu'il reste dû sur la table, toutes ses commandes confondues. */
  restant: number;
  onConfirm: (method: "cash" | "card_terminal", amount: number, tipAmount: number) => Promise<void>;
  onClose: () => void;
}) {
  // Prérempli au restant : le cas de très loin le plus fréquent est « la table
  // paie tout », et le serveur ne doit alors rien taper.
  const [montant, setMontant] = useState(() => formatAmount(restant));
  const [pourboire, setPourboire] = useState("");
  const [moyen, setMoyen] = useState<"cash" | "card_terminal">("cash");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const valeur = parseAmountInput(montant);
  const trop = valeur > restant + TOLERANCE;
  const invalide = valeur <= 0 || trop;

  async function confirmer() {
    if (invalide) {
      setError(trop ? `Pas plus que ${formatMoney(restant)}.` : "Saisissez un montant.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onConfirm(moyen, valeur, parseAmountInput(pourboire));
    } catch (e) {
      // L'appelant traduit déjà l'erreur backend (toFrenchMessage) et la
      // relance ici : ce que le serveur a tapé reste à l'écran.
      setError(e instanceof Error ? e.message : "L'encaissement a échoué. Réessayez.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-sm rounded-carte bg-white p-5 shadow-couche">
        <p className="text-surtitre font-medium uppercase text-[var(--laiton-text)]">Encaissement</p>
        <h2 className="mt-1 text-titre font-semibold text-[var(--encre)]">
          {tableLabel} — {formatMoney(restant)} à encaisser
        </h2>
        <p className="mt-2 text-etiquette text-[var(--ink-soft)]">
          À confirmer une fois l&apos;argent pris. La table passe réglée, sa facture est émise, et la
          recette du jour en tient compte.
        </p>

        <fieldset className="mt-4">
          <legend className="text-etiquette font-medium text-[var(--ink-soft)]">Moyen</legend>
          <div className="mt-1 flex gap-2">
            {MOYENS.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setMoyen(option)}
                aria-pressed={moyen === option}
                className={`flex-1 rounded-controle border px-3 py-2 text-etiquette transition-colors duration-micro ease-deplacement focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--harissa)] ${
                  moyen === option
                    ? "border-[var(--laiton)] bg-[rgba(184,134,46,.14)] font-medium text-[var(--espresso)]"
                    : "border-[var(--line)] text-[var(--ink-soft)] hover:bg-[var(--semoule)]"
                }`}
              >
                {LIBELLE_MOYEN[option]}
              </button>
            ))}
          </div>
        </fieldset>

        <div className="mt-4 flex gap-3">
          <label className="flex-1 text-etiquette font-medium text-[var(--ink-soft)]">
            Montant
            <input
              value={montant}
              onChange={(e) => {
                setMontant(e.target.value);
                setError(null);
              }}
              inputMode="decimal"
              className="mt-1 w-full rounded-champ border border-[var(--line)] p-2 text-corps text-[var(--encre)]"
              autoFocus
            />
          </label>
          <label className="flex-1 text-etiquette font-medium text-[var(--ink-soft)]">
            Pourboire
            <input
              value={pourboire}
              onChange={(e) => setPourboire(e.target.value)}
              inputMode="decimal"
              placeholder="0"
              className="mt-1 w-full rounded-champ border border-[var(--line)] p-2 text-corps text-[var(--encre)]"
            />
          </label>
        </div>

        {error && <p className="mt-3 text-etiquette text-[var(--harissa-text)]">{error}</p>}

        <div className="mt-5 flex flex-col gap-2">
          <Button variant="laiton" onClick={confirmer} loading={submitting}>
            {submitting ? "Encaissement…" : "J'ai encaissé"}
          </Button>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Retour
          </Button>
        </div>
      </div>
    </div>
  );
}
