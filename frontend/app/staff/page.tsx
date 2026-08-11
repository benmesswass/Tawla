"use client";

import { useCallback, useEffect, useState } from "react";
import { api, wsUrl, Order } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { useReconnectingSocket } from "@/lib/useReconnectingSocket";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import { clearToken } from "@/lib/auth";
import { useRouter } from "next/navigation";
import ConnectionBadge from "@/components/ConnectionBadge";

type PendingOrder = {
  order_id: number;
  table_id: number;
  taken_by_staff_id: number | null;
  taken_by_staff_name: string | null;
  scheduled_for: string | null;
};
type ReadyOrder = { order_id: number; table_id: number };
type CashRequest = { order_id: number; table_id: number; amount: number; taken_by_staff_id: number | null };
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

  const restaurantId = staff?.restaurant_id ?? null;

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
        }))
      );
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
              },
            ]
      );
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
        <div className="mb-4 text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3 flex justify-between items-start gap-2">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Fermer le message d'erreur" className="text-red-500">
            ✕
          </button>
        </div>
      )}

      {waiterCalls.length > 0 && (
        <div className="mb-4">
          <h2 className="text-lg font-semibold mb-2">🔔 Appels en attente</h2>
          {waiterCalls.map((c) => (
            <div
              key={c.call_id}
              className="border rounded-lg p-4 mb-3 flex justify-between items-center bg-rose-50 border-rose-200"
            >
              <div className="font-medium">Table {c.table_id}</div>
              <button
                onClick={() => resolveWaiterCall(c.call_id)}
                className="bg-rose-600 text-white px-3 py-2 rounded-lg text-sm"
              >
                Résolu
              </button>
            </div>
          ))}
        </div>
      )}

      {scheduledCount > 0 && (
        <p className="mb-3 text-sm bg-indigo-50 text-indigo-800 border border-indigo-200 rounded-lg py-2 px-3">
          🌙 {scheduledCount} pré-commande{scheduledCount > 1 ? "s" : ""} pour l&apos;iftar à anticiper en cuisine.
        </p>
      )}

      {pending.length === 0 && <p className="text-neutral-500">Aucune commande en attente.</p>}
      {pending.map((o) => {
        const takenByMe = o.taken_by_staff_id === staff.id;
        const takenByOther = o.taken_by_staff_id !== null && !takenByMe;
        return (
          <div key={o.order_id} className="border rounded-lg p-4 mb-3">
            <div className="flex justify-between items-center">
              <div>
                <div className="font-medium">Table {o.table_id}</div>
                <div className="text-sm text-neutral-500">Commande #{o.order_id}</div>
                {o.scheduled_for && (
                  <div className="text-xs text-indigo-700 mt-1">🌙 Pré-commande iftar {formatTime(o.scheduled_for)}</div>
                )}
              </div>
              {!takenByOther && (
                <button
                  onClick={() => (takenByMe ? confirmAndSend(o.order_id) : claim(o.order_id))}
                  className="bg-neutral-900 text-white px-3 py-2 rounded-lg text-sm"
                >
                  {takenByMe ? "Confirmé avec la table → cuisine" : "Prendre en charge"}
                </button>
              )}
            </div>
            {takenByOther && (
              <p className="text-sm text-neutral-500 mt-2">Pris en charge par {o.taken_by_staff_name}</p>
            )}
          </div>
        );
      })}

      <h2 className="text-lg font-semibold mt-8 mb-4">Prêtes à servir</h2>
      {readyToServe.length === 0 && <p className="text-neutral-500">Rien à servir pour l&apos;instant.</p>}
      {readyToServe.map((o) => (
        <div key={o.order_id} className="border rounded-lg p-4 mb-3 flex justify-between items-center bg-emerald-50">
          <div>
            <div className="font-medium">Table {o.table_id}</div>
            <div className="text-sm text-neutral-500">Commande #{o.order_id} — prête en cuisine</div>
          </div>
          <button
            onClick={() => markServed(o.order_id)}
            className="bg-emerald-600 text-white px-3 py-2 rounded-lg text-sm"
          >
            Servi
          </button>
        </div>
      ))}

      <h2 className="text-lg font-semibold mt-8 mb-4">Demandes de paiement en espèces</h2>
      {myCashRequests.length === 0 && <p className="text-neutral-500">Aucune demande en attente.</p>}
      {myCashRequests.map((o) => (
        <div key={o.order_id} className="border rounded-lg p-4 mb-3 flex justify-between items-center bg-amber-50">
          <div>
            <div className="font-medium">Table {o.table_id}</div>
            <div className="text-sm text-neutral-500">
              Commande #{o.order_id} — {o.amount.toFixed(2)} DT
            </div>
          </div>
          <button
            onClick={() => confirmCash(o.order_id)}
            className="bg-amber-700 text-white px-3 py-2 rounded-lg text-sm"
          >
            Encaissé
          </button>
        </div>
      ))}
    </div>
  );
}
