"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { lalezar } from "@/lib/fonts";
import { api, staffWsUrl, ApiError, Order, Restaurant } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { duree } from "@/lib/duree";
import { useReconnectingSocket } from "@/lib/useReconnectingSocket";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import { clearToken } from "@/lib/auth";
import ConnectionBadge from "@/components/ConnectionBadge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import { MoonIcon, UtensilsIcon } from "@/components/icons";
import Skeleton from "@/components/ui/Skeleton";

type KitchenOrder = {
  order_id: number;
  table_label: string;
  items: { name: string; quantity: number; notes: string | null; is_shared: boolean }[];
  scheduled_for: string | null;
  sent_to_kitchen_at: string | null;
};

// Au-delà de ce seuil, l'attente cuisine passe en alerte visuelle (harissa).
const ELAPSED_ALERT_MINUTES = 10;

function elapsedSeconds(iso: string | null, now: number): number | null {
  if (!iso) return null;
  return Math.max(0, (now - new Date(iso).getTime()) / 1000);
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] as string));
}

function orderFromApi(o: Order): KitchenOrder {
  return {
    order_id: o.id,
    table_label: o.table_label,
    items: o.items.map((i) => ({
      name: i.menu_item_name,
      quantity: i.quantity,
      notes: i.notes,
      is_shared: i.is_shared,
    })),
    scheduled_for: o.scheduled_for,
    sent_to_kitchen_at: o.sent_to_kitchen_at,
  };
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

// Chime synthétisé en Web Audio (deux notes courtes) — zéro fichier audio à
// héberger. Best-effort : les politiques autoplay de certains navigateurs
// bloquent l'audio tant qu'aucun geste utilisateur n'a eu lieu sur la page ;
// ça ne doit jamais faire planter l'écran cuisine.
function playKitchenChime() {
  try {
    const AudioContextCtor =
      window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new AudioContextCtor();
    const now = ctx.currentTime;
    [880, 1174.66].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = freq;
      const start = now + i * 0.14;
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(0.25, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.35);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.4);
    });
  } catch {
    // Navigateur sans Web Audio ou audio bloqué — pas de son, rien d'autre.
  }
}

