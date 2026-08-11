"use client";

import { useCallback, useEffect, useState } from "react";
import { api, wsUrl, LoyaltyMember, Order } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { useReconnectingSocket } from "@/lib/useReconnectingSocket";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import { clearToken } from "@/lib/auth";
import { useRouter } from "next/navigation";
import ConnectionBadge from "@/components/ConnectionBadge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";
import { BellIcon, MoonIcon, GiftIcon, CakeIcon } from "@/components/icons";

type PendingOrder = {
  order_id: number;
  table_id: number;
  taken_by_staff_id: number | null;
  taken_by_staff_name: string | null;
  scheduled_for: string | null;
};
type ReadyOrder = { order_id: number; table_id: number };
type CashRequest = {
  order_id: number;
  table_id: number;
  amount: number;
  taken_by_staff_id: number | null;
  loyalty_phone: string | null;
};
type WaiterCall = { call_id: number; table_id: number };

function fromApi(o: Order): PendingOrder {
  return {
    order_id: o.id,
    table_id: o.table_id,
    taken_by_staff_id: o.taken_by_staff_id,
    taken_by_staff_name: o.taken_by_staff_name,
    scheduled_for: o.scheduled_for,
  };
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

export default function StaffPage() {
  const router = useRouter();
  const { staff, loading: staffLoading } = useCurrentStaff(["waiter", "manager"]);
  const [pending, setPending] = useState<PendingOrder[]>([]);
  const [readyToServe, setReadyToServe] = useState<ReadyOrder[]>([]);
  const [cashRequests, setCashRequests] = useState<CashRequest[]>([]);
  const [waiterCalls, setWaiterCalls] = useState<WaiterCall[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loyaltyByPhone, setLoyaltyByPhone] = useState<Record<string, LoyaltyMember>>({});
  const [lookupPhone, setLookupPhone] = useState("");
  const [lookupResult, setLookupResult] = useState<LoyaltyMember | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);

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
        orders.filter((o) => o.status === "ready").map((o) => ({ order_id: o.id, table_id: o.table_id }))
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
          amount: o.total_amount,
          taken_by_staff_id: o.taken_by_staff_id,
          loyalty_phone: o.loyalty_phone,
        }))
      );
      for (const o of orders) {
        if (o.loyalty_phone) fetchLoyaltyForPhone(restaurantId, o.loyalty_phone);
      }
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }, [restaurantId]);

  const loadWaiterCalls = useCallback(async () => {
    if (!restaurantId) return;
    try {
      const calls = await api.listPendingWaiterCalls(restaurantId);
      setWaiterCalls(calls.map((c) => ({ call_id: c.id, table_id: c.table_id })));
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
      loadWaiterCalls();
    }
  }, [restaurantId, loadActiveOrders, loadCashRequests, loadWaiterCalls]);

  const status = useReconnectingSocket(restaurantId ? wsUrl(`/ws/staff/${restaurantId}`) : null, (msg) => {
    if (msg.event === "order.pending_confirmation") {
      setPending((prev) =>
        prev.some((o) => o.order_id === msg.order_id)
          ? prev
          : [
              ...prev,
              {
                order_id: msg.order_id,
                table_id: msg.table_id,
                taken_by_staff_id: null,
                taken_by_staff_name: null,
                scheduled_for: msg.scheduled_for ?? null,
              },
            ]
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
        prev.some((o) => o.order_id === msg.order_id) ? prev : [...prev, { order_id: msg.order_id, table_id: msg.table_id }]
      );
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
        prev.some((c) => c.call_id === msg.call_id) ? prev : [...prev, { call_id: msg.call_id, table_id: msg.table_id }]
      );
    }
    if (msg.event === "waiter_call.resolved") {
      setWaiterCalls((prev) => prev.filter((c) => c.call_id !== msg.call_id));
    }
  });

  // Une reconnexion après coupure peut avoir manqué des événements : on
  // recharge l'état complet à chaque retour en ligne, pas seulement au
  // premier montage.
  useEffect(() => {
    if (status === "connected") {
      loadActiveOrders();
      loadCashRequests();
      loadWaiterCalls();
    }
  }, [status, loadActiveOrders, loadCashRequests, loadWaiterCalls]);

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
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  async function markServed(orderId: number) {
    setError(null);
    try {
      await api.markServed(orderId);
      setReadyToServe((prev) => prev.filter((o) => o.order_id !== orderId));
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

  if (staffLoading || !staff) return null;

  // Chaque serveur ne voit que les demandes de paiement de ses propres
  // tables (celles qu'il a prises en charge) — le manager voit tout.
  const myCashRequests =
    staff.role === "manager" ? cashRequests : cashRequests.filter((o) => o.taken_by_staff_id === staff.id);

  const scheduledCount = pending.filter((o) => o.scheduled_for).length;

  return (
    <div className="p-4 max-w-md mx-auto">
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-lg font-semibold">Commandes à confirmer</h1>
        <ConnectionBadge status={status} />
      </div>
      <div className="flex items-center justify-between mb-4 text-sm text-neutral-500">
        <span>{staff.name}</span>
        <button onClick={logout} className="underline">
          Se déconnecter
        </button>
      </div>

      {error && (
        <Card tone="danger" padding="sm" className="mb-4 text-sm text-red-700 flex justify-between items-start gap-2">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Fermer le message d'erreur" className="text-red-500">
            ✕
          </button>
        </Card>
      )}

      {waiterCalls.length > 0 && (
        <div className="mb-4">
          <h2 className="text-lg font-semibold mb-2 flex items-center gap-1.5">
            <BellIcon className="w-5 h-5 shrink-0" />
            Appels en attente
          </h2>
          {waiterCalls.map((c) => (
            <Card key={c.call_id} tone="urgent" className="mb-3 flex justify-between items-center">
              <div className="font-medium">Table {c.table_id}</div>
              <Button variant="success" onClick={() => resolveWaiterCall(c.call_id)}>
                Résolu
              </Button>
            </Card>
          ))}
        </div>
      )}

      {scheduledCount > 0 && (
        <Card tone="info" padding="sm" className="mb-3 text-sm text-indigo-800 flex items-center gap-1.5">
          <MoonIcon className="w-4 h-4 shrink-0" />
          {scheduledCount} pré-commande{scheduledCount > 1 ? "s" : ""} pour l&apos;iftar à anticiper en cuisine.
        </Card>
      )}

      {pending.length === 0 && <EmptyState message="Aucune commande en attente." />}
      {pending.map((o) => {
        const takenByMe = o.taken_by_staff_id === staff.id;
        const takenByOther = o.taken_by_staff_id !== null && !takenByMe;
        return (
          <Card key={o.order_id} className="mb-3">
            <div className="flex justify-between items-center">
              <div>
                <div className="font-medium">Table {o.table_id}</div>
                <div className="text-sm text-neutral-500">Commande #{o.order_id}</div>
                {o.scheduled_for && (
                  <div className="text-xs text-indigo-700 mt-1 flex items-center gap-1">
                    <MoonIcon className="w-3.5 h-3.5 shrink-0" />
                    Pré-commande iftar {formatTime(o.scheduled_for)}
                  </div>
                )}
              </div>
              {!takenByOther && (
                <Button onClick={() => (takenByMe ? confirmAndSend(o.order_id) : claim(o.order_id))}>
                  {takenByMe ? "Confirmé avec la table → cuisine" : "Prendre en charge"}
                </Button>
              )}
            </div>
            {takenByOther && (
              <p className="text-sm text-neutral-500 mt-2">Pris en charge par {o.taken_by_staff_name}</p>
            )}
          </Card>
        );
      })}

      <h2 className="text-lg font-semibold mt-8 mb-4">Prêtes à servir</h2>
      {readyToServe.length === 0 && <EmptyState message="Rien à servir pour l'instant." />}
      {readyToServe.map((o) => (
        <Card key={o.order_id} tone="success" className="mb-3 flex justify-between items-center">
          <div>
            <div className="font-medium">Table {o.table_id}</div>
            <div className="text-sm text-neutral-500">Commande #{o.order_id} — prête en cuisine</div>
          </div>
          <Button variant="success" onClick={() => markServed(o.order_id)}>
            Servi
          </Button>
        </Card>
      ))}

      <h2 className="text-lg font-semibold mt-8 mb-4">Demandes de paiement en espèces</h2>
      {myCashRequests.length === 0 && <EmptyState message="Aucune demande en attente." />}
      {myCashRequests.map((o) => {
        const loyaltyMember = o.loyalty_phone ? loyaltyByPhone[o.loyalty_phone] : undefined;
        return (
          <Card key={o.order_id} tone="warning" className="mb-3">
            <div className="flex justify-between items-center">
              <div>
                <div className="font-medium">Table {o.table_id}</div>
                <div className="text-sm text-neutral-500">
                  Commande #{o.order_id} — {o.amount.toFixed(2)} DT
                </div>
              </div>
              <Button variant="success" onClick={() => confirmCash(o.order_id)}>
                Encaissé
              </Button>
            </div>
            {loyaltyMember && (
              <Card tone="warning" padding="sm" className="mt-3 text-sm flex justify-between items-center gap-2">
                <span className="inline-flex items-center gap-1.5 flex-wrap">
                  <GiftIcon className="w-4 h-4 shrink-0" />
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
                  <Button variant="success" size="sm" className="shrink-0" onClick={() => redeemReward(loyaltyMember)}>
                    Récompense donnée
                  </Button>
                )}
              </Card>
            )}
          </Card>
        );
      })}

      <h2 className="text-lg font-semibold mt-8 mb-4 flex items-center gap-1.5">
        <GiftIcon className="w-5 h-5 shrink-0" />
        Fidélité — vérifier un client
      </h2>
      <Card className="mb-3">
        <div className="flex gap-2">
          <input
            type="tel"
            value={lookupPhone}
            onChange={(e) => setLookupPhone(e.target.value)}
            placeholder="Numéro de téléphone du client"
            className="flex-1 border rounded-lg px-3 py-2 text-sm"
          />
          <Button onClick={lookupLoyaltyByPhone}>Vérifier</Button>
        </div>
        {lookupError && <p className="mt-2 text-sm text-red-700">{lookupError}</p>}
        {lookupResult && (
          <Card tone="warning" padding="sm" className="mt-3 text-sm flex justify-between items-center gap-2">
            <span className="inline-flex items-center gap-1.5 flex-wrap">
              <GiftIcon className="w-4 h-4 shrink-0" />
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
              <Button variant="success" size="sm" className="shrink-0" onClick={() => redeemReward(lookupResult)}>
                Récompense donnée
              </Button>
            )}
          </Card>
        )}
      </Card>
    </div>
  );
}
