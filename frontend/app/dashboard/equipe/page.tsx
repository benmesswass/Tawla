"use client";

import { useCallback, useEffect, useState } from "react";
import EnteteManager from "@/components/EnteteManager";
import { useRouter } from "next/navigation";
import { api, StaffRole, SubscriptionTier, TeamReport } from "@/lib/api";
import { requiredTierFromError, toFrenchMessage } from "@/lib/errors";
import { formatAmount, formatMoney } from "@/lib/currency";
import { currentMarket } from "@/lib/market";
import { duree } from "@/lib/duree";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import { clearToken } from "@/lib/auth";
import Skeleton from "@/components/ui/Skeleton";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import UpgradeModal from "@/components/UpgradeModal";

/**
 * Rapport d'activité par membre de l'équipe — la base d'une prime de rendement.
 *
 * Volontairement une page à part, accessible au seul manager : ces chiffres
 * n'ont rien à faire sur l'écran serveur partagé. Présentés comme un outil de
 * prime ils passent ; découverts par hasard en salle, ils ressemblent à de la
 * surveillance et l'équipe sabote l'outil.
 */

const ROLE_LABELS: Record<StaffRole, string> = {
  waiter: "Serveur",
  kitchen: "Cuisine",
  manager: "Manager",
};

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

const formatDelay = duree;

function csvEscape(value: string | number): string {
  const s = String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function reportToCsv(report: TeamReport): string {
  const lines: string[] = [];
  const row = (...cells: (string | number)[]) => lines.push(cells.map(csvEscape).join(","));

  row("Rapport d'équipe Tawla", `${report.start} au ${report.end}`);
  lines.push("");
  row(
    "Nom", "Rôle", "Commandes prises", "Délai moyen de prise en charge (s)",
    `Montant traité (${currentMarket.currency.symbol})`
  );
  for (const member of report.staff) {
    row(
      member.staff_name,
      ROLE_LABELS[member.role],
      member.orders_taken,
      member.avg_seconds_to_claim === null ? "" : Math.round(member.avg_seconds_to_claim),
      formatAmount(member.total_amount_handled)
    );
  }
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

export default function TeamReportPage() {
  const router = useRouter();
  const { staff, loading: staffLoading } = useCurrentStaff(["manager"]);
  const [start, setStart] = useState(isoDaysAgo(6));
  const [end, setEnd] = useState(todayIso());
  const [report, setReport] = useState<TeamReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [upgradeTier, setUpgradeTier] = useState<SubscriptionTier | null>(null);

  const restaurantId = staff?.restaurant_id ?? null;

  const load = useCallback(async () => {
    if (!restaurantId) return;
    setError(null);
    try {
      setReport(await api.getTeamReport(restaurantId, start, end));
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
        titre="Rapport d'équipe"
        sousTitre="Activité de chaque membre de l'équipe sur la période — de quoi asseoir une prime de rendement sur des chiffres plutôt que sur une impression. Ce rapport ne s'affiche nulle part ailleurs que sur cette page."
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
          onClick={() =>
            report && downloadCsv(`tawla-equipe-${report.start}-${report.end}.csv`, reportToCsv(report))
          }
          disabled={!report || report.staff.length === 0}
        >
          Exporter en CSV
        </Button>
      </div>

      {error && (
        <Card tone="danger" padding="sm" className="mb-4 text-sm text-[var(--harissa)]">
          {error}
        </Card>
      )}

      {!report ? (
        <Skeleton className="h-48 w-full" />
      ) : report.staff.length === 0 ? (
        <EmptyState message="Aucune commande prise en charge sur cette période." />
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--ink-soft)] border-b border-[var(--line)]">
                  <th className="py-2 pr-3 font-medium">Membre</th>
                  <th className="py-2 pr-3 font-medium text-right">Commandes</th>
                  <th className="py-2 pr-3 font-medium text-right">Prise en charge</th>
                  <th className="py-2 font-medium text-right">Montant traité</th>
                </tr>
              </thead>
              <tbody>
                {report.staff.map((member) => (
                  <tr key={member.staff_id} className="border-b border-[var(--line)]">
                    <td className="py-2 pr-3">
                      {member.staff_name}
                      <span className="text-[var(--ink-soft)]"> · {ROLE_LABELS[member.role]}</span>
                    </td>
                    <td className="py-2 pr-3 text-right tabular-nums">{member.orders_taken}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">
                      {formatDelay(member.avg_seconds_to_claim)}
                    </td>
                    <td className="py-2 text-right tabular-nums">
                      {formatMoney(member.total_amount_handled)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Card padding="sm" className="mt-4 text-sm text-[var(--ink-soft)]">
            <p>
              « Prise en charge » est le délai moyen entre la commande du client et le moment où le serveur
              l&apos;a prise. C&apos;est la part du délai qui dépend réellement de lui — le temps de cuisson
              n&apos;en fait pas partie.
            </p>
            <p className="mt-2">
              Les commandes annulées ne sont pas comptées. Un membre de l&apos;équipe dont le compte a été
              désactivé reste listé s&apos;il a travaillé sur la période.
            </p>
          </Card>
        </>
      )}
    </div>
  );
}
