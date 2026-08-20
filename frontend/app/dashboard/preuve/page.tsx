"use client";

import { useCallback, useEffect, useState } from "react";
import EnteteManager from "@/components/EnteteManager";
import { useRouter } from "next/navigation";
import { api, PeriodProof, ProofStats, SubscriptionTier } from "@/lib/api";
import { requiredTierFromError, toFrenchMessage } from "@/lib/errors";
import { duree } from "@/lib/duree";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import { clearToken } from "@/lib/auth";
import Skeleton from "@/components/ui/Skeleton";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import UpgradeModal from "@/components/UpgradeModal";

/**
 * La page que Wassim montre à un patron à la fin d'un pilote, et au jury.
 *
 * Trois chiffres, pas quatre. Chacun comparé à la période précédente de même
 * longueur : sans « avant », un chiffre ne prouve rien. Volontairement dépouillée
 * — c'est un document de décision, pas un tableau de bord.
 */

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

const formatDuration = duree;

function formatAmount(amount: number | null): string {
  return amount === null ? "—" : `${amount.toFixed(3)} DT`;
}

function formatDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

type Direction = "lower-is-better" | "higher-is-better";

/**
 * Écart relatif entre deux périodes. `null` quand il n'y a rien à comparer :
 * afficher « +100 % » parce que la semaine précédente était vide serait un
 * chiffre faux dans une conversation commerciale.
 */
function relativeChange(current: number | null, previous: number | null): number | null {
  if (current === null || previous === null || previous === 0) return null;
  return ((current - previous) / previous) * 100;
}

function DeltaBadge({
  current,
  previous,
  direction,
}: {
  current: number | null;
  previous: number | null;
  direction: Direction;
}) {
  const change = relativeChange(current, previous);
  if (change === null) {
    return <span className="text-xs text-[var(--ink-soft)]">pas de comparaison possible</span>;
  }
  if (Math.abs(change) < 1) {
    return <span className="text-xs text-[var(--ink-soft)]">stable</span>;
  }
  const improved = direction === "lower-is-better" ? change < 0 : change > 0;
  const sign = change > 0 ? "+" : "";
  return (
    <span
      className={`text-xs font-medium px-2 py-1 rounded-full ${
        improved ? "bg-[rgba(31,107,79,.12)] text-[var(--menthe)]" : "bg-[rgba(184,134,46,.12)] text-[#8a6420]"
      }`}
    >
      {sign}
      {change.toFixed(0)} % vs période précédente
    </span>
  );
}

function MetricCard({
  label,
  value,
  detail,
  current,
  previous,
  direction,
  previousLabel,
}: {
  label: string;
  value: string;
  detail?: string;
  current: number | null;
  previous: number | null;
  direction: Direction;
  previousLabel: string;
}) {
  return (
    <Card className="flex flex-col gap-2">
      <span className="text-sm text-[var(--ink-soft)]">{label}</span>
      <span className="text-3xl font-semibold tabular-nums">{value}</span>
      {detail && <span className="text-xs text-[var(--ink-soft)]">{detail}</span>}
      <div className="flex flex-col gap-1 mt-1">
        <DeltaBadge current={current} previous={previous} direction={direction} />
        <span className="text-xs text-[var(--ink-soft)]">Avant : {previousLabel}</span>
      </div>
    </Card>
  );
}

