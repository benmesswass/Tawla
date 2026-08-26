"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { lalezar } from "@/lib/fonts";
import { api, staffWsUrl, ApiError, Order, Restaurant } from "@/lib/api";
import { toFrenchMessage } from "@/lib/errors";
import { duree, elapsedSeconds } from "@/lib/duree";
import { useReconnectingSocket } from "@/lib/useReconnectingSocket";
import { useCurrentStaff } from "@/lib/useCurrentStaff";
import { useAccesDemoParLien } from "@/lib/demoLien";
import { clearToken } from "@/lib/auth";
import ConnectionBadge from "@/components/ConnectionBadge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";
import { MoonIcon, UtensilsIcon } from "@/components/icons";
import Skeleton from "@/components/ui/Skeleton";
import TawlaMark from "@/components/brand/TawlaMark";

type KitchenOrder = {
  order_id: number;
  table_label: string;
  items: {
    name: string;
    quantity: number;
    notes: string | null;
    is_shared: boolean;
    shared_with: number[];
    // Choix figés (« Cuisson : à point »...) — France, MARCHE_FRANCE.md phase
    // F5/A2 : ce que la cuisine doit réellement préparer, pas seulement l'article.
    options: { group_name: string; option_name: string }[];
  }[];
  scheduled_for: string | null;
  sent_to_kitchen_at: string | null;
  preparation_started_at: string | null;
  // « à préparer » tant que personne ne s'en est saisi, « en cours » ensuite.
  en_cours: boolean;
};

type KitchenTab = "todo" | "in_progress" | "done";

