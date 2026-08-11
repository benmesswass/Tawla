"use client";

import { useCallback, useEffect, useState } from "react";
import { Cairo } from "next/font/google";
import { api, wsUrl, ApiError, LoyaltyMember, MenuItem, Order, OrderStatus, Restaurant, Table } from "@/lib/api";
import { toLocalizedMessage } from "@/lib/errors";
import { useReconnectingSocket } from "@/lib/useReconnectingSocket";
import { useLocale } from "@/lib/i18n/useLocale";
import { menuCategoryLabel } from "@/lib/menuCategories";
import SplitBill from "@/components/SplitBill";
import { MoonIcon, UtensilsIcon, GiftIcon, CakeIcon, BellIcon, FlameIcon, WifiOffIcon, ShareIcon } from "@/components/icons";
import Skeleton from "@/components/ui/Skeleton";
import CelebrationOverlay from "@/components/CelebrationOverlay";
import EmptyCartIllustration from "@/components/illustrations/EmptyCartIllustration";
import LoyaltyStampCard from "@/components/LoyaltyStampCard";
import { CULTURAL_FACTS } from "@/lib/culturalFacts";
import { generateShareCardBlob } from "@/lib/shareCard";

const cairo = Cairo({ subsets: ["arabic", "latin"], weight: ["400", "600", "700"] });

type CartLine = { item: MenuItem; quantity: number; note: string; shared: boolean };

type StepStatus = Exclude<OrderStatus, "cancelled">;

const STEP_STATUSES: StepStatus[] = [
  "pending_confirmation",
  "confirmed",
  "sent_to_kitchen",
  "in_preparation",
  "ready",
  "served",
];

function lastOrderStorageKey(qrToken: string): string {
  return `resto-qr-menu:last-order:${qrToken}`;
}

function offlineQueueStorageKey(qrToken: string): string {
  return `resto-qr-menu:offline-queue:${qrToken}`;
}

function loyaltyPhoneStorageKey(restaurantId: number): string {
  return `resto-qr-menu:loyalty-phone:${restaurantId}`;
}

