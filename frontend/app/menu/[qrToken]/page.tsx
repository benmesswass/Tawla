"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Cairo } from "next/font/google";
import {
  api,
  mediaUrl,
  wsUrl,
  orderWsUrl as buildOrderWsUrl,
  ApiError,
  LoyaltyMember,
  MenuItem,
  Order,
  OrderStatus,
  RestaurantPublic,
  Table,
} from "@/lib/api";
import { toLocalizedMessage } from "@/lib/errors";
import { useReconnectingSocket } from "@/lib/useReconnectingSocket";
import { useLocale } from "@/lib/i18n/useLocale";
import { menuCategoryLabel } from "@/lib/menuCategories";
import { duree, elapsedSeconds, useHorloge } from "@/lib/duree";
import SplitBill from "@/components/SplitBill";
import { MoonIcon, UtensilsIcon, GiftIcon, CakeIcon, BellIcon, FlameIcon, WifiOffIcon, ShareIcon } from "@/components/icons";
import Skeleton from "@/components/ui/Skeleton";
import CelebrationOverlay from "@/components/CelebrationOverlay";
import EmptyCartIllustration from "@/components/illustrations/EmptyCartIllustration";
import LoyaltyStampCard from "@/components/LoyaltyStampCard";
import { CULTURAL_FACTS } from "@/lib/culturalFacts";
import { generateShareCardBlob } from "@/lib/shareCard";

const cairo = Cairo({ subsets: ["arabic", "latin"], weight: ["400", "600", "700"] });

type CartLine = {
  item: MenuItem;
  quantity: number;
  note: string;
  shared: boolean;
  // Numéros de places qui se partagent ce plat. Vide = toute la table. Saisi
  // ici plutôt qu'au moment de payer : le client vient de composer sa
  // commande, il sait qui prend quoi — dix minutes plus tard, il ne sait plus.
  sharedWith: number[];
  // Ajoutée depuis une proposition « avec ce plat » plutôt que depuis la carte.
  // Sert uniquement à mesurer l'effet de la vente incitative (Phase 14.1).
  fromSuggestion: boolean;
};

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

/**
 * Reprise du suivi après un rafraîchissement de page : il faut désormais
 * conserver le `public_token` en plus de l'identifiant, puisque l'identifiant
 * seul ne donne plus accès à la commande (Phase 12.2).
 */
type TrackedOrderRef = { id: number; token: string };

/**
 * Une **liste** de commandes, et non plus une seule.
 *
 * Une table commande souvent en plusieurs fois — on reprend un dessert, une
 * tournée de thé — et le token de chaque commande est la seule clé qui permet
 * de la suivre et de la payer. Tant qu'on n'en gardait qu'un, « commander à
 * nouveau » écrasait le précédent : l'addition d'une commande non réglée
 * devenait inatteignable, donc impayable. Constaté au premier service.
 */
function storeTrackedOrderRef(qrToken: string, id: number, token: string): void {
  const refs = readTrackedOrderRefs(qrToken).filter((r) => r.id !== id);
  refs.push({ id, token });
  localStorage.setItem(lastOrderStorageKey(qrToken), JSON.stringify(refs));
}

function forgetTrackedOrderRef(qrToken: string, id: number): void {
  const refs = readTrackedOrderRefs(qrToken).filter((r) => r.id !== id);
  if (refs.length === 0) {
    localStorage.removeItem(lastOrderStorageKey(qrToken));
    return;
  }
  localStorage.setItem(lastOrderStorageKey(qrToken), JSON.stringify(refs));
}

function readTrackedOrderRefs(qrToken: string): TrackedOrderRef[] {
  const raw = localStorage.getItem(lastOrderStorageKey(qrToken));
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    // Format d'avant : un objet unique. Un client qui a commandé juste avant
    // une mise à jour ne doit pas perdre le suivi de sa commande en cours.
    const list = Array.isArray(parsed) ? parsed : [parsed];
    return list.filter(
      (r): r is TrackedOrderRef => typeof r?.id === "number" && typeof r?.token === "string"
    );
  } catch {
    // Contenu illisible (l'identifiant seul, avant la Phase 12.2) : inutilisable
    // sans token, on l'oublie plutôt que de tenter un appel voué au 404.
  }
  localStorage.removeItem(lastOrderStorageKey(qrToken));
  return [];
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

