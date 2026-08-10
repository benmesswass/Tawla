"use client";

import { useCallback, useEffect, useState } from "react";
import { api, wsUrl, Order } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { useReconnectingSocket } from "@/lib/useReconnectingSocket";
import ConnectionBadge from "@/components/ConnectionBadge";

// MVP mono-restaurant : restaurant_id en query param (?restaurant_id=1).
// Passera par une session/login serveur quand on aura plusieurs restos.
function useRestaurantId(): number {
  if (typeof window === "undefined") return 1;
  const params = new URLSearchParams(window.location.search);
  return Number(params.get("restaurant_id") ?? 1);
}

type PendingOrder = { order_id: number; table_id: number };

export default function StaffPage() {
  const restaurantId = useRestaurantId();
  const [pending, setPending] = useState<PendingOrder[]>([]);
  const [readyToServe, setReadyToServe] = useState<PendingOrder[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadActiveOrders = useCallback(async () => {
    try {
      const orders = await api.listActiveOrders(restaurantId);
      setPending(
        orders
          .filter((o: Order) => o.status === "pending_confirmation")
          .map((o) => ({ order_id: o.id, table_id: o.table_id }))
      );
      setReadyToServe(
        orders.filter((o: Order) => o.status === "ready").map((o) => ({ order_id: o.id, table_id: o.table_id }))
      );
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }, [restaurantId]);

  // Recharge au montage : le WebSocket seul ne rattrape jamais les
  // commandes déjà en attente avant l'ouverture de cette page (bug corrigé
  // suite à l'audit du 2026-08-10).
  useEffect(() => {
    loadActiveOrders();
  }, [loadActiveOrders]);

  const status = useReconnectingSocket(wsUrl(`/ws/staff/${restaurantId}`), (msg) => {
    if (msg.event === "order.pending_confirmation") {
      setPending((prev) =>
        prev.some((o) => o.order_id === msg.order_id) ? prev : [...prev, { order_id: msg.order_id, table_id: msg.table_id }]
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

  return (
    <div className="p-4 max-w-md mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold">Commandes à confirmer</h1>
        <ConnectionBadge status={status} />
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
      {pending.map((o) => (
        <div key={o.order_id} className="border rounded-lg p-4 mb-3 flex justify-between items-center">
          <div>
            <div className="font-medium">Table {o.table_id}</div>
            <div className="text-sm text-neutral-500">Commande #{o.order_id}</div>
          </div>
          <button
            onClick={() => confirmAndSend(o.order_id)}
            className="bg-neutral-900 text-white px-3 py-2 rounded-lg text-sm"
          >
            Confirmé avec la table → cuisine
          </button>
        </div>
      ))}

      <h2 className="text-lg font-semibold mt-8 mb-4">Prêtes à servir</h2>
      {readyToServe.length === 0 && <p className="text-neutral-500">Rien à servir pour l'instant.</p>}
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