// Au-delà de ce seuil, l'attente cuisine passe en alerte visuelle (harissa).
const ELAPSED_ALERT_MINUTES = 10;

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
      shared_with: i.shared_with ?? [],
      options: i.options ?? [],
    })),
    scheduled_for: o.scheduled_for,
    sent_to_kitchen_at: o.sent_to_kitchen_at,
    preparation_started_at: o.preparation_started_at,
    en_cours: o.status === "in_preparation",
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
  // Doit être appelé avant useCurrentStaff — voir lib/demoLien.ts.
  useAccesDemoParLien();
  const router = useRouter();
  const { staff, loading: staffLoading } = useCurrentStaff(["kitchen", "manager"]);
  const [orders, setOrders] = useState<KitchenOrder[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [todayCount, setTodayCount] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [activeTab, setActiveTab] = useState<KitchenTab>("todo");

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
                items: msg.items.map((it: KitchenOrder["items"][number]) => ({
                  ...it,
                  shared_with: it.shared_with ?? [],
                  options: it.options ?? [],
                })),
                scheduled_for: msg.scheduled_for ?? null,
                sent_to_kitchen_at: msg.sent_to_kitchen_at ?? null,
                preparation_started_at: null,
                en_cours: false,
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

  // Les deux étapes étaient enchaînées derrière un seul bouton « Prêt » :
  // « en préparation » n'existait donc que le temps d'un appel réseau, et la
  // cuisine ne pouvait pas dire ce qu'elle avait déjà commencé. Les séparer,
  // c'est ce qui donne les deux onglets — et un vrai temps de préparation.
  async function commencerPreparation(orderId: number) {
    setError(null);
    try {
      await api.startPreparation(orderId);
      setOrders((prev) =>
        prev.map((o) =>
          o.order_id === orderId
            ? { ...o, en_cours: true, preparation_started_at: new Date().toISOString() }
            : o
        )
      );
    } catch (e) {
      // Déjà en préparation (ex: clic parti au moment d'une coupure, ou deux
      // écrans cuisine) : l'état visé est atteint, ce n'est pas une erreur.
      if (e instanceof ApiError && e.code === "INVALID_TRANSITION") {
        setOrders((prev) => prev.map((o) => (o.order_id === orderId ? { ...o, en_cours: true } : o)));
        return;
      }
      setError(toFrenchMessage(e));
    }
  }

  async function markDone(orderId: number) {
    setError(null);
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
                `<li>${it.quantity}× ${escapeHtml(it.name)}${it.is_shared ? " (à partager)" : ""}${
                  it.options.length
                    ? " — " + escapeHtml(it.options.map((o) => o.option_name).join(", "))
                    : ""
                }${it.notes ? " — " + escapeHtml(it.notes) : ""}</li>`
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
      <div className="p-6 bg-[var(--espresso)] min-h-screen">
        <Skeleton dark className="h-8 w-48" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
          <Skeleton dark className="h-40 w-full" />
          <Skeleton dark className="h-40 w-full" />
          <Skeleton dark className="h-40 w-full" />
        </div>
      </div>
    );
  }

  const todoOrders = orders.filter((o) => !o.en_cours);
  const inProgressOrders = orders.filter((o) => o.en_cours);
  const scheduledCount = orders.filter((o) => o.scheduled_for).length;
  const clock = new Date(now).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });

  const TABS: { key: KitchenTab; label: string; count: number }[] = [
    { key: "todo", label: "À préparer", count: todoOrders.length },
    { key: "in_progress", label: "En cours", count: inProgressOrders.length },
    { key: "done", label: "Terminées", count: todayCount ?? 0 },
  ];

  const visibleOrders = activeTab === "todo" ? todoOrders : activeTab === "in_progress" ? inProgressOrders : [];

  return (
    // L'écran cuisine tourne parfois sur un simple téléphone posé sur une
    // étagère, pas sur le grand écran pour lequel il a été dessiné : sans
    // `overflow-x-hidden` et sans passage à la ligne des actions, la page
    // débordait latéralement à 360 px et le bouton de déconnexion sortait du
    // cadre sombre (vérifié en navigateur, Phase 15). Rien sous 13px, noms de
    // plats à 19px : lisible depuis le passe, à trois mètres.
    <div className="min-h-screen bg-[var(--espresso)] overflow-x-hidden">
      <header className="px-[18px] sm:px-[26px] pt-[18px] pb-[18px] border-b border-[var(--line-on-espresso)] flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-baseline gap-3 flex-wrap">
          <TawlaMark size={30} variant="reserveSombre" />
          <h1 className={`${lalezar.className} text-[30px] leading-none text-[var(--semoule)]`}>Cuisine</h1>
          {restaurant && (
            <span className="text-[15px] font-semibold text-[var(--ink-on-espresso-strong)]">
              {restaurant.name} — service du soir
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <ConnectionBadge status={status} dark />
          <span className="text-[22px] font-semibold tabular-nums text-[var(--semoule)]">{clock}</span>
          <Button variant="secondary" dark size="sm" onClick={printTickets}>
            Imprimer (filet de secours)
          </Button>
          <button onClick={logout} className="text-sm text-[var(--ink-on-espresso)] underline">
            Se déconnecter
          </button>
        </div>
      </header>

      <p className="px-[18px] sm:px-[26px] pt-3 text-[13px] text-[var(--ink-on-espresso)]">
        {todayCount === null
          ? "…"
          : `${todayCount} commande${todayCount > 1 ? "s" : ""} traitée${todayCount > 1 ? "s" : ""} aujourd'hui`}
      </p>

      <div className="px-[18px] sm:px-[26px]">
        {error && (
          <Card tone="danger" dark padding="sm" className="mt-3 text-sm text-[var(--harissa-on-espresso-text)]">
            {error}
          </Card>
        )}

        {scheduledCount > 0 && (
          <Card
            tone="info"
            dark
            padding="sm"
            className="mt-3 text-sm text-[var(--laiton-on-espresso-text)] flex items-center gap-1.5"
          >
            <MoonIcon className="w-4 h-4 shrink-0" />
            {scheduledCount} pré-commande{scheduledCount > 1 ? "s" : ""} iftar à anticiper.
          </Card>
        )}
      </div>

      <nav className="flex gap-[14px] px-[18px] sm:px-[26px] pt-4 pb-1.5 flex-wrap" data-visite="cuisine-files">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={
              activeTab === tab.key
                ? "bg-[var(--harissa)] text-[var(--semoule)] text-[15px] font-bold rounded-full px-[18px] py-[9px]"
                : "bg-[var(--line-on-espresso)] border border-[var(--line-on-espresso-strong)] text-[rgba(246,239,221,.82)] text-[15px] font-semibold rounded-full px-[18px] py-[9px]"
            }
          >
            {tab.label} · {tab.count}
          </button>
        ))}
      </nav>

      <div className="grid grid-cols-2 lg:grid-cols-3 min-[1440px]:grid-cols-4 gap-4 p-[18px] sm:p-[26px] pt-2">
        {activeTab === "done" ? (
          <div className="col-span-full">
            <EmptyState
              message={
                todayCount
                  ? `${todayCount} commande${todayCount > 1 ? "s" : ""} servie${todayCount > 1 ? "s" : ""} aujourd'hui.`
                  : "Rien de terminé pour l'instant."
              }
              dark
            />
          </div>
        ) : (
          <>
            {visibleOrders.map((o) => {
              // Chaque colonne compte à partir de son propre repère : le temps
              // d'attente avant qu'on s'en saisisse, puis le temps de
              // préparation. Les additionner masquerait lequel dérape.
              const depuis = o.en_cours ? o.preparation_started_at : o.sent_to_kitchen_at;
              const secondes = elapsedSeconds(depuis, now);
              const late = secondes !== null && secondes >= ELAPSED_ALERT_MINUTES * 60;
              const borderColor = late
                ? "var(--harissa)"
                : o.en_cours
                  ? "rgba(31,107,79,.55)"
                  : "var(--line-on-espresso-strong)";
              const headerBg = late ? "var(--harissa)" : o.en_cours ? "rgba(31,107,79,.22)" : "var(--line-on-espresso)";
              return (
                <div
                  key={o.order_id}
                  className="rounded-[14px] overflow-hidden flex flex-col bg-[var(--espresso-card)]"
                  style={{ border: `1px solid ${borderColor}` }}
                >
                  <div
                    className="px-[14px] py-3 flex justify-between items-center"
                    style={{ backgroundColor: headerBg }}
                  >
                    <span className={`${lalezar.className} text-[26px] leading-none text-[var(--semoule)]`}>
                      {o.table_label}
                    </span>
                    {secondes !== null && (
                      <span className="text-[16px] font-bold tabular-nums text-[var(--semoule)]">
                        {duree(secondes)}
                      </span>
                    )}
                  </div>
                  <div className="px-[14px] py-3 flex-1 flex flex-col">
                    <div className="text-xs font-semibold uppercase tracking-[0.12em] text-[rgba(246,239,221,.45)]">
                      #{o.order_id}
                      {o.sent_to_kitchen_at && ` · ${formatTime(o.sent_to_kitchen_at)}`}
                    </div>
                    {o.scheduled_for && (
                      <div className="text-xs text-[var(--laiton-on-espresso-text)] mt-1.5 flex items-center gap-1">
                        <MoonIcon className="w-3.5 h-3.5 shrink-0" />
                        Iftar {formatTime(o.scheduled_for)}
                      </div>
                    )}
                    <ul className="mt-1 flex-1">
                      {o.items.map((it, i) => (
                        <li
                          key={i}
                          className="py-[6px] border-b border-[rgba(246,239,221,.09)] last:border-b-0 flex items-baseline gap-2"
                        >
                          <span className="text-[20px] font-bold tabular-nums text-[var(--harissa)] min-w-[26px] shrink-0">
                            {it.quantity}×
                          </span>
                          <span className="min-w-0">
                            <span className="text-[19px] font-semibold leading-[1.25] text-[var(--semoule)]">
                              {it.name}
                            </span>
                            {it.is_shared && (
                              <span className="ms-1.5 inline-flex items-center gap-1 align-middle rounded-full border border-[rgba(184,134,46,.7)] text-[#d8ae62] text-[13px] font-semibold px-[11px] py-[5px]">
                                <UtensilsIcon className="w-3 h-3 shrink-0" />
                                {it.shared_with.length > 0 ? `À partager · ${it.shared_with.length} couverts` : "À partager"}
                              </span>
                            )}
                            {it.options.length > 0 && (
                              <span className="block text-[15px] font-semibold text-[var(--note-cuisine)]">
                                {it.options.map((o) => o.option_name).join(" · ")}
                              </span>
                            )}
                            {it.notes && (
                              <span className="block text-[15px] font-semibold text-[var(--note-cuisine)]">
                                {it.notes}
                              </span>
                            )}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  {o.en_cours ? (
                    <button
                      onClick={() => markDone(o.order_id)}
                      className="w-full py-[15px] text-[17px] font-bold bg-[var(--menthe)] text-[var(--semoule)]"
                    >
                      Marquer prête
                    </button>
                  ) : (
                    <button
                      onClick={() => commencerPreparation(o.order_id)}
                      className="w-full py-[15px] text-[17px] font-bold bg-[var(--harissa)] text-[var(--semoule)]"
                    >
                      Commencer
                    </button>
                  )}
                </div>
              );
            })}
            {visibleOrders.length === 0 && (
              <div className="col-span-full">
                <EmptyState message={activeTab === "in_progress" ? "Rien en cuisson." : "Rien en attente."} dark />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