// `crypto.randomUUID` n'existe qu'en contexte sécurisé (HTTPS) : absent, il
// vaut `undefined` et l'appeler plantait le panier sans aucun message (C-1,
// audit 2026-08-18). Repli suffisant : cet identifiant n'a besoin que d'être
// unique par panier, pas cryptographique.
function genererIdPanier(): string {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

type CreateOrderPayload = Parameters<typeof api.createOrder>[0];

export default function MenuPage({ params }: { params: { qrToken: string } }) {
  const { qrToken } = params;
  const { t, locale, toggleLocale } = useLocale();

  const [table, setTable] = useState<Table | null>(null);
  const [restaurant, setRestaurant] = useState<RestaurantPublic | null>(null);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [cart, setCart] = useState<Record<number, CartLine>>({});
  const [cartOrderId, setCartOrderId] = useState<string | null>(null);
  // Nombre de personnes à table, demandé seulement quand un plat est marqué
  // « à partager » — jamais à l'ouverture du menu, où la question n'a pas
  // encore de raison d'être posée.
  const [convives, setConvives] = useState(2);
  // Toutes les commandes encore ouvertes de cette table — celle qu'on suit à
  // l'écran, et celles qu'on a quittées sans les régler.
  const [openOrders, setOpenOrders] = useState<{ order: Order; token: string }[]>([]);
  // Horloge partagée de l'écran de suivi : une seule source pour tous les
  // compteurs affichés.
  const maintenant = useHorloge();
  const [suggestions, setSuggestions] = useState<Record<string, number[]>>({});
  // Plat dont on propose les accompagnements juste après l'ajout au panier.
  // Un seul à la fois : empiler les propositions transformerait la page en
  // tunnel de vente, ce qu'un client de restaurant ne supporte pas.
  const [suggestFor, setSuggestFor] = useState<MenuItem | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [trackedOrder, setTrackedOrder] = useState<Order | null>(null);
  // Reçu une seule fois à la création de la commande : sans lui, plus aucun
  // appel de suivi ni de paiement n'est autorisé (Phase 12.2).
  const [orderToken, setOrderToken] = useState<string | null>(null);
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
  const [loyaltyFirstVisit, setLoyaltyFirstVisit] = useState(false);
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
        const [rest, items, suggested] = await Promise.all([
          api.getRestaurantByToken(qrToken),
          api.getMenuByToken(qrToken),
          // Best-effort : une carte sans suggestions reste une carte utilisable,
          // l'échec de cet appel ne doit jamais bloquer la commande.
          api.getMenuSuggestionsByToken(qrToken).catch(() => ({})),
        ]);
        setRestaurant(rest);
        setMenu(items);
        setSuggestions(suggested);

        // Commandes encore ouvertes pour cette table (ex: téléphone rafraîchi
        // pendant que le plat était en préparation, ou addition d'une première
        // tournée pas encore réglée) : on reprend leur suivi au lieu de
        // remontrer le menu comme si de rien n'était.
        const refs = readTrackedOrderRefs(qrToken);
        const resolved = await Promise.all(
          refs.map(async (ref) => {
            try {
              const order = await api.getOrder(ref.id, ref.token);
              // Servie ET réglée : plus rien à suivre ni à payer, on oublie.
              // Servie mais impayée, en revanche, doit rester atteignable —
              // c'est précisément l'addition qu'on perdait.
              if (order.status === "cancelled" || (order.status === "served" && order.payment_status === "paid")) {
                forgetTrackedOrderRef(qrToken, ref.id);
                return null;
              }
              return { order, token: ref.token };
            } catch {
              forgetTrackedOrderRef(qrToken, ref.id);
              return null;
            }
          })
        );

        const ouvertes = resolved.filter((r): r is { order: Order; token: string } => r !== null);
        setOpenOrders(ouvertes);
        const derniere = ouvertes[ouvertes.length - 1];
        if (derniere) {
          setTrackedOrder(derniere.order);
          setOrderToken(derniere.token);
        }
      })
      .catch((e) => setLoadError(toLocalizedMessage(e, locale)));
  }, [qrToken, locale]);

  useEffect(() => {
    load();
  }, [load]);

  // Page de retour du paiement carte Konnect (`?konnect=success` /
  // `?konnect=fail`, voir orders/router.py::start_card_payment) : Konnect ne
  // peut jamais joindre un webhook sur localhost en dev, ce filet de sécurité
  // (`api.checkCardPayment`) est donc le SEUL moyen de refléter le paiement —
  // même principe que la page de retour de l'abonnement (dashboard/page.tsx).
  // L'id et le token de la commande voyagent dans l'URL de retour : cette
  // page peut suivre plusieurs commandes ouvertes à la fois, rien d'autre ne
  // dit laquelle vient d'être payée.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const konnectResult = params.get("konnect");
    if (!konnectResult) return;
    const returnedOrderId = Number(params.get("order_id"));
    const returnedOrderToken = params.get("order_token");
    window.history.replaceState(null, "", window.location.pathname);

    if (konnectResult === "fail") {
      setPaymentError(t.paymentFailedRetry);
      return;
    }
    if (konnectResult !== "success" || !returnedOrderId || !returnedOrderToken) return;

    api
      .checkCardPayment(returnedOrderId, returnedOrderToken)
      .then((updated) => {
        setOpenOrders((prev) =>
          prev.map((r) => (r.order.id === updated.id ? { order: updated, token: returnedOrderToken } : r))
        );
        setTrackedOrder(updated);
        setOrderToken(returnedOrderToken);
      })
      .catch((e) => setPaymentError(toLocalizedMessage(e, locale)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      storeTrackedOrderRef(qrToken, order.id, order.public_token);
      setOfflineQueuedPayload(null);
      setTrackedOrder(order);
      setOrderToken(order.public_token);
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
      setLoyaltyFirstVisit(false);
      return;
    }
    try {
      const status = await api.lookupLoyalty(qrToken, phone.trim());
      setLoyaltyStatus(status);
      setLoyaltyFirstVisit(false);
      localStorage.setItem(loyaltyPhoneStorageKey(restaurant.id), phone.trim());
    } catch (e) {
      // Depuis la Phase 19.1 la route ne crée plus la fiche : un numéro
      // inconnu répond 404, et c'est exactement ce qu'est une première visite.
      // Le client le voit dit ainsi plutôt qu'en lisant « 0 commande ».
      if (e instanceof ApiError && e.code === "LOYALTY_MEMBER_NOT_FOUND") {
        setLoyaltyStatus(null);
        setLoyaltyFirstVisit(true);
        localStorage.setItem(loyaltyPhoneStorageKey(restaurant.id), phone.trim());
        return;
      }
      // Vérification de statut best-effort — une autre erreur ne doit jamais
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
      if (!orderToken) return;
      await api.savePushSubscription(
        trackedOrder.id,
        subscription.toJSON() as PushSubscriptionJSON,
        orderToken
      );
      setPushState("subscribed");
    } catch {
      setPushState("error");
    }
  }

  // Suivi temps réel de la commande après validation — jusqu'ici le client
  // n'avait plus aucune nouvelle après "commande envoyée" (audit PO 2026-08-10).
  const orderSocketUrl =
    trackedOrder && restaurant && orderToken
      ? buildOrderWsUrl(`/ws/order/${restaurant.id}/${trackedOrder.id}`, orderToken)
      : null;
  useReconnectingSocket(orderSocketUrl, (msg) => {
    if (msg.event === "order.status_changed" && trackedOrder && msg.order_id === trackedOrder.id) {
      setTrackedOrder((prev) => (prev ? { ...prev, status: msg.status } : prev));
      if (msg.status === "served" || msg.status === "cancelled") {
        localStorage.removeItem(lastOrderStorageKey(qrToken));
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

  // Canal de la table, ouvert dès le scan du QR : il porte ce qui concerne le
  // client sans concerner une commande précise. Sans lui, un serveur pouvait
  // répondre à l'appel et cliquer « résolu » sans que le bouton redevienne
  // cliquable côté client — il fallait recharger la page pour s'en apercevoir.
  const tableWsUrl = restaurant ? wsUrl(`/ws/table/${restaurant.id}/${qrToken}`) : null;
  useReconnectingSocket(tableWsUrl, (msg) => {
    if (msg.event === "waiter_call.resolved") {
      setWaiterCallState("idle");
    }
  });

  // La commande suivie évolue (paiement, changement de statut) : on répercute
  // dans la liste des commandes ouvertes, en un seul endroit plutôt qu'à chaque
  // appel. Une fois servie ET réglée, elle en sort — c'est la seule condition
  // qui autorise à l'oublier.
  useEffect(() => {
    if (!trackedOrder || !orderToken) return;
    const soldee =
      trackedOrder.status === "cancelled" ||
      (trackedOrder.status === "served" && trackedOrder.payment_status === "paid");
    setOpenOrders((prev) => {
      const autres = prev.filter((r) => r.order.id !== trackedOrder.id);
      if (soldee) {
        forgetTrackedOrderRef(qrToken, trackedOrder.id);
        return autres;
      }
      return [...autres, { order: trackedOrder, token: orderToken }];
    });
  }, [trackedOrder, orderToken, qrToken]);

  // Le compteur de fidélité n'avance qu'au paiement confirmé côté serveur —
  // on rafraîchit l'affichage client à ce moment précis (carte immédiate,
  // cash via le WebSocket ci-dessus) plutôt que de deviner la nouvelle valeur.
  useEffect(() => {
    if (trackedOrder?.payment_status === "paid" && loyaltyPhone.trim()) {
      checkLoyaltyStatus(loyaltyPhone);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trackedOrder?.payment_status]);

  async function payByCard() {
    if (!trackedOrder) return;
    setPaying(true);
    setPaymentError(null);
    const tip = Number(tipInput.replace(",", ".")) || 0;
    try {
      if (!orderToken) return;
      const updated = await api.payByCard(trackedOrder.id, tip, orderToken);
      // Restaurant ayant connecté son propre Konnect (modèle direct,
      // 2026-08-19) : rediriger pour régler, la commande reste "pending"
      // jusqu'au retour (`?konnect=success`, voir l'effet plus bas). Sans
      // `pay_url` : mode démo, déjà payée, rien de plus à faire.
      if (updated.pay_url) {
        window.location.href = updated.pay_url;
        return;
      }
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
      if (!orderToken) return;
      // Le pourboire vaut aussi pour les espèces : il était saisi puis perdu,
      // et le serveur venait encaisser le total sans lui.
      const tip = Number(tipInput.replace(",", ".")) || 0;
      const updated = await api.requestCashPayment(trackedOrder.id, tip, orderToken);
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
      await api.callWaiter(qrToken);
      setWaiterCallState("called");
      // Le bouton redevient cliquable dès qu'un serveur marque l'appel résolu
      // (canal de la table, plus haut). Ce délai n'est plus que le filet du
      // cas où personne ne le marque jamais : sans lui, le client resterait
      // bloqué sur un appel que la salle a oublié.
      setTimeout(() => setWaiterCallState("idle"), 90_000);
    } catch (e) {
      setWaiterCallError(toLocalizedMessage(e, locale));
      setWaiterCallState("idle");
    }
  }

  function addToCart(item: MenuItem, fromSuggestion = false) {
    // L'identifiant naît avec le panier, pas à l'envoi : régénéré à chaque
    // tentative, il ne protégerait de rien. C'est lui qui fait qu'un double
    // clic sur « Valider », ou une file hors ligne rejouée, retombe sur la
    // même commande au lieu d'en faire préparer deux (Phase 19.2).
    setCartOrderId((prev) => prev ?? genererIdPanier());
    setCart((prev) => {
      const existing = prev[item.id];
      return {
        ...prev,
        [item.id]: {
          item,
          quantity: (existing?.quantity ?? 0) + 1,
          note: existing?.note ?? "",
          shared: existing?.shared ?? false,
          sharedWith: existing?.sharedWith ?? [],
          // Une ligne déjà au panier garde son origine : si le client a d'abord
          // pris le plat depuis la carte, en reprendre un depuis une suggestion
          // n'en fait pas une vente incitative.
          fromSuggestion: existing?.fromSuggestion ?? fromSuggestion,
        },
      };
    });
    setCartClearedNotice(false);
    setBumpedItemId(item.id);
    setTimeout(() => setBumpedItemId((cur) => (cur === item.id ? null : cur)), 300);

    // Propose les accompagnements du plat qu'on vient d'ajouter — jamais ceux
    // d'un article lui-même issu d'une suggestion, pour ne pas enchaîner.
    if (!fromSuggestion) {
      const suggestedIds = suggestions[String(item.id)] ?? [];
      const proposable = suggestedIds.filter((id) => !cart[id]);
      setSuggestFor(proposable.length ? item : null);
    }
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
    setCart((prev) =>
      prev[itemId]
        ? { ...prev, [itemId]: { ...prev[itemId], shared, sharedWith: shared ? prev[itemId].sharedWith : [] } }
        : prev
    );
  }

  function toggleConvive(itemId: number, place: number) {
    setCart((prev) => {
      const ligne = prev[itemId];
      if (!ligne) return prev;
      const sharedWith = ligne.sharedWith.includes(place)
        ? ligne.sharedWith.filter((p) => p !== place)
        : [...ligne.sharedWith, place].sort((a, b) => a - b);
      return { ...prev, [itemId]: { ...ligne, sharedWith } };
    });
  }

  const cartLines = Object.values(cart);
  const total = cartLines.reduce((sum, l) => sum + l.item.price * l.quantity, 0);

  async function validateOrder() {
    if (!table || cartLines.length === 0) return;
    setSending(true);
    setOrderError(null);
    const payload: CreateOrderPayload = {
      qr_token: qrToken,
      items: cartLines.map((l) => ({
        menu_item_id: l.item.id,
        quantity: l.quantity,
        notes: l.note || null,
        is_shared: l.shared,
        shared_with: l.shared ? l.sharedWith : [],
        from_suggestion: l.fromSuggestion,
      })),
      scheduled_for: preOrderForIftar && restaurant?.iftar_time ? restaurant.iftar_time : null,
      loyalty_phone: loyaltyPhone.trim() || null,
      loyalty_birth_date: loyaltyBirthDate || null,
      client_order_id: cartOrderId,
    };
    try {
      const order = await api.createOrder(payload);
      storeTrackedOrderRef(qrToken, order.id, order.public_token);
      setTrackedOrder(order);
      setOrderToken(order.public_token);
      setCart({});
      setCartOrderId(null);
      setPreOrderForIftar(false);
      setShowCelebration(true);
    } catch (e) {
      // Échec réseau (pas une réponse de l'API, ex: connexion mobile coupée
      // en pleine validation) : on garde la commande de côté sur le téléphone
      // du client plutôt que de la perdre — envoi automatique dès que le
      // réseau revient (voir flushOfflineQueue).
      if (e instanceof TypeError) {
        // La charge utile part en file avec son identifiant : c'est lui, et
        // pas un nouveau, qui sera rejoué au retour du réseau.
        localStorage.setItem(offlineQueueStorageKey(qrToken), JSON.stringify(payload));
        setOfflineQueuedPayload(payload);
        setCart({});
        setCartOrderId(null);
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
        api.getMenuByToken(qrToken).then(setMenu).catch(() => {});
      }
      setOrderError(toLocalizedMessage(e, locale));
    } finally {
      setSending(false);
    }
  }

  function orderAgain() {
    // On quitte l'écran de suivi pour retourner au menu, sans rien oublier :
    // la commande reste dans `openOrders` et son token en session. Tant qu'elle
    // n'est pas réglée, le client doit pouvoir y revenir — l'effacer ici lui
    // faisait perdre l'addition de sa première tournée.
    setTrackedOrder(null);
    setOrderToken(null);
  }

  function suivreCommande(ref: { order: Order; token: string }) {
    setTrackedOrder(ref.order);
    setOrderToken(ref.token);
  }

  // Commandes ouvertes autres que celle affichée : ce sont elles qu'un rappel
  // doit signaler, sinon le client repart sans avoir payé.
  const autresCommandesOuvertes = openOrders.filter((r) => r.order.id !== trackedOrder?.id);
  const resteAPayer = autresCommandesOuvertes
    .filter((r) => r.order.payment_status !== "paid")
    .reduce((sum, r) => sum + r.order.total_amount, 0);

  // L'ardoise : toutes les commandes de la table encore à régler, celle qu'on
  // regarde comprise, dans l'ordre où elles ont été passées.
  const ardoise = openOrders
    .filter((r) => r.order.payment_status !== "paid")
    .sort((a, b) => a.order.id - b.order.id);
  const totalArdoise = ardoise.reduce((sum, r) => sum + r.order.total_amount, 0);

  // Carte de partage social (Instagram/WhatsApp Status) — générée
  // entièrement côté client sur <canvas>, sans backend ni service tiers.
  // Web Share API quand elle supporte les fichiers, sinon téléchargement.
  async function shareOrder() {
    if (!trackedOrder || !restaurant) return;
    setSharingOrder(true);
    try {
      const blob = await generateShareCardBlob({
        restaurantName: restaurant.name,
        items: trackedOrder.items.map((it) => ({
          name: it.menu_item_name,
          quantity: it.quantity,
          unitPrice: it.unit_price,
          lineTotal: it.unit_price * it.quantity,
        })),
        total: trackedOrder.total_amount,
        tip: trackedOrder.tip_amount,
        tableLabel: trackedOrder.table_label,
        orderId: trackedOrder.id,
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

        {/* Le client voyait « Envoyé » sans savoir depuis combien de temps.
            Une attente qu'on peut lire se supporte ; une attente muette fait
            lever la tête pour chercher un serveur. */}
        {!cancelled &&
          (() => {
            const secondes = elapsedSeconds(trackedOrder.created_at, maintenant);
            if (secondes === null) return null;
            return (
              <p className="mt-1 text-sm text-center text-[var(--ink-soft)] tabular-nums">
                {t.orderElapsed(duree(secondes))}
              </p>
            );
          })()}

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

        {/* L'ardoise de la table. Quand on a commandé deux fois sans payer, le
            client voulait savoir ce qu'il doit **en tout** — l'addition de sa
            deuxième tournée seule ne veut rien dire au moment de régler. */}
        {!cancelled && ardoise.length > 1 && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
            <p className="text-sm font-medium text-amber-900">{t.tableTotalTitle}</p>
            <ul className="mt-2 space-y-1 text-sm text-amber-900">
              {ardoise.map((r) => (
                <li key={r.order.id} className="flex justify-between gap-2">
                  <span>
                    {t.orderLabel(r.order.id)}
                    {r.order.id === trackedOrder.id && ` — ${t.thisOrder}`}
                  </span>
                  <span className="tabular-nums">
                    {r.order.total_amount.toFixed(2)} {t.currency}
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-2 pt-2 border-t border-amber-200 flex justify-between font-semibold text-amber-900">
              <span>{t.tableTotal}</span>
              <span className="tabular-nums">
                {totalArdoise.toFixed(2)} {t.currency}
              </span>
            </div>
            <p className="mt-1.5 text-xs text-amber-900/80">{t.tableTotalNote}</p>
          </div>
        )}

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

  // Toute la carte est affichée, ruptures comprises : elles apparaissent
  // barrées et non commandables (voir renderItem). Une catégorie entièrement
  // en rupture reste donc visible, ce qui est l'information juste — le
  // restaurant a bien des desserts, il n'en a plus ce soir.
  const categories = Array.from(new Set(menu.map((m) => m.category)));

  function categoryAnchor(category: string): string {
    // Ancre stable et sûre en URL : les catégories sont saisies par le
    // restaurant, donc accentuées et espacées.
    return `cat-${encodeURIComponent(category).replace(/%/g, "")}`;
  }

  function renderItem(item: MenuItem, index = 0) {
    // Un plat en rupture reste sur la carte, barré : le faire disparaître
    // laissait le client chercher un plat qu'il avait vu la minute d'avant, ou
    // qu'un voisin de table est en train de manger. Le dire est plus honnête
    // que l'escamoter (retour du premier service).
    const rupture = !item.is_available;
    const photo = mediaUrl(item.image_url);
    return (
      <div
        key={item.id}
        // Décalage plafonné à 6 plats : au-delà, l'attente se verrait plus que
        // l'effet. Le style inline est le seul moyen d'indexer un délai.
        style={{ animationDelay: `${Math.min(index, 6) * 35}ms` }}
        className={`plat-apparait mb-3 rounded-2xl border border-[var(--line)] bg-[var(--semoule-raised)] p-3 shadow-sm transition-shadow ${
          rupture ? "opacity-60" : ""
        }`}
      >
        <div className="flex items-start gap-3">
          {/* La photo d'abord, et visible sur téléphone : elle était masquée
              en dessous de `sm`, c'est-à-dire précisément là où le client
              commande. Une carte de restaurant sans photos ne donne pas faim. */}
          {photo && (
            <div className="relative shrink-0 w-20 h-20">
              {/* La même image, floutée derrière la vignette : elle projette la
                  couleur du plat sur le fond crème et fait ressortir la photo
                  sans ajouter le moindre octet. */}
              <div
                aria-hidden
                className="absolute inset-0 rounded-xl bg-cover bg-center blur-md opacity-40 scale-95"
                style={{ backgroundImage: `url(${photo})` }}
              />
              <img
                src={photo}
                alt={item.name}
                loading="lazy"
                className="relative w-20 h-20 rounded-xl object-cover border-2 border-white shadow-md"
              />
            </div>
          )}
          <div className="min-w-0 flex-1">
            <div className={`font-medium ${rupture ? "line-through" : ""}`}>
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
            {item.description && (
              <div className="text-sm text-[var(--ink-soft)] mt-0.5 leading-snug">{item.description}</div>
            )}
            {item.allergens && (
              <div className="text-xs text-[var(--ink-soft)]/70 mt-0.5">{t.allergensLabel(item.allergens)}</div>
            )}
            {rupture && (
              <div className="text-xs font-medium text-[var(--harissa)] mt-1">{t.itemOutOfStock}</div>
            )}

            {/* Prix et boutons sur la même ligne, au bas de la carte : le prix
                est ce qu'on cherche, le bouton ce qu'on vise. Les séparer de
                part et d'autre les rendait tous les deux difficiles à trouver. */}
            <div className="flex items-center justify-between gap-2 mt-2">
              <span
                className={`font-semibold tabular-nums text-[var(--harissa)] ${rupture ? "line-through" : ""}`}
              >
                {item.price.toFixed(2)} {t.currency}
              </span>
              <div className="flex items-center gap-2 shrink-0">
                {cart[item.id] && (
                  <>
                    <button
                      onClick={() => removeFromCart(item.id)}
                      aria-label={t.removeFromCartAria(item.name)}
                      className="w-9 h-9 rounded-full border border-[var(--line)] bg-white transition-transform active:scale-90"
                    >
                      −
                    </button>
                    <span
                      className={`inline-block min-w-[1.5rem] text-center font-medium tabular-nums ${
                        bumpedItemId === item.id ? "animate-cart-bump" : ""
                      }`}
                    >
                      {cart[item.id].quantity}
                    </span>
                  </>
                )}
                <button
                  onClick={() => addToCart(item)}
                  disabled={rupture}
                  aria-label={t.addToCartAria(item.name)}
                  className="w-9 h-9 rounded-full bg-[var(--harissa)] text-white text-lg leading-none shadow-sm transition-transform active:scale-90 disabled:opacity-30 disabled:active:scale-100"
                >
                  +
                </button>
              </div>
            </div>
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
            {cart[item.id].shared && (
              <div className="mt-2">
                <p className="text-xs text-[var(--ink-soft)]">{t.sharedWithLabel}</p>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {Array.from({ length: convives }, (_, i) => i + 1).map((place) => {
                    const choisi = cart[item.id].sharedWith.includes(place);
                    return (
                      <button
                        key={place}
                        type="button"
                        onClick={() => toggleConvive(item.id, place)}
                        aria-pressed={choisi}
                        className={`rounded-full border px-3 py-1 text-sm transition-colors ${
                          choisi
                            ? "bg-[var(--harissa)] text-white border-[var(--harissa)]"
                            : "border-[var(--line)] bg-white text-[var(--encre)]"
                        }`}
                      >
                        {t.personLabel(place)}
                      </button>
                    );
                  })}
                </div>
                {cart[item.id].sharedWith.length === 0 && (
                  <p className="mt-1 text-xs text-[var(--ink-soft)]/80">{t.sharedWithEveryone}</p>
                )}
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  return (
    <div dir={dir} className={`pb-32 ${wrapperClassName ?? ""}`}>
      <header className="bg-[var(--harissa)] text-white px-4 py-5 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-balance">{restaurant.name}</h1>
          <p className="text-white/80 text-sm">{table.label}</p>
        </div>
        <div className="flex flex-col items-end gap-2 shrink-0">
          <button
            onClick={toggleLocale}
            className="text-sm border border-white/40 rounded-lg px-3 py-1.5 text-white/90"
          >
            {t.localeSwitchLabel}
          </button>
          <button
            onClick={callWaiter}
            disabled={waiterCallState !== "idle"}
            className="text-sm border border-white/40 rounded-lg px-3 py-1.5 text-white/90 disabled:opacity-70 whitespace-nowrap"
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

      {/* Navigation par catégories, collée en haut du défilement. Sur une carte
          de cinquante plats, atteindre les desserts demandait de faire défiler
          toute la carte — et le client qui cherche renonce avant de trouver.
          Masquée en mode café, dont la carte est justement sans catégories. */}
      {!restaurant.cafe_mode_enabled && categories.length > 1 && (
        <nav className="sticky top-0 z-30 bg-[var(--semoule)]/95 backdrop-blur border-b border-[var(--line)]">
          <ul className="flex gap-2 overflow-x-auto px-4 py-2.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {categories.map((category) => (
              <li key={category}>
                <a
                  href={`#${categoryAnchor(category)}`}
                  className="inline-block whitespace-nowrap rounded-full border border-[var(--line)] bg-white px-3.5 py-1.5 text-sm font-medium text-[var(--encre)] transition-colors active:bg-[var(--harissa)] active:text-white"
                >
                  {menuCategoryLabel(category, locale)}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      )}

      <div className="p-4 max-w-md mx-auto">
        {/* Commandes déjà passées et pas encore réglées : sans ce rappel, une
            première tournée s'oubliait dès qu'on retournait au menu, et le
            client repartait sans avoir payé. */}
        {autresCommandesOuvertes.length > 0 && (
          <div className="mb-4 border rounded-lg p-3 bg-amber-50 border-amber-200">
            <p className="text-sm font-medium text-amber-900">
              {t.openOrdersTitle(autresCommandesOuvertes.length, resteAPayer)}
            </p>
            <ul className="mt-2 space-y-1.5">
              {autresCommandesOuvertes.map((ref) => (
                <li key={ref.order.id}>
                  <button
                    onClick={() => suivreCommande(ref)}
                    className="w-full text-start text-sm underline text-amber-900 flex justify-between gap-2"
                  >
                    <span>{t.openOrderLine(ref.order.id, ref.order.items.length)}</span>
                    <span className="tabular-nums shrink-0">
                      {ref.order.total_amount.toFixed(2)} {t.currency}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
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
              {/* Le client doit savoir à quoi sert son numéro avant de le
                  taper — pas dans une page qu'il n'ouvrira jamais (Phase 16). */}
              <p className="text-xs text-orange-900/80 leading-relaxed">
                {t.loyaltyConsentNotice}{" "}
                <Link href="/confidentialite" className="underline">
                  {t.loyaltyPrivacyLink}
                </Link>
              </p>
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
              {loyaltyFirstVisit && (
                <p className="text-sm text-orange-900 pt-1 flex items-center gap-1.5">
                  <GiftIcon className="w-4 h-4 shrink-0" />
                  {t.loyaltyFirstVisit}
                </p>
              )}
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
          <section className="mb-6">{menu.map((item, i) => renderItem(item, i))}</section>
        ) : (
          categories.map((category) => (
            <section key={category} id={categoryAnchor(category)} className="mb-8 scroll-mt-20">
              {/* Un titre encadré de deux filets : sur une carte longue, c'est
                  ce qui fait qu'on voit qu'on a changé de section en faisant
                  défiler, sans avoir à lire. */}
              <h2 className="flex items-center gap-3 mb-3">
                <span className="h-px flex-1 bg-[var(--line)]" />
                <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--laiton)] whitespace-nowrap">
                  {menuCategoryLabel(category, locale)}
                </span>
                <span className="h-px flex-1 bg-[var(--line)]" />
              </h2>
              {menu.filter((m) => m.category === category).map((item, i) => renderItem(item, i))}
            </section>
          ))
        )}

        {cartLines.length > 0 && (
          <div className="fixed bottom-0 left-0 right-0 bg-white border-t p-4">
            <div className="max-w-md mx-auto">
              {/* Posé seulement quand un plat est à partager : sinon c'est une
                  question de plus entre le client et sa commande. */}
              {cartLines.some((l) => l.shared) && (
                <label className="flex items-center gap-2 text-sm text-[var(--ink-soft)] mb-3">
                  {t.dinersLabel}
                  <input
                    type="number"
                    min={2}
                    max={12}
                    value={convives}
                    onChange={(e) => setConvives(Math.max(2, Math.min(12, Number(e.target.value) || 2)))}
                    className="w-16 border border-[var(--line)] rounded px-2 py-1"
                  />
                </label>
              )}
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

        {suggestFor && (
          <div
            className={`fixed left-0 right-0 bg-white border-t p-4 shadow-lg ${
              cartLines.length > 0 ? "bottom-[132px]" : "bottom-0"
            }`}
          >
            <div className="max-w-md mx-auto">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">{t.suggestionTitle(suggestFor.name)}</p>
                  <p className="text-xs text-neutral-500">{t.suggestionHint}</p>
                </div>
                <button
                  onClick={() => setSuggestFor(null)}
                  aria-label={t.closeErrorAria}
                  className="text-neutral-400 shrink-0"
                >
                  ✕
                </button>
              </div>
              <ul className="mt-3 space-y-2">
                {(suggestions[String(suggestFor.id)] ?? [])
                  .map((id) => menu.find((m) => m.id === id))
                  .filter((item): item is MenuItem => !!item && item.is_available && !cart[item.id])
                  .map((item) => (
                    <li key={item.id} className="flex items-center gap-3">
                      <span className="flex-1 text-sm">
                        {item.name}
                        <span className="text-neutral-500"> · {item.price.toFixed(2)} DT</span>
                      </span>
                      <button
                        onClick={() => addToCart(item, true)}
                        className="text-sm font-medium px-3 py-1.5 rounded-lg bg-[var(--harissa)] text-white"
                      >
                        {t.suggestionAdd}
                      </button>
                    </li>
                  ))}
              </ul>
              <button
                onClick={() => setSuggestFor(null)}
                className="mt-3 text-sm text-neutral-500 underline"
              >
                {t.suggestionDismiss}
              </button>
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
