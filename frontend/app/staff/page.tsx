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
};
type ReadyOrder = { order_id: number; table_id: number };

function fromApi(o: Order): PendingOrder {
  return {
    order_id: o.id,
    table_id: o.table_id,
    taken_by_staff_id: o.taken_by_staff_id,
    taken_by_staff_name: o.taken_by_staff_name,
  };
}

export default function StaffPage() {
  const router = useRouter();
  const { staff, loading: staffLoading } = useCurrentStaff(["waiter", "manager"]);
  const [pending, setPending] = useState<PendingOrder[]>([]);
  const [readyToServe, setReadyToServe] = useState<ReadyOrder[]>([]);
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

  // Recharge au montage : le WebSocket seul ne rattrape jamais les
  // commandes déjà en attente avant l'ouverture de cette page.
  useEffect(() => {
    if (restaurantId) loadActiveOrders();
  }, [restaurantId, loadActiveOrders]);

  const status = useReconnectingSocket(restaurantId ? wsUrl(`/ws/staff/${restaurantId}`) : null, (msg) => {
    if (msg.event === "order.pending_confirmation") {
      setPending((prev) =>
        prev.some((o) => o.order_id === msg.order_id)
          ? prev
          : [...prev, { order_id: msg.order_id, table_id: msg.table_id, taken_by_staff_id: null, taken_by_staff_name: null }]
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
  });

  // Une reconnexion après coupure peut avoir manqué des événements : on
  // recharge l'état complet à chaque retour en ligne, pas seulement au
  // premier montage.
  useEffect(() => {
    if (status === "connected") loadActiveOrders();
  }, [status, loadActiveOrders]);

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

  function logout() {
    clearToken();
    router.push("/login");
  }

  if (staffLoading || !staff) return null;

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
    </div>
  );
}
