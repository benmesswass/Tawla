"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { lalezar } from "@/lib/fonts";
import { api, staffWsUrl, LoyaltyMember, MyShift, Order, PlanTable } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { useReconnectingSocket } from "@/lib/useReconnectingSocket";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import { clearToken } from "@/lib/auth";
import { useRouter } from "next/navigation";
import ConnectionBadge from "@/components/ConnectionBadge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";
import MaSoiree from "@/components/MaSoiree";
import PlanDeSalle from "@/components/plan/PlanDeSalle";
import ActionTable, { ActionsTable } from "@/components/plan/ActionTable";
import { ETAT_LIBRE, ordreDArrivee } from "@/components/plan/types";
import { construireEtats } from "@/components/plan/etats";
import { BellIcon, MoonIcon, GiftIcon, CakeIcon } from "@/components/icons";
import { duree, elapsedSeconds, useHorloge } from "@/lib/duree";

// Même seuil que `ABANDONED_PENDING_AFTER` côté serveur : au-delà, la commande
// est comptée perdue dans les chiffres du patron. L'écran doit donc alerter
// avant, pas après — sinon le serveur découvre la perte dans le tableau de bord.
const ATTENTE_ALERTE_MINUTES = 10;
import Skeleton from "@/components/ui/Skeleton";
import TawlaMark from "@/components/brand/TawlaMark";

type PendingOrder = {
  order_id: number;
  table_id: number;
  table_label: string;
  taken_by_staff_id: number | null;
  taken_by_staff_name: string | null;
  created_at: string | null;
  scheduled_for: string | null;
};
type ReadyOrder = { order_id: number; table_id: number; table_label: string; ready_at: string | null };
type CashRequest = {
  order_id: number;
  table_id: number;
  table_label: string;
  amount: number;
  taken_by_staff_id: number | null;
  loyalty_phone: string | null;
};
// Carte physique (terminal apporté par un serveur) — même mécanique, même
// forme que la demande en espèces (2026-08-19).
type CardTerminalRequest = CashRequest;
type WaiterCall = { call_id: number; table_id: number; table_label: string; created_at: string | null };
/** Commandes parties en cuisine : rien à faire pour le serveur, mais la table
 *  n'est pas libre pour autant — le plan doit la montrer occupée. */
type EnCuisine = { order_id: number; table_id: number };

function fromApi(o: Order): PendingOrder {
  return {
    order_id: o.id,
    table_id: o.table_id,
    table_label: o.table_label,
    taken_by_staff_id: o.taken_by_staff_id,
    taken_by_staff_name: o.taken_by_staff_name,
    created_at: o.created_at ?? null,
    scheduled_for: o.scheduled_for,
  };
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}


function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] as string));
}

// Chrome commun à toutes les files de la colonne de droite : liseré vertical à
// la couleur de la file, titre, compteur plein, précision optionnelle.
function EntetePanneau({ titre, couleur, count, precision }: { titre: string; couleur: string; count: number; precision?: string }) {
  return (
    <div className="px-[14px] py-[11px] border-b border-[var(--line)] flex items-center gap-2.5">
      <span className="w-[9px] h-[22px] rounded-[3px] shrink-0" style={{ backgroundColor: couleur }} />
      <span className="text-[13.5px] font-bold text-[var(--encre)]">{titre}</span>
      <span
        className="inline-flex items-center justify-center min-w-[22px] h-[22px] px-1.5 rounded-full text-[12px] font-bold text-[var(--semoule)]"
        style={{ backgroundColor: couleur }}
      >
        {count}
      </span>
      {precision && <span className="ms-auto text-xs text-[var(--ink-soft)]">{precision}</span>}
    </div>
  );
}

function FileVide({ message }: { message: string }) {
  return <p className="py-5 px-[14px] text-center text-[12.5px] text-[var(--ink-faint)]">{message}</p>;
}