function csvEscape(value: string | number): string {
  const s = String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

// Reformate ce qui est déjà chargé — aucun endpoint supplémentaire, même
// mécanique que l'export de /dashboard/stats.
function proofToCsv(proof: ProofStats): string {
  const lines: string[] = [];
  const row = (...cells: (string | number)[]) => lines.push(cells.map(csvEscape).join(","));
  const cell = (value: number | null) => (value === null ? "" : value);

  row("Preuve Tawla — trois métriques");
  lines.push("");
  row("Indicateur", "Période mesurée", "Période précédente");
  row(
    "Période",
    `${proof.current.start} au ${proof.current.end}`,
    `${proof.previous.start} au ${proof.previous.end}`
  );
  row("Commandes", proof.current.orders_count, proof.previous.orders_count);
  row("Commandes perdues", proof.current.lost_orders_count, proof.previous.lost_orders_count);
  row("dont annulées", proof.current.cancelled_count, proof.previous.cancelled_count);
  row("dont oubliées", proof.current.abandoned_count, proof.previous.abandoned_count);
  row(
    "Délai commande vers cuisine (secondes)",
    cell(proof.current.avg_order_to_kitchen_seconds),
    cell(proof.previous.avg_order_to_kitchen_seconds)
  );
  row("Panier moyen (DT)", cell(proof.current.avg_basket_amount), cell(proof.previous.avg_basket_amount));

  return lines.join("\n");
}

function downloadCsv(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function lostRate(period: PeriodProof): string {
  if (period.orders_count === 0) return "—";
  return `${((period.lost_orders_count / period.orders_count) * 100).toFixed(0)} % des commandes`;
}

export default function ProofPage() {
  const router = useRouter();
  const { staff, loading: staffLoading } = useCurrentStaff(["manager"]);
  const [start, setStart] = useState(isoDaysAgo(6));
  const [end, setEnd] = useState(todayIso());
  const [proof, setProof] = useState<ProofStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [upgradeTier, setUpgradeTier] = useState<SubscriptionTier | null>(null);

  const restaurantId = staff?.restaurant_id ?? null;

  const load = useCallback(async () => {
    if (!restaurantId) return;
    setError(null);
    try {
      setProof(await api.getProofStats(restaurantId, start, end));
    } catch (e) {
      const tier = requiredTierFromError(e);
      if (tier) {
        setUpgradeTier(tier);
        return;
      }
      setError(toFrenchMessage(e));
    }
  }, [restaurantId, start, end]);

  useEffect(() => {
    if (restaurantId) load();
  }, [restaurantId, load]);


  if (staffLoading || !staff) {
    return (
      <div className="p-4 max-w-4xl mx-auto space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  return (
    <div className="p-4 max-w-4xl mx-auto">
      {upgradeTier && restaurantId && (
        <UpgradeModal
          restaurantId={restaurantId}
          requiredTier={upgradeTier}
          onClose={() => setUpgradeTier(null)}
          onUpgraded={() => load()}
        />
      )}
      <EnteteManager
        titre="Preuve du pilote"
        sousTitre="Les trois seuls chiffres qui comptent pour décider si Tawla vous fait gagner de l'argent, comparés à la période précédente de même longueur."
      />

      <div className="flex items-end gap-2 mb-6 flex-wrap">
        <div className="flex flex-col">
          <label htmlFor="start" className="text-xs text-[var(--ink-soft)]">
            Du
          </label>
          <input
            id="start"
            type="date"
            value={start}
            max={end}
            onChange={(e) => setStart(e.target.value)}
            className="border border-[var(--line)] rounded-lg px-2 py-1 text-sm"
          />
        </div>
        <div className="flex flex-col">
          <label htmlFor="end" className="text-xs text-[var(--ink-soft)]">
            Au
          </label>
          <input
            id="end"
            type="date"
            value={end}
            min={start}
            max={todayIso()}
            onChange={(e) => setEnd(e.target.value)}
            className="border border-[var(--line)] rounded-lg px-2 py-1 text-sm"
          />
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => proof && downloadCsv(`tawla-preuve-${proof.current.start}-${proof.current.end}.csv`, proofToCsv(proof))}
          disabled={!proof}
        >
          Exporter en CSV
        </Button>
      </div>

      {error && (
        <Card tone="danger" padding="sm" className="mb-4 text-sm text-[var(--harissa)]">
          {error}
        </Card>
      )}

      {!proof ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <MetricCard
              label="Commandes perdues"
              value={String(proof.current.lost_orders_count)}
              detail={`${lostRate(proof.current)} · ${proof.current.cancelled_count} annulée(s), ${proof.current.abandoned_count} oubliée(s)`}
              current={proof.current.lost_orders_count}
              previous={proof.previous.lost_orders_count}
              direction="lower-is-better"
              previousLabel={String(proof.previous.lost_orders_count)}
            />
            <MetricCard
              label="Délai commande → cuisine"
              value={formatDuration(proof.current.avg_order_to_kitchen_seconds)}
              detail="Du panier validé à l'arrivée sur l'écran cuisine"
              current={proof.current.avg_order_to_kitchen_seconds}
              previous={proof.previous.avg_order_to_kitchen_seconds}
              direction="lower-is-better"
              previousLabel={formatDuration(proof.previous.avg_order_to_kitchen_seconds)}
            />
            <MetricCard
              label="Panier moyen"
              value={formatAmount(proof.current.avg_basket_amount)}
              detail="Commandes annulées exclues"
              current={proof.current.avg_basket_amount}
              previous={proof.previous.avg_basket_amount}
              direction="higher-is-better"
              previousLabel={formatAmount(proof.previous.avg_basket_amount)}
            />
          </div>

          {proof.current.orders_with_suggestion_count > 0 && (
            <Card tone="success" padding="sm" className="mt-4">
              <p className="text-sm font-medium text-[var(--menthe)]">Effet des suggestions « avec ce plat »</p>
              {proof.current.avg_basket_with_suggestion !== null &&
              proof.current.avg_basket_without_suggestion !== null ? (
                <>
                  <p className="text-sm text-[var(--menthe)] mt-1">
                    Panier moyen <strong>{formatAmount(proof.current.avg_basket_with_suggestion)}</strong>{" "}
                    quand le client accepte une suggestion, contre{" "}
                    <strong>{formatAmount(proof.current.avg_basket_without_suggestion)}</strong> sinon —{" "}
                    <strong>
                      {(() => {
                        const change = relativeChange(
                          proof.current.avg_basket_with_suggestion,
                          proof.current.avg_basket_without_suggestion
                        );
                        return change === null ? "—" : `${change > 0 ? "+" : ""}${change.toFixed(0)} %`;
                      })()}
                    </strong>
                    .
                  </p>
                  <p className="text-xs text-[var(--menthe)] mt-2">
                    Sur {proof.current.orders_with_suggestion_count} commande(s) où une suggestion a été
                    acceptée. C&apos;est le chiffre à citer en rendez-vous : il compare des commandes du même
                    établissement sur la même période, donc il n&apos;attribue pas à Tawla une hausse due à
                    des tables plus nombreuses.
                  </p>
                </>
              ) : (
                // Toutes les commandes de la période comportent une suggestion :
                // il n'y a donc rien à quoi les comparer. Le dire vaut mieux que
                // masquer le bloc — sinon le manager croit que rien n'est mesuré.
                <p className="text-sm text-[var(--menthe)] mt-1">
                  {proof.current.orders_with_suggestion_count} commande(s) avec une suggestion acceptée, pour
                  un panier moyen de{" "}
                  <strong>{formatAmount(proof.current.avg_basket_with_suggestion)}</strong>. La comparaison
                  s&apos;affichera dès qu&apos;une commande sera passée sans suggestion sur la même période.
                </p>
              )}
            </Card>
          )}

          <Card padding="sm" className="mt-4 text-sm text-[var(--ink-soft)]">
            <p>
              <strong className="text-[var(--encre)]">{proof.current.orders_count} commande(s)</strong> du{" "}
              {formatDate(proof.current.start)} au {formatDate(proof.current.end)}, comparées aux{" "}
              {proof.previous.orders_count} commande(s) du {formatDate(proof.previous.start)} au{" "}
              {formatDate(proof.previous.end)}.
            </p>
            <p className="mt-2">
              Une commande est comptée perdue dans deux cas : elle a été annulée, ou bien plus de 10 minutes se
              sont écoulées <strong className="text-[var(--encre)]">entre le moment où le client a validé son
              panier et celui où un serveur l&apos;a prise en charge</strong> — autrement dit, personne n&apos;a
              réagi. Le temps de cuisine et le temps de service n&apos;entrent pas dans ce calcul. Ces 10 minutes
              sont une proposition à ajuster avec vous après un premier service.
            </p>
          </Card>
        </>
      )}
    </div>
  );
}