export default function KitchenPage() {
  const router = useRouter();
  const { staff, loading: staffLoading } = useCurrentStaff(["kitchen", "manager"]);
  const [orders, setOrders] = useState<KitchenOrder[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [todayCount, setTodayCount] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(tick);
  }, []);

  const restaurantId = staff?.restaurant_id ?? null;

  const loadActiveOrders = useCallback(async () => {
    if (!restaurantId) return;
    try {
      const active = await api.listActiveOrders(restaurantId);
      setOrders(
        active
          .filter((o) => o.status === "sent_to_kitchen" || o.status === "in_preparation")
          .map(orderFromApi)
      );
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }, [restaurantId]);

  const loadRestaurant = useCallback(async () => {
    if (!restaurantId) return;
    try {
      setRestaurant(await api.getRestaurant(restaurantId));
    } catch {
      // Best-effort : sans cette info, le retour sonore reste simplement
      // désactivé (comportement par défaut), rien d'autre ne dépend d'elle.
    }
  }, [restaurantId]);

  const loadTodayCount = useCallback(async () => {
    if (!restaurantId) return;
    try {
      const { count } = await api.getKitchenTodayCount(restaurantId);
      setTodayCount(count);
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }, [restaurantId]);

  // Rechargement au montage : sans ça, un écran cuisine qui plante ou se
  // rafraîchit perd toutes les commandes en cours (bug corrigé suite à
  // l'audit du 2026-08-10).
  useEffect(() => {
    if (restaurantId) {
      loadActiveOrders();
      loadRestaurant();
      loadTodayCount();
    }
  }, [restaurantId, loadActiveOrders, loadRestaurant, loadTodayCount]);

  const status = useReconnectingSocket(restaurantId ? staffWsUrl(`/ws/kitchen/${restaurantId}`) : null, (msg) => {
    if (msg.event === "order.sent_to_kitchen") {
      setOrders((prev) =>
        prev.some((o) => o.order_id === msg.order_id)
          ? prev
          : [
              ...prev,
              {
                order_id: msg.order_id,
                table_label: msg.table_label,
                items: msg.items,
                scheduled_for: msg.scheduled_for ?? null,
                sent_to_kitchen_at: msg.sent_to_kitchen_at ?? null,
              },
            ]
      );
      setTodayCount((prev) => (prev === null ? prev : prev + 1));
      if (restaurant?.kitchen_sound_enabled) playKitchenChime();
    }
  });

  // Canal refusé (session expirée, compte désactivé par le manager) : le hook
  // a cessé de réessayer, on renvoie vers la connexion plutôt que de laisser
  // l'écran cuisine figé en plein service.
  useEffect(() => {
    if (status === "unauthorized") {
      clearToken();
      router.push("/login");
    }
  }, [status, router]);

  useEffect(() => {
    if (status === "connected") {
      loadActiveOrders();
      loadTodayCount();
    }
  }, [status, loadActiveOrders, loadTodayCount]);

  async function markDone(orderId: number) {
    setError(null);
    try {
      await api.startPreparation(orderId);
    } catch (e) {
      // Une commande déjà en préparation (ex: reconnexion après un clic
      // parti au moment de la coupure) n'est pas une vraie erreur ; toute
      // autre erreur doit interrompre le passage à "prêt".
      if (!(e instanceof ApiError && e.code === "INVALID_TRANSITION")) {
        setError(toFrenchMessage(e));
        return;
      }
    }
    try {
      await api.markReady(orderId);
      setOrders((prev) => prev.filter((o) => o.order_id !== orderId));
    } catch (e) {
      setError(toFrenchMessage(e));
    }
  }

  function printTickets() {
    const win = window.open("", "_blank", "width=420,height=640");
    if (!win) return;
    const rows = orders
      .map(
        (o) => `
      <div style="margin-bottom:14px;padding-bottom:10px;border-bottom:1px dashed #000;">
        <strong>${escapeHtml(o.table_label)} — Commande #${o.order_id}</strong>
        <ul style="margin:4px 0 0;padding-left:18px;">
          ${o.items
            .map(
              (it) =>
                `<li>${it.quantity}× ${escapeHtml(it.name)}${it.is_shared ? " (à partager)" : ""}${it.notes ? " — " + escapeHtml(it.notes) : ""}</li>`
            )
            .join("")}
        </ul>
      </div>`
      )
      .join("");
    win.document.write(
      `<html><head><title>Commandes en cours</title></head><body style="font-family:monospace;padding:12px;">` +
        `<h3>Filet de secours — commandes en cours</h3>` +
        (rows || "<p>Aucune commande en cours.</p>") +
        `</body></html>`
    );
    win.document.close();
    win.focus();
    win.print();
  }

  function logout() {
    clearToken();
    router.push("/login");
  }

  if (staffLoading || !staff) {
    return (
      <div className="p-6 bg-neutral-950 min-h-screen">
        <Skeleton dark className="h-8 w-48" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
          <Skeleton dark className="h-40 w-full" />
          <Skeleton dark className="h-40 w-full" />
          <Skeleton dark className="h-40 w-full" />
        </div>
      </div>
    );
  }

  const scheduledCount = orders.filter((o) => o.scheduled_for).length;

  return (
    // L'écran cuisine tourne parfois sur un simple téléphone posé sur une
    // étagère, pas sur le grand écran pour lequel il a été dessiné : sans
    // `overflow-x-hidden` et sans passage à la ligne des actions, la page
    // débordait latéralement à 360 px et le bouton de déconnexion sortait du
    // cadre sombre (vérifié en navigateur, Phase 15).
    <div className="p-4 sm:p-6 bg-neutral-950 min-h-screen text-white overflow-x-hidden">
      <div className="flex items-center justify-between mb-1 flex-wrap gap-3">
        <h1 className={`${lalezar.className} text-2xl sm:text-3xl`}>Écran cuisine</h1>
        <div className="flex items-center gap-3 flex-wrap">
          <ConnectionBadge status={status} dark />
          <Button variant="secondary" dark onClick={printTickets}>
            Imprimer (filet de secours)
          </Button>
          <button onClick={logout} className="text-sm text-neutral-400 underline">
            Se déconnecter
          </button>
        </div>
      </div>

      <p className="text-sm text-neutral-500 mb-4">
        {todayCount === null
          ? "…"
          : `${todayCount} commande${todayCount > 1 ? "s" : ""} traitée${todayCount > 1 ? "s" : ""} aujourd'hui`}
      </p>

      {error && (
        <Card tone="danger" dark padding="sm" className="mb-4 text-sm text-red-300">
          {error}
        </Card>
      )}

      {scheduledCount > 0 && (
        <Card tone="info" dark padding="sm" className="mb-2 text-sm text-indigo-200 flex items-center gap-1.5">
          <MoonIcon className="w-4 h-4 shrink-0" />
          {scheduledCount} pré-commande{scheduledCount > 1 ? "s" : ""} iftar à anticiper.
        </Card>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
        {orders.map((o) => (
          <Card key={o.order_id} dark padding="md" className="text-white">
            <div className="flex justify-between items-baseline mb-1">
              <span className="text-xl font-bold">{o.table_label}</span>
              <span className="text-neutral-500 text-sm">#{o.order_id}</span>
            </div>
            {(() => {
              const secondes = elapsedSeconds(o.sent_to_kitchen_at, now);
              if (secondes === null) return null;
              const late = secondes >= ELAPSED_ALERT_MINUTES * 60;
              return (
                <Badge tone={late ? "danger" : "neutral"} dark className="mb-2">
                  il y a {duree(secondes)}
                </Badge>
              );
            })()}
            {o.scheduled_for && (
              <div className="text-xs text-indigo-300 mb-2 flex items-center gap-1">
                <MoonIcon className="w-3.5 h-3.5 shrink-0" />
                Iftar {formatTime(o.scheduled_for)}
              </div>
            )}
            <ul className="space-y-1 mb-4">
              {o.items.map((it, i) => (
                <li key={i}>
                  <span className="font-medium">{it.quantity}×</span> {it.name}
                  {it.is_shared && (
                    <Badge tone="warning" dark className="ms-1.5 inline-flex items-center gap-1">
                      <UtensilsIcon className="w-3 h-3 shrink-0" />
                      à partager
                    </Badge>
                  )}
                  {it.notes && <span className="text-neutral-500"> — {it.notes}</span>}
                </li>
              ))}
            </ul>
            <Button variant="success" dark className="w-full" onClick={() => markDone(o.order_id)}>
              Prêt
            </Button>
          </Card>
        ))}
      </div>
      {orders.length === 0 && <EmptyState message="Aucune commande en cuisine." dark className="mt-4" />}
    </div>
  );
}