export default function StaffPage() {
  const router = useRouter();
  const { staff, loading: staffLoading } = useCurrentStaff(["waiter", "manager"]);
  const maintenant = useHorloge();
  const [pending, setPending] = useState<PendingOrder[]>([]);
  const [readyToServe, setReadyToServe] = useState<ReadyOrder[]>([]);
  const [cashRequests, setCashRequests] = useState<CashRequest[]>([]);
  const [cardTerminalRequests, setCardTerminalRequests] = useState<CardTerminalRequest[]>([]);
  const [waiterCalls, setWaiterCalls] = useState<WaiterCall[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [myShift, setMyShift] = useState<MyShift | null>(null);
  const [plan, setPlan] = useState<PlanTable[]>([]);
  const [enCuisine, setEnCuisine] = useState<EnCuisine[]>([]);
  const [vuePlan, setVuePlan] = useState(true);
  const [tableOuverte, setTableOuverte] = useState<number | null>(null);
  const [loyaltyByPhone, setLoyaltyByPhone] = useState<Record<string, LoyaltyMember>>({});
  const [lookupPhone, setLookupPhone] = useState("");
  const [lookupResult, setLookupResult] = useState<LoyaltyMember | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(tick);
  }, []);

  const restaurantId = staff?.restaurant_id ?? null;

  async function fetchLoyaltyForPhone(rId: number, phone: string) {
    try {
      const member = await api.getLoyaltyMemberForStaff(rId, phone);
      setLoyaltyByPhone((prev) => ({ ...prev, [phone]: member }));
    } catch {
      // Pas de fiche fidélité pour ce numéro (jamais renseigné côté client) —
      // rien à afficher, ce n'est pas une erreur.
    }
  }

  const loadActiveOrders = useCallback(async () => {
    if (!restaurantId) return;
    try {
      const orders = await api.listActiveOrders(restaurantId);
      setPending(orders.filter((o) => o.status === "pending_confirmation").map(fromApi));
      setReadyToServe(
        orders
          .filter((o) => o.status === "ready")
          .map((o) => ({ order_id: o.id, table_id: o.table_id, table_label: o.table_label, ready_at: o.ready_at ?? null }))
      );
      setEnCuisine(
        orders
          .filter((o) => ["confirmed", "sent_to_kitchen", "in_preparation"].includes(o.status))
          .map((o) => ({ order_id: o.id, table_id: o.table_id }))
      );
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }, [restaurantId]);

  const loadCashRequests = useCallback(async () => {
    if (!restaurantId) return;
    try {
      const orders = await api.listPendingCashPayments(restaurantId);
      setCashRequests(
        orders.map((o) => ({
          order_id: o.id,
          table_id: o.table_id,
          table_label: o.table_label,
          amount: o.total_amount,
          taken_by_staff_id: o.taken_by_staff_id,
          // Optionnel sur `Order` depuis la Phase 12.2 (absent des réponses
          // client), mais toujours servi sur cette route protégée par JWT.
          loyalty_phone: o.loyalty_phone ?? null,
        }))
      );
      for (const o of orders) {
        if (o.loyalty_phone) fetchLoyaltyForPhone(restaurantId, o.loyalty_phone);
      }
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }, [restaurantId]);

  const loadCardTerminalRequests = useCallback(async () => {
    if (!restaurantId) return;
    try {
      const orders = await api.listPendingCardTerminalPayments(restaurantId);
      setCardTerminalRequests(
        orders.map((o) => ({
          order_id: o.id,
          table_id: o.table_id,
          table_label: o.table_label,
          amount: o.total_amount,
          taken_by_staff_id: o.taken_by_staff_id,
          loyalty_phone: o.loyalty_phone ?? null,
        }))
      );
      for (const o of orders) {
        if (o.loyalty_phone) fetchLoyaltyForPhone(restaurantId, o.loyalty_phone);
      }
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }, [restaurantId]);

  const loadPlan = useCallback(async () => {
    if (!restaurantId) return;
    // Best-effort : une salle non dessinée ne doit pas empêcher le service.
    try {
      setPlan(await api.getPlan(restaurantId));
    } catch {
      setPlan([]);
    }
  }, [restaurantId]);

  const loadMyShift = useCallback(async () => {
    // Best-effort : ses chiffres personnels ne doivent jamais empêcher l'écran
    // de service de s'afficher.
    try {
      setMyShift(await api.getMyShift());
    } catch {
      setMyShift(null);
    }
  }, []);

  const loadWaiterCalls = useCallback(async () => {
    if (!restaurantId) return;
    try {
      const calls = await api.listPendingWaiterCalls(restaurantId);
      setWaiterCalls(calls.map((c) => ({ call_id: c.id, table_id: c.table_id, table_label: c.table_label, created_at: c.created_at })));
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }, [restaurantId]);

  // Recharge au montage : le WebSocket seul ne rattrape jamais les
  // commandes déjà en attente avant l'ouverture de cette page.
  useEffect(() => {
    if (restaurantId) {
      loadActiveOrders();
      loadCashRequests();
      loadCardTerminalRequests();
      loadWaiterCalls();
      loadMyShift();
      loadPlan();
    }
  }, [restaurantId, loadActiveOrders, loadCashRequests, loadCardTerminalRequests, loadWaiterCalls, loadMyShift, loadPlan]);

  const status = useReconnectingSocket(restaurantId ? staffWsUrl(`/ws/staff/${restaurantId}`) : null, (msg) => {
    if (msg.event === "order.pending_confirmation") {
      setPending((prev) =>
        prev.some((o) => o.order_id === msg.order_id)
          ? prev
          : [
              ...prev,
              {
                order_id: msg.order_id,
                table_id: msg.table_id,
                table_label: msg.table_label,
                taken_by_staff_id: null,
                taken_by_staff_name: null,
                created_at: msg.created_at ?? null,
                scheduled_for: msg.scheduled_for ?? null,
              },
            ]
      );
    }
    if (msg.event === "order.sent_to_kitchen") {
      setEnCuisine((prev) =>
        prev.some((o) => o.order_id === msg.order_id)
          ? prev
          : [...prev, { order_id: msg.order_id, table_id: msg.table_id }]
      );
    }
    if (msg.event === "order.claimed") {
      setPending((prev) =>
        prev.map((o) =>
          o.order_id === msg.order_id
            ? { ...o, taken_by_staff_id: msg.taken_by_staff_id, taken_by_staff_name: msg.taken_by_staff_name }
            : o
        )
      );
    }
    if (msg.event === "order.ready") {
      setReadyToServe((prev) =>
        prev.some((o) => o.order_id === msg.order_id) ? prev : [...prev, { order_id: msg.order_id, table_id: msg.table_id, table_label: msg.table_label, ready_at: msg.ready_at ?? null }]
      );
      // La commande quitte la cuisine : sinon la table resterait « en cuisine »
      // sur le plan alors que le plat attend au passe.
      setEnCuisine((prev) => prev.filter((o) => o.order_id !== msg.order_id));
    }
    if (msg.event === "order.cash_requested") {
      setCashRequests((prev) =>
        prev.some((o) => o.order_id === msg.order_id)
          ? prev
          : [
              ...prev,
              {
                order_id: msg.order_id,
                table_id: msg.table_id,
                table_label: msg.table_label,
                amount: msg.amount,
                taken_by_staff_id: msg.taken_by_staff_id,
                loyalty_phone: msg.loyalty_phone ?? null,
              },
            ]
      );
      if (msg.loyalty_phone && restaurantId) fetchLoyaltyForPhone(restaurantId, msg.loyalty_phone);
    }
    if (msg.event === "order.card_terminal_requested") {
      setCardTerminalRequests((prev) =>
        prev.some((o) => o.order_id === msg.order_id)
          ? prev
          : [
              ...prev,
              {
                order_id: msg.order_id,
                table_id: msg.table_id,
                table_label: msg.table_label,
                amount: msg.amount,
                taken_by_staff_id: msg.taken_by_staff_id,
                loyalty_phone: msg.loyalty_phone ?? null,
              },
            ]
      );
      if (msg.loyalty_phone && restaurantId) fetchLoyaltyForPhone(restaurantId, msg.loyalty_phone);
    }
    if (msg.event === "waiter_call.created") {
      setWaiterCalls((prev) =>
        prev.some((c) => c.call_id === msg.call_id) ? prev : [...prev, { call_id: msg.call_id, table_id: msg.table_id, table_label: msg.table_label, created_at: msg.created_at ?? null }]
      );
    }
    if (msg.event === "waiter_call.resolved") {
      setWaiterCalls((prev) => prev.filter((c) => c.call_id !== msg.call_id));
    }
  });

  // Canal refusé (session expirée, compte désactivé par le manager) : le hook
  // a cessé de réessayer, on renvoie vers la connexion plutôt que de laisser un
  // écran figé en plein service.
  useEffect(() => {
    if (status === "unauthorized") {
      clearToken();
      router.push("/login");
    }
  }, [status, router]);

  // Une reconnexion après coupure peut avoir manqué des événements : on
  // recharge l'état complet à chaque retour en ligne, pas seulement au
  // premier montage.
  useEffect(() => {
    if (status === "connected") {
      loadActiveOrders();
      loadCashRequests();
      loadCardTerminalRequests();
      loadWaiterCalls();
      loadMyShift();
    }
  }, [status, loadActiveOrders, loadCashRequests, loadCardTerminalRequests, loadWaiterCalls, loadMyShift]);

  const etatsDesTables = useMemo(
    () =>
      construireEtats({
        aPrendre: pending.map((o) => ({
          table_id: o.table_id,
          depuis: o.created_at,
          parQui: o.taken_by_staff_name,
          aMoi: o.taken_by_staff_id === staff?.id,
        })),
        aServir: readyToServe.map((o) => ({ table_id: o.table_id, depuis: o.ready_at })),
        // Espèces et carte physique se traitent pareil sur le plan : une
        // table qui doit être encaissée s'allume, quel que soit le moyen —
        // seule la liste plus bas distingue les deux (2026-08-19).
        additions: [...cashRequests, ...cardTerminalRequests].map((o) => ({
          table_id: o.table_id,
          aMoi: o.taken_by_staff_id === staff?.id,
        })),
        appels: waiterCalls.map((c) => ({ table_id: c.table_id, depuis: c.created_at })),
        enCuisine,
      }),
    [pending, readyToServe, cashRequests, cardTerminalRequests, waiterCalls, enCuisine, staff?.id]
  );

  const salleDessinee = plan.some((t) => t.pos_x !== null && t.pos_y !== null);
  const tableActive = tableOuverte === null ? null : plan.find((t) => t.id === tableOuverte) ?? null;
  // Le même classement que celui affiché sur le plan : le panneau d'action doit
  // dire la même chose que la table qu'on vient de toucher.
  const rangs = useMemo(() => ordreDArrivee(etatsDesTables), [etatsDesTables]);

  /**
   * Ce que le serveur peut faire pour la table qu'il vient de toucher.
   *
   * Sans ça le plan ne fait que signaler : il faut redescendre dans la liste et
   * retrouver la bonne carte. Toutes les actions sont les mêmes qu'en bas de
   * page — c'est le même appel API, pas un chemin parallèle.
   */
  function actionsPourTable(tableId: number): ActionsTable {
    const appel = waiterCalls.find((c) => c.table_id === tableId);
    const aPrendre = pending.find((o) => o.table_id === tableId);
    const aServir = readyToServe.find((o) => o.table_id === tableId);
    const additionCash = cashRequests.find((o) => o.table_id === tableId);
    const additionCarte = cardTerminalRequests.find((o) => o.table_id === tableId);
    return {
      resoudreAppel: appel ? () => resolveWaiterCall(appel.call_id) : undefined,
      prendreEnCharge: aPrendre ? () => claim(aPrendre.order_id) : undefined,
      envoyerEnCuisine: aPrendre ? () => confirmAndSend(aPrendre.order_id) : undefined,
      servir: aServir ? () => markServed(aServir.order_id) : undefined,
      encaisser: additionCash
        ? () => confirmCash(additionCash.order_id)
        : additionCarte
          ? () => confirmCardTerminal(additionCarte.order_id)
          : undefined,
    };
  }

  async function claim(orderId: number) {
    setError(null);
    try {
      const updated = await api.claimOrder(orderId);
      setPending((prev) =>
        prev.map((o) =>
          o.order_id === orderId
            ? { ...o, taken_by_staff_id: updated.taken_by_staff_id, taken_by_staff_name: updated.taken_by_staff_name }
            : o
        )
      );
      // C'est la prise en charge qui compte dans « ma soirée », pas l'envoi en
      // cuisine : sans ce rafraîchissement, son compteur reste à zéro alors
      // qu'il vient de prendre la table.
      loadMyShift();
    } catch (e) {
      setError(toFrenchMessage(e));
      loadActiveOrders();
    }
  }

  async function confirmAndSend(orderId: number) {
    setError(null);
    try {
      // Le serveur doit d'abord vérifier la commande AVEC la table avant ce clic.
      await api.confirmOrder(orderId);
      await api.sendToKitchen(orderId);
      setPending((prev) => prev.filter((o) => o.order_id !== orderId));
      loadMyShift();
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  async function markServed(orderId: number) {
    setError(null);
    try {
      await api.markServed(orderId);
      setReadyToServe((prev) => prev.filter((o) => o.order_id !== orderId));
      loadMyShift();
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  async function confirmCash(orderId: number) {
    setError(null);
    try {
      await api.confirmCashPayment(orderId);
      setCashRequests((prev) => prev.filter((o) => o.order_id !== orderId));
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  async function confirmCardTerminal(orderId: number) {
    setError(null);
    try {
      await api.confirmCardTerminalPayment(orderId);
      setCardTerminalRequests((prev) => prev.filter((o) => o.order_id !== orderId));
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  async function resolveWaiterCall(callId: number) {
    setError(null);
    try {
      await api.resolveWaiterCall(callId);
      setWaiterCalls((prev) => prev.filter((c) => c.call_id !== callId));
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  async function redeemReward(member: LoyaltyMember) {
    setError(null);
    try {
      const updated = await api.redeemLoyaltyReward(member.id);
      setLoyaltyByPhone((prev) => ({ ...prev, [member.phone_number]: updated }));
      if (lookupResult?.id === member.id) setLookupResult(updated);
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  async function lookupLoyaltyByPhone() {
    if (!restaurantId || !lookupPhone.trim()) return;
    setLookupError(null);
    setLookupResult(null);
    try {
      const member = await api.getLoyaltyMemberForStaff(restaurantId, lookupPhone.trim());
      setLookupResult(member);
    } catch (e) {
      setLookupError(toFrenchMessage(e));
    }
  }

  function logout() {
    clearToken();
    router.push("/login");
  }

  /**
   * Filet de secours papier : quand le réseau tombe en plein service, l'équipe
   * bascule au carnet (voir terrain/PRISE_EN_MAIN.md). Le serveur doit pouvoir
   * emporter ce qui est en cours plutôt que de le recopier de mémoire.
   * L'écran cuisine avait déjà ce bouton, pas le pool serveur — or c'est lui
   * qui prend les commandes.
   */
  function printPending() {
    const win = window.open("", "_blank", "width=420,height=640");
    if (!win) return;
    const rows = pending
      .map(
        (o) => `
      <div style="margin-bottom:12px;padding-bottom:8px;border-bottom:1px dashed #000;">
        <strong>${escapeHtml(o.table_label)} — Commande #${o.order_id}</strong>
        ${o.taken_by_staff_name ? `<div>Pris en charge par ${escapeHtml(o.taken_by_staff_name)}</div>` : ""}
      </div>`
      )
      .join("");
    const cash = cashRequests
      .map(
        (c) => `<div>${escapeHtml(c.table_label)} — addition ${c.amount.toFixed(3)} DT (espèces)</div>`
      )
      .join("");
    win.document.write(
      `<html><head><title>Service en cours</title></head><body style="font-family:sans-serif;padding:12px;">
       <h3>À confirmer (${pending.length})</h3>${rows || "<div>aucune</div>"}
       <h3>Paiements en espèces (${cashRequests.length})</h3>${cash || "<div>aucun</div>"}
       </body></html>`
    );
    win.document.close();
    win.print();
  }

  if (staffLoading || !staff) {
    return (
      <div className="p-4 max-w-md mx-auto space-y-3">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-20 w-full mt-4" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  // Chaque serveur ne voit que les demandes de paiement de ses propres
  // tables (celles qu'il a prises en charge) — le manager voit tout.
  const myCashRequests =
    staff.role === "manager" ? cashRequests : cashRequests.filter((o) => o.taken_by_staff_id === staff.id);
  const myCardTerminalRequests =
    staff.role === "manager"
      ? cardTerminalRequests
      : cardTerminalRequests.filter((o) => o.taken_by_staff_id === staff.id);
  const encaissementRequests = [
    ...myCashRequests.map((o) => ({ ...o, methode: "espèces" as const, confirmer: () => confirmCash(o.order_id) })),
    ...myCardTerminalRequests.map((o) => ({ ...o, methode: "carte" as const, confirmer: () => confirmCardTerminal(o.order_id) })),
  ].sort((a, b) => a.order_id - b.order_id);

  // Tables où ce serveur a au moins une action en cours (commande ou
  // encaissement pris en charge) — le "prêt à servir" n'a pas de propriétaire
  // (premier arrivé), il ne compte donc pas ici.
  const mesTables = new Set<number>();
  pending.forEach((o) => {
    if (o.taken_by_staff_id === staff.id) mesTables.add(o.table_id);
  });
  cashRequests.forEach((o) => {
    if (o.taken_by_staff_id === staff.id) mesTables.add(o.table_id);
  });
  cardTerminalRequests.forEach((o) => {
    if (o.taken_by_staff_id === staff.id) mesTables.add(o.table_id);
  });

  const scheduledCount = pending.filter((o) => o.scheduled_for).length;
  const clock = new Date(now).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="min-h-screen bg-[var(--semoule)]">
      <header className="bg-[var(--espresso)] px-4 md:px-6 py-4 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <TawlaMark size={30} variant="reserveSombre" />
          <div>
            <h1 className={`${lalezar.className} text-[26px] leading-none text-[var(--semoule)]`}>Service</h1>
            <p className="text-[14px] font-semibold text-[rgba(246,239,221,.62)] mt-1">
              {staff.name} — {mesTables.size} table{mesTables.size > 1 ? "s" : ""} en charge
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <ConnectionBadge status={status} dark />
          <span className="text-[18px] font-semibold tabular-nums text-[var(--semoule)]">{clock}</span>
          <button
            onClick={printPending}
            data-visite="staff-filet"
            className="text-sm text-[var(--ink-on-espresso)] underline"
          >
            Imprimer (filet de secours)
          </button>
          <button onClick={logout} className="text-sm text-[var(--ink-on-espresso)] underline">
            Se déconnecter
          </button>
        </div>
      </header>

      <div className="p-4 max-w-md mx-auto md:max-w-none md:mx-0 md:px-6">
        {error && (
          <Card tone="danger" padding="sm" className="mb-4 text-sm text-[var(--harissa)] flex justify-between items-start gap-2">
            <span>{error}</span>
            <button onClick={() => setError(null)} aria-label="Fermer le message d'erreur" className="text-[var(--harissa)]">
              ✕
            </button>
          </Card>
        )}

        <div className="mb-5">
          <MaSoiree shift={myShift} tablesEnCharge={mesTables.size} />
        </div>

        {scheduledCount > 0 && (
          <Card tone="info" padding="sm" className="mb-4 text-sm text-[#8a6420] flex items-center gap-1.5">
            <MoonIcon className="w-4 h-4 shrink-0 text-[var(--laiton)]" />
            {scheduledCount} pré-commande{scheduledCount > 1 ? "s" : ""} pour l&apos;iftar à anticiper en cuisine.
          </Card>
        )}

        <div className={`grid grid-cols-1 gap-[18px] items-start ${vuePlan ? "xl:grid-cols-[588px_1fr]" : ""}`}>
          {vuePlan && (
            <div className="rounded-2xl border border-[var(--line)] bg-[var(--semoule-raised)] overflow-hidden">
              <div className="px-[14px] py-[11px] border-b border-[var(--line)] flex items-baseline gap-2 flex-wrap">
                <span className="text-[13.5px] font-bold text-[var(--encre)]">Plan de salle</span>
                <span className="text-xs text-[var(--ink-soft)]">Salle principale · {plan.length} tables</span>
                <button onClick={() => setVuePlan(false)} className="ms-auto text-sm underline text-[var(--laiton)]">
                  Voir la liste
                </button>
              </div>
              <div className="p-3">
                {salleDessinee ? (
                  <>
                    <PlanDeSalle
                      tables={plan}
                      etats={etatsDesTables}
                      onTableActivee={(t) => setTableOuverte((ouverte) => (ouverte === t.id ? null : t.id))}
                      tableSelectionnee={tableOuverte}
                      action={
                        tableActive && (
                          <ActionTable
                            table={tableActive}
                            etat={etatsDesTables[tableActive.id] ?? ETAT_LIBRE}
                            rang={rangs[tableActive.id] ?? null}
                            actions={actionsPourTable(tableActive.id)}
                            onFermer={() => setTableOuverte(null)}
                          />
                        )
                      }
                    />
                    <p className="text-xs text-[var(--ink-soft)] mt-2">
                      Touchez une table pour agir dessus. Quand plusieurs tables commandent en même
                      temps, le chiffre posé dessus donne l&apos;ordre d&apos;arrivée : la 1 attend
                      depuis le plus longtemps.
                    </p>
                  </>
                ) : (
                  <EmptyState message="Votre salle n'est pas encore dessinée." />
                )}
              </div>
            </div>
          )}

          {!vuePlan && salleDessinee && (
            <button
              onClick={() => setVuePlan(true)}
              className="text-sm underline text-[var(--laiton)] justify-self-start"
            >
              Voir le plan
            </button>
          )}

          {/* Colonne de droite : les quatre files, dans l'ordre où un serveur
              doit les regarder — ce qui attend d'être confirmé et les appels
              (harissa, action requise) d'abord, puis ce qui est prêt et les
              encaissements. */}
          <div className="flex flex-col gap-[14px]" data-visite="staff-files">
            <div className="rounded-2xl border border-[var(--line)] bg-[var(--semoule-raised)] overflow-hidden">
              <EntetePanneau titre="Commandes à confirmer" couleur="var(--harissa)" count={pending.length} />
              {pending.length === 0 && <FileVide message="Rien en attente" />}
              {pending.map((o) => {
                const takenByMe = o.taken_by_staff_id === staff.id;
                const takenByOther = o.taken_by_staff_id !== null && !takenByMe;
                const secondes = elapsedSeconds(o.created_at, maintenant);
                const tardive = secondes !== null && secondes >= ATTENTE_ALERTE_MINUTES * 60;
                return (
                  <div
                    key={o.order_id}
                    className="flex items-center gap-[14px] px-[14px] py-[11px] border-b border-[#efe6d2] last:border-b-0"
                    style={{ backgroundColor: tardive ? "rgba(214,64,30,.06)" : "transparent" }}
                  >
                    <span className={`${lalezar.className} text-[24px] leading-none min-w-[58px] text-[var(--encre)]`}>
                      {o.table_label}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="text-[13.5px] font-semibold text-[var(--encre)]">Commande #{o.order_id}</div>
                      {o.scheduled_for && (
                        <div className="text-xs text-[var(--laiton)] mt-0.5 flex items-center gap-1">
                          <MoonIcon className="w-3.5 h-3.5 shrink-0" />
                          Iftar {formatTime(o.scheduled_for)}
                        </div>
                      )}
                      {takenByOther && (
                        <p className="text-xs text-[var(--ink-soft)] mt-0.5">Pris en charge par {o.taken_by_staff_name}</p>
                      )}
                    </div>
                    {secondes !== null && (
                      <span
                        className="text-[12.5px] font-semibold tabular-nums min-w-[60px] text-end shrink-0"
                        style={{ color: tardive ? "var(--harissa)" : "var(--ink-soft)" }}
                      >
                        {duree(secondes)}
                      </span>
                    )}
                    {!takenByOther && (
                      <button
                        onClick={() => (takenByMe ? confirmAndSend(o.order_id) : claim(o.order_id))}
                        className="shrink-0 whitespace-nowrap rounded-[10px] px-[15px] py-[10px] text-[13px] font-bold bg-[var(--harissa)] text-[var(--semoule)]"
                      >
                        {takenByMe ? "Confirmer" : "Prendre en charge"}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="rounded-2xl border border-[var(--line)] bg-[var(--semoule-raised)] overflow-hidden">
              <EntetePanneau titre="Appels serveur" couleur="var(--harissa)" count={waiterCalls.length} />
              {waiterCalls.length === 0 && <FileVide message="Rien en attente" />}
              {waiterCalls.map((c) => (
                <div
                  key={c.call_id}
                  className="flex items-center gap-[14px] px-[14px] py-[11px] border-b border-[#efe6d2] last:border-b-0"
                  style={{ backgroundColor: "rgba(214,64,30,.06)" }}
                >
                  <span className={`${lalezar.className} text-[24px] leading-none min-w-[58px] text-[var(--encre)]`}>
                    {c.table_label}
                  </span>
                  <div className="min-w-0 flex-1 text-[13.5px] font-semibold text-[var(--encre)] inline-flex items-center gap-1.5">
                    <BellIcon className="w-4 h-4 shrink-0 text-[var(--harissa)]" />
                    Vous appelle
                  </div>
                  <button
                    onClick={() => resolveWaiterCall(c.call_id)}
                    className="shrink-0 whitespace-nowrap rounded-[10px] px-[15px] py-[10px] text-[13px] font-bold bg-[var(--harissa)] text-[var(--semoule)]"
                  >
                    Je prends
                  </button>
                </div>
              ))}
            </div>

            <div className="rounded-2xl border border-[var(--line)] bg-[var(--semoule-raised)] overflow-hidden">
              <EntetePanneau titre="Prêtes à servir" couleur="var(--menthe)" count={readyToServe.length} />
              {readyToServe.length === 0 && <FileVide message="Rien en attente" />}
              {readyToServe.map((o) => (
                <div
                  key={o.order_id}
                  className="flex items-center gap-[14px] px-[14px] py-[11px] border-b border-[#efe6d2] last:border-b-0"
                >
                  <span className={`${lalezar.className} text-[24px] leading-none min-w-[58px] text-[var(--encre)]`}>
                    {o.table_label}
                  </span>
                  <div className="min-w-0 flex-1 text-[13.5px] font-semibold text-[var(--encre)]">
                    Commande #{o.order_id} — prête en cuisine
                  </div>
                  <button
                    onClick={() => markServed(o.order_id)}
                    className="shrink-0 whitespace-nowrap rounded-[10px] px-[15px] py-[10px] text-[13px] font-bold bg-[var(--menthe)] text-[var(--semoule)]"
                  >
                    Servie
                  </button>
                </div>
              ))}
            </div>

            <div className="rounded-2xl border border-[var(--line)] bg-[var(--semoule-raised)] overflow-hidden">
              <EntetePanneau titre="Demandes d'encaissement" couleur="var(--laiton)" count={encaissementRequests.length} />
              {encaissementRequests.length === 0 && <FileVide message="Rien en attente" />}
              {encaissementRequests.map((o) => {
                const loyaltyMember = o.loyalty_phone ? loyaltyByPhone[o.loyalty_phone] : undefined;
                return (
                  <div key={`${o.methode}-${o.order_id}`} className="border-b border-[#efe6d2] last:border-b-0">
                    <div className="flex items-center gap-[14px] px-[14px] py-[11px]">
                      <span className={`${lalezar.className} text-[24px] leading-none min-w-[58px] text-[var(--encre)]`}>
                        {o.table_label}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="text-[13.5px] font-semibold text-[var(--encre)]">
                          Commande #{o.order_id} — {o.amount.toFixed(3)} DT
                        </div>
                        <div className="text-xs text-[var(--ink-soft)] mt-0.5">{o.methode === "espèces" ? "Espèces" : "Carte (terminal)"}</div>
                      </div>
                      <button
                        onClick={o.confirmer}
                        className="shrink-0 whitespace-nowrap rounded-[10px] px-[15px] py-[10px] text-[13px] font-bold bg-[var(--laiton)] text-[var(--espresso)]"
                      >
                        Encaisser
                      </button>
                    </div>
                    {loyaltyMember && (
                      <div className="mx-[14px] mb-[11px] rounded-xl border border-[rgba(184,134,46,.5)] bg-[var(--creme)] px-3 py-2.5 text-sm flex justify-between items-center gap-2 flex-wrap">
                        <span className="inline-flex items-center gap-1.5 flex-wrap text-[var(--encre)]">
                          <GiftIcon className="w-4 h-4 shrink-0 text-[var(--laiton)]" />
                          {loyaltyMember.phone_number} — {loyaltyMember.order_count} commande
                          {loyaltyMember.order_count > 1 ? "s" : ""}
                          {loyaltyMember.reward_available ? " — récompense disponible" : ""}
                          {loyaltyMember.is_birthday_today && (
                            <span className="inline-flex items-center gap-1">
                              — <CakeIcon className="w-3.5 h-3.5 shrink-0" /> anniversaire aujourd&apos;hui
                            </span>
                          )}
                        </span>
                        {loyaltyMember.reward_available && (
                          <Button variant="laiton" size="sm" className="shrink-0" onClick={() => redeemReward(loyaltyMember)}>
                            Récompense donnée
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <h2 className="text-lg font-semibold mt-8 mb-4 flex items-center gap-1.5 text-[var(--encre)]">
          <GiftIcon className="w-5 h-5 shrink-0 text-[var(--laiton)]" />
          Fidélité — vérifier un client
        </h2>
        <Card className="mb-3">
          <div className="flex gap-2">
            <input
              type="tel"
              value={lookupPhone}
              onChange={(e) => setLookupPhone(e.target.value)}
              placeholder="Numéro de téléphone du client"
              className="flex-1 bg-white border border-[var(--line)] rounded-xl px-3 py-2 text-sm"
            />
            <Button onClick={lookupLoyaltyByPhone}>Vérifier</Button>
          </div>
          {lookupError && <p className="mt-2 text-sm text-[var(--harissa)]">{lookupError}</p>}
          {lookupResult && (
            <div className="mt-3 rounded-xl border border-[rgba(184,134,46,.5)] bg-[var(--creme)] px-3 py-2.5 text-sm flex justify-between items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1.5 flex-wrap text-[var(--encre)]">
                <GiftIcon className="w-4 h-4 shrink-0 text-[var(--laiton)]" />
                {lookupResult.phone_number} — {lookupResult.order_count} commande
                {lookupResult.order_count > 1 ? "s" : ""}
                {lookupResult.reward_available
                  ? " — récompense disponible"
                  : ` — encore ${lookupResult.orders_until_reward} pour un article offert`}
                {lookupResult.is_birthday_today && (
                  <span className="inline-flex items-center gap-1">
                    — <CakeIcon className="w-3.5 h-3.5 shrink-0" /> anniversaire aujourd&apos;hui
                  </span>
                )}
              </span>
              {lookupResult.reward_available && (
                <Button variant="laiton" size="sm" className="shrink-0" onClick={() => redeemReward(lookupResult)}>
                  Récompense donnée
                </Button>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