// Web Push exige la clé VAPID en Uint8Array, pas en base64url brut —
// conversion standard, aucune lib externe nécessaire pour ça.
function urlBase64ToUint8Array(base64url: string): Uint8Array {
  const padding = "=".repeat((4 - (base64url.length % 4)) % 4);
  const base64 = (base64url + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

type CreateOrderPayload = Parameters<typeof api.createOrder>[0];

export default function MenuPage({ params }: { params: { qrToken: string } }) {
  const { qrToken } = params;
  const { t, locale, toggleLocale } = useLocale();

  const [table, setTable] = useState<Table | null>(null);
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [cart, setCart] = useState<Record<number, CartLine>>({});
  const [loadError, setLoadError] = useState<string | null>(null);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [trackedOrder, setTrackedOrder] = useState<Order | null>(null);
  const [tipInput, setTipInput] = useState("");
  const [paying, setPaying] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [preOrderForIftar, setPreOrderForIftar] = useState(false);
  const [waiterCallState, setWaiterCallState] = useState<"idle" | "calling" | "called">("idle");
  const [waiterCallError, setWaiterCallError] = useState<string | null>(null);
  const [offlineQueuedPayload, setOfflineQueuedPayload] = useState<CreateOrderPayload | null>(null);
  const [retryingOffline, setRetryingOffline] = useState(false);
  const [loyaltySectionOpen, setLoyaltySectionOpen] = useState(false);
  const [loyaltyPhone, setLoyaltyPhone] = useState("");
  const [loyaltyBirthDate, setLoyaltyBirthDate] = useState("");
  const [loyaltyStatus, setLoyaltyStatus] = useState<LoyaltyMember | null>(null);
  const [pushState, setPushState] = useState<
    "idle" | "subscribing" | "subscribed" | "unsupported" | "denied" | "error"
  >("idle");
  const [showCelebration, setShowCelebration] = useState(false);
  const [bumpedItemId, setBumpedItemId] = useState<number | null>(null);
  const [cartClearedNotice, setCartClearedNotice] = useState(false);
  const [culturalFactIndex, setCulturalFactIndex] = useState(0);
  const [sharingOrder, setSharingOrder] = useState(false);

  function formatTime(iso: string): string {
    return new Date(iso).toLocaleTimeString(locale === "ar" ? "ar-TN" : "fr-FR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  // Nombre de tampons remplis pour la carte de fidélité visuelle : le cycle
  // repart de 0 après chaque récompense (order_count % 10), sauf pile au
  // moment où la récompense vient d'être débloquée (multiple de 10 exact) —
  // là, la carte doit apparaître pleine, pas vide.
  function loyaltyStampsFilled(status: LoyaltyMember): number {
    if (status.reward_available) return 10;
    return status.order_count % 10;
  }

  const load = useCallback(() => {
    setLoadError(null);
    setTable(null);
    api
      .getTableByToken(qrToken)
      .then(async (t) => {
        setTable(t);
        const [rest, items] = await Promise.all([api.getRestaurant(t.restaurant_id), api.getMenu(t.restaurant_id)]);
        setRestaurant(rest);
        setMenu(items);

        // Si le client a déjà une commande en cours pour cette table (ex:
        // téléphone rafraîchi pendant que le plat était en préparation), on
        // reprend le suivi au lieu de lui montrer à nouveau tout le menu.
        const savedId = sessionStorage.getItem(lastOrderStorageKey(qrToken));
        if (savedId) {
          try {
            const order = await api.getOrder(Number(savedId));
            if (order.status !== "served" && order.status !== "cancelled") {
              setTrackedOrder(order);
            } else {
              sessionStorage.removeItem(lastOrderStorageKey(qrToken));
            }
          } catch {
            sessionStorage.removeItem(lastOrderStorageKey(qrToken));
          }
        }
      })
      .catch((e) => setLoadError(toLocalizedMessage(e, locale)));
  }, [qrToken, locale]);

  useEffect(() => {
    load();
  }, [load]);

  // PWA offline-first : une commande mise de côté faute de réseau (voir
  // validateOrder) est stockée sur l'appareil du client, pas en mémoire —
  // elle doit survivre à une page fermée puis rouverte.
  const flushOfflineQueue = useCallback(async () => {
    const raw = localStorage.getItem(offlineQueueStorageKey(qrToken));
    if (!raw) return;
    setRetryingOffline(true);
    try {
      const payload: CreateOrderPayload = JSON.parse(raw);
      const order = await api.createOrder(payload);
      localStorage.removeItem(offlineQueueStorageKey(qrToken));
      sessionStorage.setItem(lastOrderStorageKey(qrToken), String(order.id));
      setOfflineQueuedPayload(null);
      setTrackedOrder(order);
    } catch {
      // Toujours hors ligne (ou erreur transitoire) : on retentera au
      // prochain événement "online" ou clic manuel — pas d'erreur affichée
      // à chaque tentative silencieuse, ça n'apporterait rien au client.
    } finally {
      setRetryingOffline(false);
    }
  }, [qrToken]);

  useEffect(() => {
    const raw = localStorage.getItem(offlineQueueStorageKey(qrToken));
    if (!raw) return;
    try {
      setOfflineQueuedPayload(JSON.parse(raw));
    } catch {
      localStorage.removeItem(offlineQueueStorageKey(qrToken));
      return;
    }
    flushOfflineQueue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qrToken]);

  useEffect(() => {
    window.addEventListener("online", flushOfflineQueue);
    return () => window.removeEventListener("online", flushOfflineQueue);
  }, [flushOfflineQueue]);

  useEffect(() => {
    if (!showCelebration) return;
    const timer = setTimeout(() => setShowCelebration(false), 1800);
    return () => clearTimeout(timer);
  }, [showCelebration]);

  // Anecdote culturelle qui tourne pendant l'attente cuisine (10-20 min en
  // moyenne) — un petit plus pendant l'attente plutôt qu'un écran silencieux.
  const inKitchenWait =
    trackedOrder?.status === "sent_to_kitchen" || trackedOrder?.status === "in_preparation";
  useEffect(() => {
    if (!inKitchenWait) return;
    const timer = setInterval(() => {
      setCulturalFactIndex((i) => (i + 1) % CULTURAL_FACTS[locale === "ar" ? "ar" : "fr"].length);
    }, 8000);
    return () => clearInterval(timer);
  }, [inKitchenWait, locale]);

  // Carte de fidélité — pré-remplit le numéro déjà utilisé sur ce resto
  // (évite de le retaper à chaque visite), sans jamais le rendre obligatoire.
  useEffect(() => {
    if (!restaurant) return;
    const saved = localStorage.getItem(loyaltyPhoneStorageKey(restaurant.id));
    if (saved) setLoyaltyPhone(saved);
  }, [restaurant]);

  async function checkLoyaltyStatus(phone: string) {
    if (!restaurant || !phone.trim()) {
      setLoyaltyStatus(null);
      return;
    }
    try {
      const status = await api.lookupLoyalty(restaurant.id, phone.trim(), loyaltyBirthDate || null);
      setLoyaltyStatus(status);
      localStorage.setItem(loyaltyPhoneStorageKey(restaurant.id), phone.trim());
    } catch {
      // Vérification de statut best-effort — une erreur ici ne doit jamais
      // bloquer la commande, qui reste possible sans numéro fidélité.
    }
  }

  // Opt-in explicite pour être notifié quand la commande passe "prête" —
  // touche le client même s'il a quitté l'onglet, contrairement au suivi
  // WebSocket seul (voir public/sw.js pour la réception côté navigateur).
  async function subscribeToPush() {
    if (!trackedOrder) return;
    if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
      setPushState("unsupported");
      return;
    }

    setPushState("subscribing");
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setPushState(permission === "denied" ? "denied" : "idle");
        return;
      }

      const { public_key } = await api.getVapidPublicKey();
      if (!public_key) {
        setPushState("unsupported");
        return;
      }

      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(public_key),
      });
      await api.savePushSubscription(trackedOrder.id, subscription.toJSON() as PushSubscriptionJSON);
      setPushState("subscribed");
    } catch {
      setPushState("error");
    }
  }

  // Suivi temps réel de la commande après validation — jusqu'ici le client
  // n'avait plus aucune nouvelle après "commande envoyée" (audit PO 2026-08-10).
  const orderWsUrl =
    trackedOrder && restaurant ? wsUrl(`/ws/order/${restaurant.id}/${trackedOrder.id}`) : null;
  useReconnectingSocket(orderWsUrl, (msg) => {
    if (msg.event === "order.status_changed" && trackedOrder && msg.order_id === trackedOrder.id) {
      setTrackedOrder((prev) => (prev ? { ...prev, status: msg.status } : prev));
      if (msg.status === "served" || msg.status === "cancelled") {
        sessionStorage.removeItem(lastOrderStorageKey(qrToken));
      }
    }
    // Le serveur vient d'encaisser un paiement en espèces demandé depuis
    // cette même page — inutile de faire deviner au client s'il doit
    // rafraîchir pour le voir.
    if (msg.event === "order.payment_confirmed" && trackedOrder && msg.order_id === trackedOrder.id) {
      setTrackedOrder((prev) => (prev ? { ...prev, payment_status: "paid" } : prev));
    }
    // Dès qu'un serveur est affecté (prise en charge ou confirmation), le
    // client sait qui s'occupe de sa table sans avoir à demander.
    if (msg.event === "order.staff_assigned" && trackedOrder && msg.order_id === trackedOrder.id) {
      setTrackedOrder((prev) => (prev ? { ...prev, taken_by_staff_name: msg.staff_name } : prev));
    }
  });

  // Rupture de stock en temps réel : un plat qui devient indisponible doit
  // disparaître du menu immédiatement, sans attendre que le client tente de
  // commander pour le découvrir (ex: ITEM_UNAVAILABLE au moment de valider).
  const menuWsUrl = restaurant ? wsUrl(`/ws/menu/${restaurant.id}`) : null;
  useReconnectingSocket(menuWsUrl, (msg) => {
    if (msg.event === "menu_item.availability_changed") {
      setMenu((prev) =>
        prev.map((m) => (m.id === msg.menu_item_id ? { ...m, is_available: msg.is_available } : m))
      );
      if (!msg.is_available) {
        setCart((prev) => {
          if (!prev[msg.menu_item_id]) return prev;
          const next = { ...prev };
          delete next[msg.menu_item_id];
          if (Object.keys(next).length === 0) {
            setCartClearedNotice(true);
          }
          return next;
        });
      }
    }
  });

  // Le compteur de fidélité n'avance qu'au paiement confirmé côté serveur —
  // on rafraîchit l'affichage client à ce moment précis (carte immédiate,
  // cash via le WebSocket ci-dessus) plutôt que de deviner la nouvelle valeur.
  useEffect(() => {
    if (trackedOrder?.payment_status === "paid" && trackedOrder.loyalty_phone) {
      checkLoyaltyStatus(trackedOrder.loyalty_phone);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trackedOrder?.payment_status]);

  async function payByCard() {
    if (!trackedOrder) return;
    setPaying(true);
    setPaymentError(null);
    const tip = Number(tipInput.replace(",", ".")) || 0;
    try {
      const updated = await api.payByCard(trackedOrder.id, tip);
      setTrackedOrder(updated);
    } catch (e) {
      setPaymentError(toLocalizedMessage(e, locale));
    } finally {
      setPaying(false);
    }
  }

  async function payByCash() {
    if (!trackedOrder) return;
    setPaying(true);
    setPaymentError(null);
    try {
      const updated = await api.requestCashPayment(trackedOrder.id);
      setTrackedOrder(updated);
    } catch (e) {
      setPaymentError(toLocalizedMessage(e, locale));
    } finally {
      setPaying(false);
    }
  }

  async function callWaiter() {
    if (!table || waiterCallState !== "idle") return;
    setWaiterCallState("calling");
    setWaiterCallError(null);
    try {
      await api.callWaiter(table.restaurant_id, table.id);
      setWaiterCallState("called");
      // Cooldown le temps qu'un serveur arrive réellement à table — évite le
      // spam de clics sans avoir besoin d'un canal temps réel côté client.
      setTimeout(() => setWaiterCallState("idle"), 90_000);
    } catch (e) {
      setWaiterCallError(toLocalizedMessage(e, locale));
      setWaiterCallState("idle");
    }
  }

  function addToCart(item: MenuItem) {
    setCart((prev) => {
      const existing = prev[item.id];
      return {
        ...prev,
        [item.id]: {
          item,
          quantity: (existing?.quantity ?? 0) + 1,
          note: existing?.note ?? "",
          shared: existing?.shared ?? false,
        },
      };
    });
    setCartClearedNotice(false);
    setBumpedItemId(item.id);
    setTimeout(() => setBumpedItemId((cur) => (cur === item.id ? null : cur)), 300);
  }

  function removeFromCart(itemId: number) {
    setCart((prev) => {
      const next = { ...prev };
      if (next[itemId] && next[itemId].quantity > 1) {
        next[itemId] = { ...next[itemId], quantity: next[itemId].quantity - 1 };
      } else {
        delete next[itemId];
      }
      return next;
    });
  }

  function setNote(itemId: number, note: string) {
    setCart((prev) => (prev[itemId] ? { ...prev, [itemId]: { ...prev[itemId], note } } : prev));
  }

  function setShared(itemId: number, shared: boolean) {
    setCart((prev) => (prev[itemId] ? { ...prev, [itemId]: { ...prev[itemId], shared } } : prev));
  }

  const cartLines = Object.values(cart);
  const total = cartLines.reduce((sum, l) => sum + l.item.price * l.quantity, 0);

  async function validateOrder() {
    if (!table || cartLines.length === 0) return;
    setSending(true);
    setOrderError(null);
    const payload: CreateOrderPayload = {
      restaurant_id: table.restaurant_id,
      table_id: table.id,
      items: cartLines.map((l) => ({
        menu_item_id: l.item.id,
        quantity: l.quantity,
        notes: l.note || null,
        is_shared: l.shared,
      })),
      scheduled_for: preOrderForIftar && restaurant?.iftar_time ? restaurant.iftar_time : null,
      loyalty_phone: loyaltyPhone.trim() || null,
    };
    try {
      const order = await api.createOrder(payload);
      sessionStorage.setItem(lastOrderStorageKey(qrToken), String(order.id));
      setTrackedOrder(order);
      setCart({});
      setPreOrderForIftar(false);
      setShowCelebration(true);
    } catch (e) {
      // Échec réseau (pas une réponse de l'API, ex: connexion mobile coupée
      // en pleine validation) : on garde la commande de côté sur le téléphone
      // du client plutôt que de la perdre — envoi automatique dès que le
      // réseau revient (voir flushOfflineQueue).
      if (e instanceof TypeError) {
        localStorage.setItem(offlineQueueStorageKey(qrToken), JSON.stringify(payload));
        setOfflineQueuedPayload(payload);
        setCart({});
        setPreOrderForIftar(false);
        setSending(false);
        return;
      }
      // Un article devenu indisponible pendant que le client avait le panier
      // ouvert ne doit plus faire disparaître tout l'écran (bug critique
      // corrigé suite à l'audit) : on retire juste cet article et le client
      // peut valider le reste.
      if (e instanceof ApiError && (e.code === "ITEM_UNAVAILABLE" || e.code === "ITEM_NOT_FOUND")) {
        const staleId = e.context.menu_item_id as number | undefined;
        if (staleId) {
          setCart((prev) => {
            const next = { ...prev };
            delete next[staleId];
            return next;
          });
        }
        api.getMenu(table.restaurant_id).then(setMenu).catch(() => {});
      }
      setOrderError(toLocalizedMessage(e, locale));
    } finally {
      setSending(false);
    }
  }

  function orderAgain() {
    setTrackedOrder(null);
    sessionStorage.removeItem(lastOrderStorageKey(qrToken));
  }

  // Carte de partage social (Instagram/WhatsApp Status) — générée
  // entièrement côté client sur <canvas>, sans backend ni service tiers.
  // Web Share API quand elle supporte les fichiers, sinon téléchargement.
  async function shareOrder() {
    if (!trackedOrder || !restaurant) return;
    setSharingOrder(true);
    try {
      const blob = await generateShareCardBlob({
        restaurantName: restaurant.name,
        items: trackedOrder.items.map((it) => ({ name: it.menu_item_name, quantity: it.quantity })),
        locale: locale === "ar" ? "ar" : "fr",
      });
      if (!blob) return;
      const file = new File([blob], "ma-commande-tawla.png", { type: "image/png" });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        try {
          await navigator.share({ files: [file], title: t.shareCardTitle(restaurant.name), text: t.shareCardText });
          return;
        } catch {
          // Partage annulé par le client ou API refusée — on retombe sur le
          // téléchargement direct plutôt que de laisser un écran bloqué.
        }
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "ma-commande-tawla.png";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setSharingOrder(false);
    }
  }

  const dir = t.dir;
  const wrapperClassName = locale === "ar" ? cairo.className : undefined;

  if (loadError) {
    return (
      <div dir={dir} className={`p-6 max-w-md mx-auto text-center ${wrapperClassName ?? ""}`}>
        <p className="text-red-600 mb-4">{loadError}</p>
        <button onClick={load} className="bg-neutral-900 text-white px-4 py-2 rounded-lg">
          {t.retry}
        </button>
      </div>
    );
  }
  if (!table || !restaurant) {
    return (
      <div dir={dir} className={`${wrapperClassName ?? ""}`}>
        <span className="sr-only">{t.loadingMenu}</span>
        <Skeleton className="h-24 w-full" />
        <div className="p-4 max-w-md mx-auto space-y-4">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      </div>
    );
  }

  if (offlineQueuedPayload) {
    return (
      <div dir={dir} className={`p-6 max-w-md mx-auto text-center ${wrapperClassName ?? ""}`}>
        <h1 className="text-xl font-semibold flex items-center justify-center gap-2">
          <WifiOffIcon className="w-5 h-5 shrink-0" />
          {t.offlineQueuedTitle}
        </h1>
        <p className="mt-4 text-neutral-600">{t.offlineQueuedMessage}</p>
        <button
          onClick={flushOfflineQueue}
          disabled={retryingOffline}
          className="mt-8 w-full bg-neutral-900 text-white rounded-lg py-2.5 disabled:opacity-50"
        >
          {retryingOffline ? t.sending : t.retryNow}
        </button>
      </div>
    );
  }

  if (trackedOrder) {
    const currentStepIndex = STEP_STATUSES.indexOf(trackedOrder.status as StepStatus);
    const cancelled = trackedOrder.status === "cancelled";
    return (
      <>
        {showCelebration && <CelebrationOverlay />}
        <div dir={dir} className={`p-6 max-w-md mx-auto ${wrapperClassName ?? ""}`}>
        <h1 className="text-xl font-semibold text-center">
          {cancelled ? t.orderCancelledTitle : t.orderSentTitle}
        </h1>
        <p className="mt-2 text-neutral-600 text-center">{t.orderSubtitle(table.label, trackedOrder.id)}</p>

        <div className="mt-4 text-center">
          <button
            onClick={callWaiter}
            disabled={waiterCallState !== "idle"}
            className="text-sm border border-neutral-300 rounded-lg px-3 py-1.5 disabled:opacity-70"
          >
            {waiterCallState === "called" ? (
              t.callWaiterSent
            ) : (
              <span className="inline-flex items-center gap-1.5">
                <BellIcon className="w-4 h-4 shrink-0" />
                {t.callWaiterButton}
              </span>
            )}
          </button>
          {waiterCallError && <p className="mt-2 text-sm text-red-600">{waiterCallError}</p>}
        </div>

        {!cancelled && trackedOrder.scheduled_for && (
          <p className="mt-4 text-sm text-center bg-indigo-50 text-indigo-800 border border-indigo-200 rounded-lg py-2 px-3 flex items-center justify-center gap-1.5">
            <MoonIcon className="w-4 h-4 shrink-0" />
            {t.preorderBadge(formatTime(trackedOrder.scheduled_for))}
          </p>
        )}

        {!cancelled && trackedOrder.taken_by_staff_name && (
          <p className="mt-4 text-sm text-center bg-amber-50 text-amber-800 border border-amber-200 rounded-lg py-2 px-3">
            {t.dedicatedServer(trackedOrder.taken_by_staff_name)}
          </p>
        )}

        {!cancelled &&
          trackedOrder.status !== "ready" &&
          trackedOrder.status !== "served" &&
          pushState !== "unsupported" && (
            <div className="mt-4 text-center">
              {pushState === "subscribed" ? (
                <p className="text-sm text-emerald-700 flex items-center justify-center gap-1.5">
                  <BellIcon className="w-4 h-4 shrink-0" />
                  {t.pushSubscribed}
                </p>
              ) : pushState === "denied" ? (
                <p className="text-sm text-neutral-500">{t.pushDenied}</p>
              ) : (
                <button
                  onClick={subscribeToPush}
                  disabled={pushState === "subscribing"}
                  className="text-sm border border-neutral-300 rounded-lg px-3 py-1.5 disabled:opacity-70"
                >
                  {pushState === "subscribing" ? (
                    t.sending
                  ) : (
                    <span className="inline-flex items-center gap-1.5">
                      <BellIcon className="w-4 h-4 shrink-0" />
                      {t.pushSubscribeButton}
                    </span>
                  )}
                </button>
              )}
            </div>
          )}

        {!cancelled && trackedOrder.loyalty_phone && loyaltyStatus && (
          <div className="mt-4 text-sm text-center bg-orange-50 text-orange-900 border border-orange-200 rounded-lg py-3 px-3">
            <LoyaltyStampCard
              filled={loyaltyStampsFilled(loyaltyStatus)}
              rewardAvailable={loyaltyStatus.reward_available}
            />
            {loyaltyStatus.reward_available ? (
              <p className="font-medium mt-2">{t.loyaltyRewardAvailable}</p>
            ) : (
              <p className="flex items-center justify-center gap-1.5 mt-2">
                <GiftIcon className="w-4 h-4 shrink-0" />
                {t.loyaltyProgress(loyaltyStatus.order_count, loyaltyStatus.orders_until_reward)}
              </p>
            )}
            {loyaltyStatus.is_birthday_today && (
              <p className="mt-1 flex items-center justify-center gap-1.5">
                <CakeIcon className="w-4 h-4 shrink-0" />
                {t.loyaltyBirthdayBanner}
              </p>
            )}
          </div>
        )}

        {!cancelled && (
          <ol className="mt-8">
            {STEP_STATUSES.map((status, i) => {
              const done = i < currentStepIndex;
              const current = i === currentStepIndex;
              const isLast = i === STEP_STATUSES.length - 1;
              const showWaitHint = current && (status === "sent_to_kitchen" || status === "in_preparation");
              return (
                <li key={status} className="relative ps-10 pb-6 last:pb-0">
                  {!isLast && (
                    <span
                      className="absolute top-7 bottom-0 w-0.5 start-[15px]"
                      style={{ backgroundColor: done ? "var(--menthe)" : "var(--line)" }}
                    />
                  )}
                  <span
                    className={`absolute top-0 start-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold ${
                      current ? "animate-pulse-ring" : ""
                    }`}
                    style={{
                      backgroundColor: done || current ? "var(--menthe)" : "var(--semoule-raised)",
                      color: done || current ? "white" : "var(--ink-soft)",
                      border: done || current ? "none" : "1px solid var(--line)",
                    }}
                  >
                    {done ? "✓" : i + 1}
                  </span>
                  <div className="pt-1">
                    <span
                      className={current || done ? "font-semibold" : "text-neutral-400"}
                      style={{ color: current ? "var(--encre)" : done ? "var(--menthe)" : undefined }}
                    >
                      {t.steps[status]}
                    </span>
                    {showWaitHint && (
                      <p className="text-xs mt-0.5" style={{ color: "var(--ink-soft)" }}>
                        {t.kitchenWaitHint}
                      </p>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        )}

        {!cancelled && inKitchenWait && (
          <div
            className="mt-4 text-sm rounded-lg py-2.5 px-3 flex items-start gap-2"
            style={{ backgroundColor: "var(--semoule)", border: "1px solid var(--line)", color: "var(--encre)" }}
          >
            <FlameIcon className="w-4 h-4 shrink-0 mt-0.5 text-[var(--laiton)]" />
            <span>{CULTURAL_FACTS[locale === "ar" ? "ar" : "fr"][culturalFactIndex]}</span>
          </div>
        )}

        <div className="mt-8 border-t pt-4">
          <p className="text-sm font-medium mb-2">{t.orderDetailsTitle}</p>
          <ul className="text-sm text-neutral-600 space-y-1">
            {trackedOrder.items.map((it) => (
              <li key={it.id}>
                {it.quantity}× {it.menu_item_name}
                {it.is_shared && (
                  <span className="text-amber-700 inline-flex items-center gap-1 align-middle">
                    · <UtensilsIcon className="w-3.5 h-3.5 shrink-0" /> {t.sharedTag}
                  </span>
                )}
                {it.notes && <span className="text-neutral-400"> — {it.notes}</span>}
              </li>
            ))}
          </ul>
          <div className="flex justify-between font-medium mt-2 pt-2 border-t">
            <span>{t.total}</span>
            <span>
              {trackedOrder.total_amount.toFixed(2)} {t.currency}
            </span>
          </div>
        </div>

        {!cancelled && (
          <div className="mt-6 border-t pt-4">
            <p className="text-sm font-medium mb-3">{t.paymentTitle}</p>

            {trackedOrder.payment_status === "paid" && (
              <p className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                {t.paidMessage(trackedOrder.payment_method === "card" ? "card" : "cash", trackedOrder.tip_amount)}
              </p>
            )}

            {trackedOrder.payment_status === "pending" && (
              <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
                {t.cashPendingMessage(trackedOrder.total_amount)}
              </p>
            )}

            {trackedOrder.payment_status === "unpaid" && (
              <div className="space-y-3">
                {paymentError && (
                  <div className="text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">
                    {paymentError}
                  </div>
                )}
                <SplitBill order={trackedOrder} t={t} />
                <div>
                  <label htmlFor="tip" className="text-sm text-neutral-500">
                    {t.tipLabel}
                  </label>
                  <input
                    id="tip"
                    type="text"
                    inputMode="decimal"
                    value={tipInput}
                    onChange={(e) => setTipInput(e.target.value)}
                    placeholder={t.tipPlaceholder}
                    className="mt-1 w-full text-sm border rounded-lg px-3 py-1.5"
                  />
                </div>
                <button
                  onClick={payByCard}
                  disabled={paying}
                  className="w-full bg-neutral-900 text-white rounded-lg py-2.5 disabled:opacity-50"
                >
                  {t.payByCard}
                </button>
                <button
                  onClick={payByCash}
                  disabled={paying}
                  className="w-full border border-neutral-300 rounded-lg py-2.5 disabled:opacity-50"
                >
                  {t.payByCash}
                </button>
              </div>
            )}
          </div>
        )}

        <button
          onClick={shareOrder}
          disabled={sharingOrder}
          className="mt-8 w-full border border-neutral-300 rounded-lg py-2.5 disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
        >
          <ShareIcon className="w-4 h-4 shrink-0" />
          {t.shareOrderButton}
        </button>

        <button onClick={orderAgain} className="mt-3 w-full border border-neutral-300 rounded-lg py-2.5">
          {t.orderAgain}
        </button>
        </div>
      </>
    );
  }

  const availableItems = menu.filter((m) => m.is_available);
  const categories = Array.from(new Set(availableItems.map((m) => m.category)));

  function renderItem(item: MenuItem) {
    return (
      <div key={item.id} className="border-b py-3">
        <div className="flex justify-between items-center">
          <div className="pe-3">
            <div className="font-medium">
              {item.name}
              {item.spice_level > 0 && (
                <span className="ms-1 inline-flex items-center gap-0.5 align-middle text-[var(--harissa)]">
                  {Array.from({ length: item.spice_level }).map((_, i) => (
                    <FlameIcon key={i} className="w-3.5 h-3.5 shrink-0" />
                  ))}
                </span>
              )}
              {!item.is_halal && (
                <span className="ms-1 text-xs font-normal text-red-600 border border-red-200 rounded px-1 align-middle">
                  {t.notHalalBadge}
                </span>
              )}
            </div>
            {item.description && <div className="text-sm text-neutral-500">{item.description}</div>}
            {item.allergens && (
              <div className="text-xs text-neutral-400 mt-0.5">{t.allergensLabel(item.allergens)}</div>
            )}
            <div className="text-sm text-neutral-500 mt-0.5">
              {item.price.toFixed(2)} {t.currency}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {item.image_url && (
              <img
                src={item.image_url}
                alt={item.name}
                className="w-12 h-12 rounded-lg object-cover hidden sm:block"
              />
            )}
            {cart[item.id] && (
              <>
                <button
                  onClick={() => removeFromCart(item.id)}
                  aria-label={t.removeFromCartAria(item.name)}
                  className="w-8 h-8 rounded-full border"
                >
                  -
                </button>
                <span
                  className={`inline-block min-w-[1.5rem] text-center ${
                    bumpedItemId === item.id ? "animate-cart-bump" : ""
                  }`}
                >
                  {cart[item.id].quantity}
                </span>
              </>
            )}
            <button
              onClick={() => addToCart(item)}
              aria-label={t.addToCartAria(item.name)}
              className="w-8 h-8 rounded-full bg-neutral-900 text-white transition-transform active:scale-90"
            >
              +
            </button>
          </div>
        </div>
        {cart[item.id] && (
          <>
            <input
              type="text"
              value={cart[item.id].note}
              onChange={(e) => setNote(item.id, e.target.value)}
              placeholder={t.notePlaceholder}
              className="mt-2 w-full text-sm border rounded-lg px-3 py-1.5"
            />
            <label className="mt-2 flex items-center gap-2 text-sm text-neutral-600">
              <input
                type="checkbox"
                checked={cart[item.id].shared}
                onChange={(e) => setShared(item.id, e.target.checked)}
              />
              <UtensilsIcon className="w-4 h-4 shrink-0" />
              {t.sharedCheckboxLabel}
            </label>
          </>
        )}
      </div>
    );
  }

  return (
    <div dir={dir} className={`pb-32 ${wrapperClassName ?? ""}`}>
      <header className="bg-amber-700 text-white px-4 py-5 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{restaurant.name}</h1>
          <p className="text-amber-100 text-sm">{table.label}</p>
        </div>
        <div className="flex flex-col items-end gap-2 shrink-0">
          <button
            onClick={toggleLocale}
            className="text-sm border border-amber-300 rounded-lg px-3 py-1.5 text-amber-50"
          >
            {t.localeSwitchLabel}
          </button>
          <button
            onClick={callWaiter}
            disabled={waiterCallState !== "idle"}
            className="text-sm border border-amber-300 rounded-lg px-3 py-1.5 text-amber-50 disabled:opacity-70 whitespace-nowrap"
          >
            {waiterCallState === "called" ? (
              t.callWaiterSent
            ) : (
              <span className="inline-flex items-center gap-1.5">
                <BellIcon className="w-4 h-4 shrink-0" />
                {t.callWaiterButton}
              </span>
            )}
          </button>
        </div>
      </header>

      {restaurant.ramadan_mode_enabled && restaurant.iftar_time && (
        <div className="bg-indigo-950 text-indigo-100 px-4 py-3 text-sm flex items-center justify-center gap-1.5">
          <MoonIcon className="w-4 h-4 shrink-0" />
          {t.ramadanBanner(formatTime(restaurant.iftar_time))}
        </div>
      )}

      <div className="p-4 max-w-md mx-auto">
        {waiterCallError && (
          <div className="mb-4 text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">
            {waiterCallError}
          </div>
        )}
        {orderError && (
          <div className="mb-4 text-sm bg-red-50 text-red-700 border border-red-200 rounded-lg p-3 flex justify-between items-start gap-2">
            <span>{orderError}</span>
            <button onClick={() => setOrderError(null)} aria-label={t.closeErrorAria} className="text-red-500">
              ✕
            </button>
          </div>
        )}

        <div className="mb-4 border rounded-lg p-3 bg-orange-50 border-orange-200">
          {!loyaltySectionOpen ? (
            <button
              onClick={() => setLoyaltySectionOpen(true)}
              className="text-sm underline text-orange-800 inline-flex items-center gap-1.5"
            >
              <GiftIcon className="w-4 h-4 shrink-0" />
              {t.loyaltyToggle}
            </button>
          ) : (
            <div className="space-y-2">
              <label className="block text-sm text-orange-900">
                {t.loyaltyPhoneLabel}
                <input
                  type="tel"
                  value={loyaltyPhone}
                  onChange={(e) => setLoyaltyPhone(e.target.value)}
                  onBlur={() => checkLoyaltyStatus(loyaltyPhone)}
                  placeholder={t.loyaltyPhonePlaceholder}
                  className="mt-1 w-full text-sm border rounded-lg px-3 py-1.5"
                />
              </label>
              <label className="block text-sm text-orange-900">
                {t.loyaltyBirthDateLabel}
                <input
                  type="date"
                  value={loyaltyBirthDate}
                  onChange={(e) => setLoyaltyBirthDate(e.target.value)}
                  onBlur={() => checkLoyaltyStatus(loyaltyPhone)}
                  className="mt-1 w-full text-sm border rounded-lg px-3 py-1.5"
                />
              </label>
              {loyaltyStatus && (
                <div className="text-sm text-orange-900 pt-1">
                  <LoyaltyStampCard
                    filled={loyaltyStampsFilled(loyaltyStatus)}
                    rewardAvailable={loyaltyStatus.reward_available}
                  />
                  {loyaltyStatus.reward_available ? (
                    <p className="font-medium mt-2">{t.loyaltyRewardAvailable}</p>
                  ) : (
                    <p className="flex items-center gap-1.5 mt-2">
                      <GiftIcon className="w-4 h-4 shrink-0" />
                      {t.loyaltyProgress(loyaltyStatus.order_count, loyaltyStatus.orders_until_reward)}
                    </p>
                  )}
                  {loyaltyStatus.is_birthday_today && (
                    <p className="mt-1 flex items-center gap-1.5">
                      <CakeIcon className="w-4 h-4 shrink-0" />
                      {t.loyaltyBirthdayBanner}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {restaurant.cafe_mode_enabled ? (
          <section className="mb-6">{availableItems.map(renderItem)}</section>
        ) : (
          categories.map((category) => (
            <section key={category} className="mb-6">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-amber-700 mb-2">
                {menuCategoryLabel(category, locale)}
              </h2>
              {availableItems.filter((m) => m.category === category).map(renderItem)}
            </section>
          ))
        )}

        {cartLines.length > 0 && (
          <div className="fixed bottom-0 left-0 right-0 bg-white border-t p-4">
            <div className="max-w-md mx-auto">
              {restaurant.ramadan_mode_enabled && restaurant.iftar_time && (
                <label className="flex items-center gap-2 text-sm text-indigo-900 mb-3">
                  <input
                    type="checkbox"
                    checked={preOrderForIftar}
                    onChange={(e) => setPreOrderForIftar(e.target.checked)}
                  />
                  <MoonIcon className="w-4 h-4 shrink-0" />
                  {t.preorderCheckboxLabel(formatTime(restaurant.iftar_time))}
                </label>
              )}
              <div className="flex justify-between items-center">
                <span className="font-medium">
                  {total.toFixed(2)} {t.currency}
                </span>
                <button
                  onClick={validateOrder}
                  disabled={sending}
                  className="bg-neutral-900 text-white px-4 py-2 rounded-lg"
                >
                  {sending ? t.sending : t.validateOrder}
                </button>
              </div>
            </div>
          </div>
        )}

        {cartLines.length === 0 && cartClearedNotice && (
          <div className="fixed bottom-0 left-0 right-0 bg-white border-t p-4">
            <div className="max-w-md mx-auto flex items-center gap-3">
              <EmptyCartIllustration className="w-10 h-10 shrink-0 text-neutral-400" />
              <p className="text-sm text-neutral-600 flex-1">{t.cartClearedNotice}</p>
              <button
                onClick={() => setCartClearedNotice(false)}
                aria-label={t.closeErrorAria}
                className="text-neutral-400 shrink-0"
              >
                ✕
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
