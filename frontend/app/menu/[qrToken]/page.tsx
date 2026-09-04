"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { cairo, lalezar } from "@/lib/fonts";
import {
  api,
  mediaUrl,
  invoiceUrl,
  wsUrl,
  orderWsUrl as buildOrderWsUrl,
  ApiError,
  LoyaltyMember,
  MenuItem,
  MenuItemOptionGroup,
  Order,
  OrderStatus,
  RestaurantPublic,
  Table,
} from "@/lib/api";
import { urlBase64ToUint8Array } from "@/lib/webPush";
import { toLocalizedMessage } from "@/lib/errors";
import { formatAmount } from "@/lib/currency";
import { currentMarket } from "@/lib/market";
import { useReconnectingSocket } from "@/lib/useReconnectingSocket";
import { useLocale } from "@/lib/i18n/useLocale";
import { menuCategoryLabel } from "@/lib/menuCategories";
import { duree, elapsedSeconds, useHorloge } from "@/lib/duree";
import SplitBill from "@/components/SplitBill";
import TawlaMark from "@/components/brand/TawlaMark";
import VignetteCategorie from "@/components/VignetteCategorie";
import ReseauxSociaux from "@/components/ReseauxSociaux";
import {
  MoonIcon,
  UtensilsIcon,
  GiftIcon,
  CakeIcon,
  BellIcon,
  FlameIcon,
  WifiOffIcon,
  ShareIcon,
  StampIcon,
} from "@/components/icons";
import Skeleton from "@/components/ui/Skeleton";
import CelebrationOverlay from "@/components/CelebrationOverlay";
import EmptyCartIllustration from "@/components/illustrations/EmptyCartIllustration";
import LoyaltyStampCard from "@/components/LoyaltyStampCard";
import QrCode from "@/components/QrCode";
import { culturalFactsFor } from "@/lib/culturalFacts";
import { generateShareCardBlob } from "@/lib/shareCard";

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
  // Choix faits dans le sélecteur d'options (France, MARCHE_FRANCE.md phase
  // F5/A2) — un seul jeu de choix par article au panier (v1) : rouvrir le
  // sélecteur remplace la sélection plutôt que d'ajouter une seconde ligne.
  selectedOptions: SelectedOption[];
};

type SelectedOption = { optionId: number; groupName: string; optionName: string; priceDelta: number };

type StepStatus = Exclude<OrderStatus, "cancelled">;

// La frise côté client regroupe "envoyée en cuisine" et "en préparation" en une
// seule étape "En cuisine" — une distinction utile au serveur, pas au client
// qui attend son plat.
type DisplayStep = "received" | "confirmed" | "in_kitchen" | "ready" | "served";

const DISPLAY_STEPS: DisplayStep[] = ["received", "confirmed", "in_kitchen", "ready", "served"];

function displayStepIndex(status: StepStatus): number {
  switch (status) {
    case "pending_confirmation":
      return 0;
    case "confirmed":
      return 1;
    case "sent_to_kitchen":
    case "in_preparation":
      return 2;
    case "ready":
      return 3;
    case "served":
      return 4;
  }
}

function lastOrderStorageKey(qrToken: string): string {
  return `resto-qr-menu:last-order:${qrToken}`;
}

// Une seule fois par commande : sans ça, rouvrir la page après paiement (ou
// une reconnexion WebSocket) redéclencherait la modale d'avis Google à
// chaque fois (Phase D1bis).
function googleReviewShownStorageKey(orderId: number): string {
  return `resto-qr-menu:avis-google-propose:${orderId}`;
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
  // Article en cours de configuration dans le sélecteur d'options (France,
  // MARCHE_FRANCE.md phase F5/A2) — un seul à la fois, comme suggestFor.
  const [optionChooserFor, setOptionChooserFor] = useState<MenuItem | null>(null);
  // Modale d'avis Google post-paiement (Phase D1bis).
  const [showGoogleReview, setShowGoogleReview] = useState(false);
  // Catégorie surlignée dans la barre collante (Phase D2 de ROADMAP_DESIGN.md)
  // — stocke l'ancre (`categoryAnchor(category)`), pas le nom brut : c'est ce
  // que l'IntersectionObserver lit directement sur `section.id`.
  const [activeCategoryAnchor, setActiveCategoryAnchor] = useState<string | null>(null);
  // groupId -> ids des options choisies dans ce groupe, pendant la composition.
  const [chooserSelection, setChooserSelection] = useState<Record<number, number[]>>({});
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
  const [customerEmail, setCustomerEmail] = useState("");
  const [paying, setPaying] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [preOrderForIftar, setPreOrderForIftar] = useState(false);
  const [waiterCallState, setWaiterCallState] = useState<"idle" | "calling" | "called">("idle");
  const [waiterCallError, setWaiterCallError] = useState<string | null>(null);
  const [offlineQueuedPayload, setOfflineQueuedPayload] = useState<CreateOrderPayload | null>(null);
  const [retryingOffline, setRetryingOffline] = useState(false);
  const [offlineRetryCountdown, setOfflineRetryCountdown] = useState(5);
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

  function renderLoyaltyCard(status: LoyaltyMember) {
    const complete = status.reward_available;
    return (
      <div
        className={`rounded-2xl p-3 ${
          complete
            ? "bg-[var(--espresso)] border border-[var(--laiton)]"
            : "bg-[var(--creme)] border border-[rgba(184,134,46,.5)]"
        }`}
      >
        <div className="flex items-center gap-1.5">
          <StampIcon className={`w-4 h-4 shrink-0 ${complete ? "text-[var(--laiton-on-espresso-text)]" : "text-[var(--laiton)]"}`} />
          {complete ? (
            <h3 className={`${lalezar.className} text-[21px] leading-none text-[var(--laiton)]`}>
              {t.loyaltyCompleteTitle}
            </h3>
          ) : (
            <h3 className="text-[13px] font-semibold text-[var(--encre)]">{t.loyaltyCardTitle}</h3>
          )}
        </div>
        <div className="mt-2.5">
          <LoyaltyStampCard filled={loyaltyStampsFilled(status)} rewardAvailable={complete} />
        </div>
        {complete ? (
          <p className="mt-3 w-full text-center bg-[var(--harissa)] text-[var(--semoule)] rounded-xl py-[13px] text-[14.5px] font-bold">
            {t.loyaltyRewardAvailable}
          </p>
        ) : (
          <p className="mt-2 text-center text-xs text-[var(--ink-soft)]">
            {t.loyaltyProgress(status.order_count, status.orders_until_reward)}
          </p>
        )}
        {status.is_birthday_today && (
          <p
            className={`mt-1.5 flex items-center justify-center gap-1.5 text-xs ${
              complete ? "text-[var(--laiton-on-espresso-text)]" : "text-[var(--laiton)]"
            }`}
          >
            <CakeIcon className="w-4 h-4 shrink-0" /> {t.loyaltyBirthdayBanner}
          </p>
        )}
      </div>
    );
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

  // Compte à rebours affiché sur l'écran hors ligne : retente aussi toutes les
  // 5s pendant que la commande patiente, sans attendre l'évènement "online" du
  // navigateur qui ne se déclenche pas toujours sur une connexion instable.
  useEffect(() => {
    if (!offlineQueuedPayload) return;
    setOfflineRetryCountdown(5);
    const tick = setInterval(() => setOfflineRetryCountdown((c) => (c <= 1 ? 5 : c - 1)), 1000);
    const retry = setInterval(() => flushOfflineQueue(), 5000);
    return () => {
      clearInterval(tick);
      clearInterval(retry);
    };
  }, [offlineQueuedPayload, flushOfflineQueue]);

  useEffect(() => {
    if (!showCelebration) return;
    const timer = setTimeout(() => setShowCelebration(false), 1800);
    return () => clearTimeout(timer);
  }, [showCelebration]);

  // Anecdote culturelle qui tourne pendant l'attente cuisine (10-20 min en
  // moyenne) — un petit plus pendant l'attente plutôt qu'un écran silencieux.
  // Contenu propre à chaque marché, et au type d'établissement en France
  // (`restaurant?.cafe_mode_enabled`) — voir lib/culturalFacts.ts.
  const inKitchenWait =
    trackedOrder?.status === "sent_to_kitchen" || trackedOrder?.status === "in_preparation";
  const culturalFacts = culturalFactsFor(locale, restaurant?.cafe_mode_enabled ?? false);
  // Une seule condition, consommée à la fois par l'effet (qui fait tourner
  // l'anecdote) et par le rendu plus bas (qui l'affiche) — #151 avait déjà
  // corrigé cette duplication pour `currentMarket.culturalFactsEnabled`,
  // appliqué ici à `culturalFacts.length` : `culturalFactsFor` ne renvoie
  // jamais un tableau vide pour un marché servi, mais la condition doit
  // rester unique pour ne pas se dédoubler une seconde fois.
  const showCulturalFacts = inKitchenWait && culturalFacts.length > 0;
  useEffect(() => {
    if (!showCulturalFacts) return;
    // `cafe_mode_enabled` peut basculer en direct (dashboard manager)
    // pendant que le client a cette page ouverte (vérifié en live, voir le
    // message de ce commit) — `culturalFacts` change alors de longueur (7
    // anecdotes resto vs 6 café). Remettre l'index à 0 à chaque changement
    // de tableau : sans ça, un index resté à 6 sur un tableau de 6 (indices
    // 0-5) affiche `undefined` jusqu'au prochain tick de l'intervalle.
    setCulturalFactIndex(0);
    const timer = setInterval(() => {
      setCulturalFactIndex((i) => (i + 1) % culturalFacts.length);
    }, 8000);
    return () => clearInterval(timer);
  }, [showCulturalFacts, culturalFacts]);

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

  // Modale d'avis Google (Phase D1bis) : même transition que ci-dessus,
  // identique quel que soit le mode de paiement. Rien si le restaurant n'a
  // pas renseigné de lien (palier sous Pro compris — le verrou est à
  // l'écriture côté Réglages, pas ici) ou si déjà proposée pour cette
  // commande précise.
  useEffect(() => {
    if (
      trackedOrder?.payment_status === "paid" &&
      restaurant?.google_review_url &&
      !localStorage.getItem(googleReviewShownStorageKey(trackedOrder.id))
    ) {
      localStorage.setItem(googleReviewShownStorageKey(trackedOrder.id), "1");
      setShowGoogleReview(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trackedOrder?.payment_status]);

  // Barre de catégories collante : surligne celle en cours de lecture
  // (Phase D2 de ROADMAP_DESIGN.md). Requêté sur le DOM réel plutôt que sur
  // `categories` (calculé plus bas, après les retours anticipés ci-dessous,
  // donc indisponible ici) — sans incidence : la vue de suivi de commande et
  // le mode café n'ont pas de section `cat-…`, l'observer n'y observe rien.
  useEffect(() => {
    const sections = Array.from(document.querySelectorAll<HTMLElement>("section[id^='cat-']"));
    if (sections.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActiveCategoryAnchor(entry.target.id);
        });
      },
      // Bande de détection fine juste sous la barre collante (~48px de haut)
      // plutôt que la moitié de l'écran : sur une section courte (1-2 plats),
      // une bande large aurait sauté la catégorie plutôt que de s'y arrêter.
      { rootMargin: "-56px 0px -70% 0px", threshold: 0 }
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, [menu]);

  // La pastille active se recentre dans la barre horizontale : sans ça, sur
  // une carte à 5-6 catégories, elle finit hors du cadre visible dès qu'on
  // avance dans la carte et le surlignage ne sert plus à rien.
  useEffect(() => {
    if (!activeCategoryAnchor) return;
    document.getElementById(`${activeCategoryAnchor}-pill`)?.scrollIntoView({
      behavior: "smooth",
      inline: "center",
      block: "nearest",
    });
  }, [activeCategoryAnchor]);

  async function payByCard() {
    if (!trackedOrder) return;
    setPaying(true);
    setPaymentError(null);
    const tip = Number(tipInput.replace(",", ".")) || 0;
    try {
      if (!orderToken) return;
      const updated = await api.payByCard(trackedOrder.id, tip, orderToken, customerEmail.trim() || undefined);
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
      const updated = await api.requestCashPayment(trackedOrder.id, tip, orderToken, customerEmail.trim() || undefined);
      setTrackedOrder(updated);
    } catch (e) {
      setPaymentError(toLocalizedMessage(e, locale));
    } finally {
      setPaying(false);
    }
  }

  async function payByCardTerminal() {
    if (!trackedOrder) return;
    setPaying(true);
    setPaymentError(null);
    try {
      if (!orderToken) return;
      const tip = Number(tipInput.replace(",", ".")) || 0;
      const updated = await api.requestCardTerminalPayment(
        trackedOrder.id, tip, orderToken, customerEmail.trim() || undefined
      );
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

  function addToCart(item: MenuItem, fromSuggestion = false, selectedOptions?: SelectedOption[]) {
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
          // Choix du sélecteur d'options, gardés à l'identique tant qu'on ne
          // fait qu'incrémenter la quantité (voir openOptionChooser).
          selectedOptions: selectedOptions ?? existing?.selectedOptions ?? [],
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

  // --- Sélecteur d'options (France, MARCHE_FRANCE.md phase F5/A2) ----------
  // v1 volontairement simple : un seul jeu de choix par article au panier.
  // Rouvrir le sélecteur (bouton "+" tant que rien n'est encore au panier)
  // sert aussi à corriger un choix avant validation ; ajouter un DEUXIÈME
  // article identique avec une combinaison différente n'est pas couvert —
  // limitation connue, pas un oubli.

  function openOptionChooser(item: MenuItem) {
    const initial: Record<number, number[]> = {};
    for (const group of item.option_groups) initial[group.id] = [];
    setChooserSelection(initial);
    setOptionChooserFor(item);
  }

  function toggleChooserOption(group: MenuItemOptionGroup, optionId: number) {
    setChooserSelection((prev) => {
      const current = prev[group.id] ?? [];
      if (current.includes(optionId)) {
        return { ...prev, [group.id]: current.filter((id) => id !== optionId) };
      }
      // Choix unique (max 1) : le nouveau remplace l'ancien, comme un bouton
      // radio. Choix multiple : s'ajoute tant que max_select n'est pas atteint.
      const next = group.max_select <= 1 ? [optionId] : [...current, optionId].slice(-group.max_select);
      return { ...prev, [group.id]: next };
    });
  }

  function chooserSatisfiesMinimums(item: MenuItem): boolean {
    return item.option_groups.every((g) => (chooserSelection[g.id]?.length ?? 0) >= g.min_select);
  }

  function chooserTotalPrice(item: MenuItem): number {
    const delta = item.option_groups
      .flatMap((g) => g.options.filter((o) => (chooserSelection[g.id] ?? []).includes(o.id)))
      .reduce((sum, o) => sum + o.price_delta, 0);
    return item.price + delta;
  }

  function confirmOptionChooser() {
    const item = optionChooserFor;
    if (!item || !chooserSatisfiesMinimums(item)) return;
    const selected: SelectedOption[] = item.option_groups.flatMap((g) =>
      g.options
        .filter((o) => (chooserSelection[g.id] ?? []).includes(o.id))
        .map((o) => ({ optionId: o.id, groupName: g.name, optionName: o.name, priceDelta: o.price_delta }))
    );
    addToCart(item, false, selected);
    setOptionChooserFor(null);
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
  // Prix de base + suppléments des options choisies (France, F5/A2) — jamais
  // relu ailleurs que dans le panier : le serveur refige tout à la création
  // de la commande (voir orders/service.py::create_order côté backend).
  function lineUnitPrice(line: CartLine): number {
    return line.item.price + line.selectedOptions.reduce((sum, o) => sum + o.priceDelta, 0);
  }
  const total = cartLines.reduce((sum, l) => sum + lineUnitPrice(l) * l.quantity, 0);

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
        selected_option_ids: l.selectedOptions.map((o) => o.optionId),
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

  // Relance au moment où le repas touche à sa fin plutôt qu'un bouton statique
  // "commander à nouveau" (retour démo 2026-08-31, point 13) : réutilise les
  // suggestions "avec ce plat" déjà configurées par le restaurant (Phase 14.1)
  // sur les articles de CETTE commande, plutôt qu'un moteur de reco à part.
  // Vide si le restaurant n'a rien configuré pour ces plats — le bouton simple
  // reste alors le seul affiché, pas de UI vide.
  const postOrderSuggestions: MenuItem[] =
    trackedOrder?.status === "served"
      ? Array.from(new Set(trackedOrder.items.flatMap((line) => suggestions[String(line.menu_item_id)] ?? [])))
          .map((id) => menu.find((m) => m.id === id))
          .filter(
            (item): item is MenuItem =>
              !!item &&
              item.is_available &&
              !cart[item.id] &&
              !trackedOrder.items.some((line) => line.menu_item_id === item.id)
          )
          .slice(0, 3)
      : [];

  function addSuggestionAndOrderAgain(item: MenuItem) {
    addToCart(item, true);
    orderAgain();
  }

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
      <div dir={dir} className={`min-h-screen bg-[var(--semoule)] p-6 max-w-md mx-auto text-center ${wrapperClassName ?? ""}`}>
        <p className="text-[var(--harissa)] mb-4">{loadError}</p>
        <button
          onClick={load}
          className="bg-[var(--harissa)] text-[var(--semoule)] px-5 py-3 rounded-xl font-bold text-[14.5px] shadow-[0_2px_0_var(--harissa-pressed)] active:shadow-none active:translate-y-[2px]"
        >
          {t.retry}
        </button>
      </div>
    );
  }
  if (!table || !restaurant) {
    return (
      <div dir={dir} className={`min-h-screen bg-[var(--semoule)] ${wrapperClassName ?? ""}`}>
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

  // Modale d'avis Google (Phase D1bis) : calculée une seule fois, référencée
  // depuis les deux branches de retour plus bas (suivi de commande, puis
  // navigation du menu). Le paiement se termine toujours dans la première —
  // un retour anticipé séparé du retour principal — donc la modale doit y
  // être atteignable elle aussi, pas seulement dans le retour principal.
  const googleReviewModal = showGoogleReview && restaurant.google_review_url && (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-0 sm:p-4"
      role="dialog"
      aria-modal="true"
      onClick={() => setShowGoogleReview(false)}
    >
      <div
        className="w-full max-w-md rounded-t-2xl sm:rounded-2xl bg-[var(--semoule-raised)] p-[22px] text-center"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-center gap-1 text-[var(--laiton)]">
          {Array.from({ length: 5 }).map((_, i) => (
            <svg key={i} viewBox="0 0 24 24" fill="currentColor" className="w-[22px] h-[22px]">
              <path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1L12 2Z" />
            </svg>
          ))}
        </div>
        <p className={`${lalezar.className} text-[22px] mt-3`}>{t.googleReviewTitle}</p>
        <p className="text-[13.5px] text-[var(--ink-soft)] leading-[1.5] mt-1.5">
          {t.googleReviewBody(restaurant.name)}
        </p>
        <a
          href={restaurant.google_review_url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => setShowGoogleReview(false)}
          className="block mt-[18px] bg-[var(--harissa)] text-[var(--semoule)] rounded-full py-[13px] text-[14.5px] font-bold"
        >
          {t.googleReviewCta}
        </a>
        <button
          onClick={() => setShowGoogleReview(false)}
          className="mt-2 text-[13px] text-[var(--ink-faint)] underline"
        >
          {t.googleReviewDismiss}
        </button>
      </div>
    </div>
  );

  if (offlineQueuedPayload) {
    return (
      <div dir={dir} className={`min-h-screen bg-[var(--semoule)] p-6 max-w-md mx-auto ${wrapperClassName ?? ""}`}>
        <div className="rounded-2xl border border-[var(--laiton)] bg-[var(--creme)] p-[14px]">
          <div className="flex items-center gap-2">
            <WifiOffIcon className="w-[18px] h-[18px] shrink-0 text-[var(--laiton)]" />
            <h1 className="text-[13.5px] font-bold text-[var(--encre)]">{t.offlineQueuedTitle}</h1>
          </div>
          <p className="mt-2 text-[12.5px] leading-[1.5] text-[var(--ink-soft)]">{t.offlineQueuedMessage}</p>
          <div className="mt-3 rounded-xl border border-[var(--line-strong)] bg-[var(--semoule-raised)] py-[13px] text-center">
            <p className="text-sm font-semibold text-[var(--ink-soft)] tabular-nums">
              {retryingOffline ? t.sending : t.offlineRetryCountdown(offlineRetryCountdown)}
            </p>
          </div>
        </div>
        <button
          onClick={flushOfflineQueue}
          disabled={retryingOffline}
          className="mt-4 w-full bg-[var(--harissa)] text-[var(--semoule)] rounded-xl py-3 font-bold text-[14.5px] shadow-[0_2px_0_var(--harissa-pressed)] active:shadow-none active:translate-y-[2px] disabled:opacity-50"
        >
          {retryingOffline ? t.sending : t.retryNow}
        </button>
      </div>
    );
  }

  if (trackedOrder) {
    const currentDisplayIndex = displayStepIndex(trackedOrder.status as StepStatus);
    const cancelled = trackedOrder.status === "cancelled";
    return (
      <>
        {showCelebration && <CelebrationOverlay />}
        <div dir={dir} className={`min-h-screen bg-[var(--semoule)] pt-[22px] px-[18px] pb-[30px] max-w-md mx-auto ${wrapperClassName ?? ""}`}>
        <h1 className={`${lalezar.className} text-[27px] leading-tight text-center text-[var(--encre)]`}>
          {cancelled ? t.orderCancelledTitle : t.orderSentTitle}
        </h1>
        <p className="mt-2 text-[13px] text-[var(--ink-soft)] text-center">{t.orderSubtitle(table.label, trackedOrder.id)}</p>

        {/* Le client voyait « Envoyé » sans savoir depuis combien de temps.
            Une attente qu'on peut lire se supporte ; une attente muette fait
            lever la tête pour chercher un serveur. */}
        {!cancelled &&
          (() => {
            const secondes = elapsedSeconds(trackedOrder.created_at, maintenant);
            if (secondes === null) return null;
            return (
              <p className="mt-1 text-[12.5px] font-semibold text-center text-[var(--laiton)] tabular-nums">
                {t.orderElapsed(duree(secondes))}
              </p>
            );
          })()}

        {/* Même `data-visite` que le bouton d'appel de la carte, plus bas : les
            deux écrans ne coexistent jamais (celui-ci sort par un retour
            anticipé), et la visite trouve sa cible sur l'un comme sur l'autre. */}
        <div className="mt-4 text-center" data-visite="client-appel">
          <button
            onClick={callWaiter}
            disabled={waiterCallState !== "idle"}
            className="min-h-[44px] inline-flex items-center gap-1.5 text-xs font-semibold border border-[var(--line)] bg-white text-[var(--encre)] rounded-full px-3 py-[11px] disabled:opacity-70"
          >
            {waiterCallState === "called" ? (
              t.callWaiterSent
            ) : (
              <>
                <BellIcon className="w-[14px] h-[14px] shrink-0" />
                {t.callWaiterButton}
              </>
            )}
          </button>
          {waiterCallError && <p className="mt-2 text-sm text-[var(--harissa)]">{waiterCallError}</p>}
        </div>

        {!cancelled && trackedOrder.scheduled_for && (
          <p className="mt-4 text-sm text-center bg-[rgba(184,134,46,.12)] text-[#8a6420] border border-[rgba(184,134,46,.55)] rounded-xl py-2 px-3 flex items-center justify-center gap-1.5">
            <MoonIcon className="w-4 h-4 shrink-0 text-[var(--laiton)]" />
            {t.preorderBadge(formatTime(trackedOrder.scheduled_for))}
          </p>
        )}

        {!cancelled && trackedOrder.taken_by_staff_name && (
          <p className="mt-4 text-sm text-center bg-[rgba(184,134,46,.12)] text-[#8a6420] border border-[rgba(184,134,46,.55)] rounded-xl py-2 px-3">
            {t.dedicatedServer(trackedOrder.taken_by_staff_name)}
          </p>
        )}

        {!cancelled &&
          trackedOrder.status !== "ready" &&
          trackedOrder.status !== "served" &&
          pushState !== "unsupported" && (
            <div className="mt-4 text-center">
              {pushState === "subscribed" ? (
                <p className="text-sm text-[var(--menthe)] flex items-center justify-center gap-1.5">
                  <BellIcon className="w-4 h-4 shrink-0" />
                  {t.pushSubscribed}
                </p>
              ) : pushState === "denied" ? (
                <p className="text-sm text-[var(--ink-faint)]">{t.pushDenied}</p>
              ) : (
                <button
                  onClick={subscribeToPush}
                  disabled={pushState === "subscribing"}
                  className="text-sm border border-[var(--line)] bg-white text-[var(--encre)] rounded-full px-3 py-1.5 disabled:opacity-70"
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
          <div className="mt-4">{renderLoyaltyCard(loyaltyStatus)}</div>
        )}

        {!cancelled && (
          <ol className="mt-8">
            {DISPLAY_STEPS.map((step, i) => {
              const isLast = i === DISPLAY_STEPS.length - 1;
              // Sur la dernière étape, `i` n'est jamais strictement inférieur
              // à `currentDisplayIndex` (rien après « servie ») : sans le cas
              // `isLast`, ce repère restait « en cours » à vie une fois la
              // commande servie (audit produit du 2026-08-28).
              const done = isLast ? i <= currentDisplayIndex : i < currentDisplayIndex;
              const current = i === currentDisplayIndex && !done;
              const showWaitHint = current && step === "in_kitchen";
              return (
                <li key={step} className="relative ps-[46px] pb-5 last:pb-0">
                  {!isLast && (
                    <span
                      className="absolute top-[34px] bottom-0 w-0.5 start-[17px]"
                      style={{ backgroundColor: done ? "var(--menthe)" : "var(--line)" }}
                    />
                  )}
                  <span
                    className={`absolute top-0 start-0 w-[34px] h-[34px] rounded-full flex items-center justify-center text-[12.5px] font-bold ${
                      current ? "animate-tw-pulse" : ""
                    }`}
                    style={{
                      backgroundColor: done ? "var(--menthe)" : current ? "var(--harissa)" : "var(--creme)",
                      color: done || current ? "var(--semoule)" : "var(--ink-faint)",
                      border: done ? "1px solid var(--menthe)" : current ? "1px solid var(--harissa)" : "1px solid var(--line)",
                    }}
                  >
                    {done ? "✓" : i + 1}
                  </span>
                  <div className="pt-1">
                    <span
                      className={current ? "font-bold" : done ? "font-semibold" : "font-normal"}
                      style={{ color: current || done ? "var(--encre)" : "var(--ink-faint)" }}
                    >
                      {t.trackingSteps[step]}
                    </span>
                    {showWaitHint && (
                      <p className="text-[11.5px] mt-0.5 text-[var(--ink-soft)]">{t.kitchenWaitHint}</p>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        )}

        {!cancelled && showCulturalFacts && (
          <div className="mt-4 text-[12.5px] leading-[1.5] rounded-xl py-[11px] px-3 flex items-start gap-2 bg-[var(--semoule-raised)] border border-[var(--line)] text-[var(--encre)]">
            <FlameIcon className="w-[15px] h-[15px] shrink-0 mt-0.5 text-[var(--laiton)]" />
            <span>{culturalFacts[culturalFactIndex]}</span>
          </div>
        )}

        <div className="mt-8 border-t border-[var(--line)] pt-[14px]">
          <p className="text-[10.5px] font-bold uppercase tracking-[0.14em] text-[var(--laiton)] mb-2">
            {t.orderDetailsTitle}
          </p>
          <ul className="text-[13px] leading-[1.75] text-[var(--ink-soft)] space-y-0">
            {trackedOrder.items.map((it) => (
              <li key={it.id}>
                {it.quantity}× {it.menu_item_name}
                {it.is_shared && (
                  <span className="text-[var(--laiton)] inline-flex items-center gap-1 align-middle">
                    · <UtensilsIcon className="w-3.5 h-3.5 shrink-0" /> {t.sharedTag}
                  </span>
                )}
                {it.options.length > 0 && (
                  <span className="text-[var(--ink-faint)]"> — {it.options.map((o) => o.option_name).join(", ")}</span>
                )}
                {it.notes && <span className="text-[var(--ink-faint)]"> — {it.notes}</span>}
              </li>
            ))}
          </ul>
          <div className="flex justify-between text-[15px] font-bold text-[var(--encre)] mt-2 pt-2 border-t border-[var(--line)]">
            <span>{t.total}</span>
            <span className="tabular-nums">
              {formatAmount(trackedOrder.total_amount)} {t.currency}
            </span>
          </div>
        </div>

        {/* L'ardoise de la table. Quand on a commandé deux fois sans payer, le
            client voulait savoir ce qu'il doit **en tout** — l'addition de sa
            deuxième tournée seule ne veut rien dire au moment de régler. */}
        {!cancelled && ardoise.length > 1 && (
          <div className="mt-4 rounded-xl border border-[rgba(184,134,46,.5)] bg-[var(--creme)] p-3">
            <p className="text-sm font-semibold text-[var(--encre)]">{t.tableTotalTitle}</p>
            <ul className="mt-2 space-y-1 text-sm text-[var(--ink-soft)]">
              {ardoise.map((r) => (
                <li key={r.order.id} className="flex justify-between gap-2">
                  <span>
                    {t.orderLabel(r.order.id)}
                    {r.order.id === trackedOrder.id && ` — ${t.thisOrder}`}
                  </span>
                  <span className="tabular-nums">
                    {formatAmount(r.order.total_amount)} {t.currency}
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-2 pt-2 border-t border-[rgba(184,134,46,.35)] flex justify-between font-semibold text-[var(--encre)]">
              <span>{t.tableTotal}</span>
              <span className="tabular-nums">
                {formatAmount(totalArdoise)} {t.currency}
              </span>
            </div>
            <p className="mt-1.5 text-xs text-[var(--ink-soft)]">{t.tableTotalNote}</p>
          </div>
        )}

        {!cancelled && (
          <div className="mt-6 border-t border-[var(--line)] pt-[14px]">
            <p className="text-[10.5px] font-bold uppercase tracking-[0.14em] text-[var(--laiton)] mb-3">
              {t.paymentTitle}
            </p>

            {trackedOrder.payment_status === "paid" && (
              <>
                <div className="rounded-xl p-[13px] bg-[rgba(31,107,79,.1)] border border-[rgba(31,107,79,.45)] flex items-center gap-3">
                  <span className="w-[26px] h-[26px] rounded-full bg-[var(--menthe)] text-[var(--semoule)] flex items-center justify-center shrink-0 text-sm font-bold">
                    ✓
                  </span>
                  <p className="text-[13.5px] font-semibold text-[var(--menthe)]">
                    {t.paidMessage(trackedOrder.payment_method ?? "card", trackedOrder.tip_amount)}
                  </p>
                </div>
                <p className="mt-2 text-[12.5px] text-[var(--ink-soft)] text-center">
                  {t.orderSubtitle(table.label, trackedOrder.id)}
                </p>
                {orderToken && (
                  <div className="mt-3 text-center">
                    <a
                      href={invoiceUrl(trackedOrder.id, orderToken)}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-block w-full text-sm font-semibold border border-[var(--line)] bg-white text-[var(--encre)] rounded-xl py-2.5"
                    >
                      {t.invoiceDownload}
                    </a>
                    <QrCode
                      url={invoiceUrl(trackedOrder.id, orderToken)}
                      alt="QR code de la facture"
                      caption={t.invoiceQrCaption}
                    />
                  </div>
                )}
              </>
            )}

            {trackedOrder.payment_status === "pending" && (
              <p className="text-sm text-[#8a6420] bg-[rgba(184,134,46,.12)] border border-[rgba(184,134,46,.55)] rounded-xl p-3">
                {trackedOrder.payment_method === "card_terminal"
                  ? t.cardTerminalPendingMessage(trackedOrder.total_amount)
                  : t.cashPendingMessage(trackedOrder.total_amount)}
              </p>
            )}

            {trackedOrder.payment_status === "unpaid" && (
              <div className="space-y-3">
                {paymentError && (
                  <div className="text-sm text-[var(--harissa)] bg-[rgba(214,64,30,.1)] border border-[rgba(214,64,30,.55)] rounded-xl p-3">
                    {paymentError}
                  </div>
                )}
                <SplitBill order={trackedOrder} t={t} />
                <div>
                  <p className="text-sm text-[var(--ink-soft)] mb-1.5">{t.tipLabel}</p>
                  <div className="flex gap-2">
                    {[0, 0.05, 0.1].map((pct) => {
                      const amount = Number((trackedOrder.total_amount * pct).toFixed(currentMarket.currency.decimals));
                      const selected = (tipInput === "" && pct === 0) || Number(tipInput) === amount;
                      return (
                        <button
                          key={pct}
                          type="button"
                          onClick={() => setTipInput(pct === 0 ? "" : String(amount))}
                          className={`flex-1 rounded-[10px] py-[9px] text-center ${
                            selected
                              ? "border border-[var(--harissa)] bg-[var(--creme)] text-[var(--harissa)] text-[12.5px] font-bold"
                              : "border border-[var(--line)] bg-white text-[var(--encre)] text-[12.5px] font-semibold"
                          }`}
                        >
                          {pct === 0 ? t.tipNone : `${Math.round(pct * 100)}%`}
                        </button>
                      );
                    })}
                  </div>
                  <input
                    type="text"
                    inputMode="decimal"
                    aria-label={t.tipLabel}
                    value={tipInput}
                    onChange={(e) => setTipInput(e.target.value.replace(/[^0-9.,]/g, ""))}
                    placeholder={t.tipPlaceholder}
                    className="mt-2 w-full text-sm bg-white border border-[var(--line)] rounded-xl px-3 py-2"
                  />
                </div>
                <div>
                  <label htmlFor="customer-email" className="text-sm text-[var(--ink-soft)]">
                    {t.emailLabel}
                  </label>
                  <input
                    id="customer-email"
                    type="email"
                    value={customerEmail}
                    onChange={(e) => setCustomerEmail(e.target.value)}
                    placeholder={t.emailPlaceholder}
                    className="mt-1 w-full text-sm bg-white border border-[var(--line)] rounded-xl px-3 py-2"
                  />
                </div>
                <button
                  onClick={payByCard}
                  disabled={paying}
                  className="w-full bg-[var(--harissa)] text-[var(--semoule)] rounded-xl py-[15px] text-[15px] font-bold shadow-[0_2px_0_var(--harissa-pressed)] active:shadow-none active:translate-y-[2px] disabled:opacity-50"
                >
                  {t.payByCard}
                </button>
                <button
                  onClick={payByCardTerminal}
                  disabled={paying}
                  className="w-full border border-[var(--line)] bg-white text-[var(--encre)] rounded-xl py-[13px] text-sm font-semibold disabled:opacity-50"
                >
                  {t.payByCardTerminal}
                </button>
                <button
                  onClick={payByCash}
                  disabled={paying}
                  className="w-full border border-[var(--line)] bg-white text-[var(--encre)] rounded-xl py-[13px] text-sm font-semibold disabled:opacity-50"
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
          className="mt-8 w-full border border-[var(--line)] bg-white text-[var(--encre)] rounded-xl py-2.5 text-sm font-semibold disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
        >
          <ShareIcon className="w-4 h-4 shrink-0" />
          {t.shareOrderButton}
        </button>

        {postOrderSuggestions.length > 0 ? (
          <div className="mt-3 border border-[var(--line)] bg-[var(--semoule-raised)] rounded-xl p-[14px]">
            <p className="text-sm font-bold text-[var(--encre)]">{t.postOrderSuggestionTitle}</p>
            <ul className="mt-2 space-y-2">
              {postOrderSuggestions.map((item) => (
                <li key={item.id} className="flex items-center gap-3">
                  <span className="flex-1 text-sm text-[var(--ink-soft)]">
                    <span className="text-[var(--encre)]">{item.name}</span> · {formatAmount(item.price)} {t.currency}
                  </span>
                  <button
                    onClick={() => addSuggestionAndOrderAgain(item)}
                    className="text-[12.5px] font-semibold px-[14px] py-2 rounded-[10px] bg-[var(--harissa)] text-[var(--semoule)]"
                  >
                    {t.suggestionAdd}
                  </button>
                </li>
              ))}
            </ul>
            <button onClick={orderAgain} className="mt-3 text-sm text-[var(--ink-soft)] underline">
              {t.orderAgain}
            </button>
          </div>
        ) : (
          <button
            onClick={orderAgain}
            className="mt-3 w-full border border-[var(--line)] bg-white text-[var(--encre)] rounded-xl py-2.5 text-sm font-semibold"
          >
            {t.orderAgain}
          </button>
        )}
        </div>
        {googleReviewModal}
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
    const ligne = cart[item.id];
    const perPerson = ligne
      ? (lineUnitPrice(ligne) * ligne.quantity) / (ligne.sharedWith.length > 0 ? ligne.sharedWith.length : convives)
      : 0;
    const hasOptionGroups = item.option_groups.length > 0;
    return (
      <div
        key={item.id}
        // Le premier plat de la carte sert de cible à la visite guidée : c'est
        // le seul élément dont on est sûr qu'il existe. Comparé sur l'id et non
        // sur `index`, qui repart à zéro à chaque catégorie.
        data-visite={item.id === menu[0]?.id ? "client-plat" : undefined}
        // Décalage plafonné à 6 plats : au-delà, l'attente se verrait plus que
        // l'effet. Le style inline est le seul moyen d'indexer un délai.
        style={{ animationDelay: `${Math.min(index, 6) * 35}ms` }}
        className="plat-apparait mb-[10px] rounded-[14px] border border-[var(--line)] bg-[var(--semoule-raised)] p-[11px] transition-shadow"
      >
        <div className="flex items-start gap-3">
          {/* La vignette est toujours présente, même sans photo : une carte de
              restaurant garde la même grille de lecture plat après plat. Sans
              photo, une tuile générique par catégorie (VignetteCategorie)
              plutôt qu'un vide — jamais une fausse photo qui ne ressemblerait
              pas au plat réel. */}
          <div className={`relative shrink-0 w-[72px] h-[72px] ${rupture ? "opacity-45" : ""}`}>
            {photo ? (
              <>
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
                  className="relative w-[72px] h-[72px] rounded-xl object-cover border-2 border-white shadow-md"
                />
              </>
            ) : (
              <VignetteCategorie category={item.category} />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className={`text-[14.5px] font-semibold leading-[1.25] ${rupture ? "line-through opacity-45" : ""}`}>
              {item.name}
              {item.spice_level > 0 && (
                <span className="ms-1 inline-flex items-center gap-0.5 align-middle text-[var(--harissa)]">
                  {Array.from({ length: item.spice_level }).map((_, i) => (
                    <FlameIcon key={i} className="w-[13px] h-[13px] shrink-0" />
                  ))}
                </span>
              )}
              {!item.is_halal && (
                <span className="ms-1 text-xs font-normal text-[var(--harissa)] border border-[var(--harissa)] rounded px-1 align-middle">
                  {t.notHalalBadge}
                </span>
              )}
            </div>
            {item.description && (
              <div className="text-[12.5px] leading-[1.35] text-[var(--ink-soft)] mt-[3px]">{item.description}</div>
            )}
            {item.allergens && (
              <div className="text-xs text-[var(--ink-soft)]/70 mt-0.5">{t.allergensLabel(item.allergens)}</div>
            )}
            {item.regimes.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {item.regimes.map((r) => (
                  <span
                    key={r.id}
                    className="text-[10.5px] font-medium text-[var(--menthe)] border border-[var(--menthe)] rounded px-1.5 py-[1px]"
                  >
                    {r.name}
                  </span>
                ))}
              </div>
            )}
            {rupture && (
              <div className="text-[11.5px] font-semibold text-[var(--harissa)] mt-1">{t.itemOutOfStock}</div>
            )}

            {/* Prix et boutons sur la même ligne, au bas de la carte : le prix
                est ce qu'on cherche, le bouton ce qu'on vise. Les séparer de
                part et d'autre les rendait tous les deux difficiles à trouver. */}
            <div className="flex items-center justify-between gap-2 mt-2">
              <span
                className={`text-[14.5px] font-bold tabular-nums text-[var(--harissa)] ${
                  rupture ? "line-through opacity-45" : ""
                }`}
              >
                {formatAmount(item.price)} {t.currency}
              </span>
              <div className="flex items-center gap-2 shrink-0">
                {ligne && (
                  <>
                    <button
                      onClick={() => removeFromCart(item.id)}
                      aria-label={t.removeFromCartAria(item.name)}
                      className="w-[34px] h-[34px] rounded-full border border-[var(--line)] bg-white transition-transform active:scale-90"
                    >
                      −
                    </button>
                    <span
                      className={`inline-block min-w-[16px] text-center text-[14px] font-bold tabular-nums ${
                        bumpedItemId === item.id ? "animate-cart-bump" : ""
                      }`}
                    >
                      {ligne.quantity}
                    </span>
                  </>
                )}
                <button
                  onClick={() => (hasOptionGroups && !ligne ? openOptionChooser(item) : addToCart(item))}
                  disabled={rupture}
                  aria-label={t.addToCartAria(item.name)}
                  className={`w-[34px] h-[34px] rounded-full text-[19px] leading-none shadow-sm transition-transform active:scale-90 disabled:cursor-not-allowed disabled:active:scale-100 ${
                    rupture
                      ? "bg-[var(--line-strong)] text-[var(--semoule)]"
                      : "bg-[var(--harissa)] text-[var(--semoule)]"
                  }`}
                >
                  +
                </button>
              </div>
            </div>
          </div>
        </div>
        {ligne && (
          <div className="mt-[10px] pt-[10px] border-t border-[var(--line)]">
            {ligne.selectedOptions.length > 0 && (
              <p className="text-xs text-[var(--ink-soft)] mb-2">
                {ligne.selectedOptions.map((o) => o.optionName).join(" · ")}
              </p>
            )}
            <input
              type="text"
              value={ligne.note}
              onChange={(e) => setNote(item.id, e.target.value)}
              placeholder={t.notePlaceholder}
              className="w-full text-xs bg-white border border-[var(--line)] rounded-[10px] px-[10px] py-2 placeholder:text-[var(--ink-soft)]"
            />
            <label className="mt-2 flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={ligne.shared}
                onChange={(e) => setShared(item.id, e.target.checked)}
                className="sr-only"
              />
              <span
                className="w-[18px] h-[18px] rounded-[5px] border-[1.5px] flex items-center justify-center shrink-0"
                style={{
                  backgroundColor: ligne.shared ? "var(--menthe)" : "#fff",
                  borderColor: ligne.shared ? "var(--menthe)" : "var(--line-strong)",
                }}
              >
                {ligne.shared && (
                  <svg
                    viewBox="0 0 24 24"
                    className="w-[11px] h-[11px]"
                    fill="none"
                    stroke="var(--semoule)"
                    strokeWidth={3}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M4 12l5 5L20 6" />
                  </svg>
                )}
              </span>
              <UtensilsIcon className="w-4 h-4 shrink-0 text-[var(--ink-soft)]" />
              <span className="text-[var(--encre)]">{t.sharedCheckboxLabel}</span>
            </label>
            {ligne.shared && (
              <div className="mt-2">
                <p className="text-xs text-[var(--ink-soft)]">{t.sharedWithLabel}</p>
                <div className="mt-1 flex flex-wrap gap-[6px]">
                  {Array.from({ length: convives }, (_, i) => i + 1).map((place) => {
                    const choisi = ligne.sharedWith.includes(place);
                    return (
                      <button
                        key={place}
                        type="button"
                        onClick={() => toggleConvive(item.id, place)}
                        aria-pressed={choisi}
                        className={`rounded-full border px-[12px] py-[5px] text-sm transition-colors ${
                          choisi
                            ? "bg-[var(--harissa)] text-[var(--semoule)] border-[var(--harissa)]"
                            : "border-[var(--line)] bg-white text-[var(--encre)]"
                        }`}
                      >
                        {t.personLabel(place)}
                      </button>
                    );
                  })}
                </div>
                {ligne.sharedWith.length === 0 ? (
                  <p className="mt-1 text-xs text-[var(--ink-soft)]/80">{t.sharedWithEveryone}</p>
                ) : (
                  <p className="mt-1 text-[11.5px] text-[var(--ink-soft)]">
                    {t.sharedPerPersonAmount(perPerson)}
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  const couverturePhoto = mediaUrl(restaurant.cover_photo_url);
  const logoPhoto = mediaUrl(restaurant.logo_url);
  const enTeteActions = (
    <>
      <button
        onClick={toggleLocale}
        className="min-h-[44px] inline-flex items-center text-xs font-semibold bg-[rgba(36,24,17,.2)] border border-[rgba(246,239,221,.34)] rounded-full px-3 py-[11px] whitespace-nowrap"
      >
        {t.localeSwitchLabel}
      </button>
      <button
        onClick={callWaiter}
        disabled={waiterCallState !== "idle"}
        data-visite="client-appel"
        className="min-h-[44px] inline-flex items-center gap-1.5 text-xs font-semibold bg-[rgba(36,24,17,.2)] border border-[rgba(246,239,221,.34)] rounded-full px-3 py-[11px] disabled:opacity-70 whitespace-nowrap"
      >
        {waiterCallState === "called" ? (
          t.callWaiterSent
        ) : (
          <>
            <BellIcon className="w-[14px] h-[14px] shrink-0" />
            {t.callWaiterButton}
          </>
        )}
      </button>
    </>
  );

  return (
    <div dir={dir} className={`min-h-screen bg-[var(--semoule)] pb-[132px] ${wrapperClassName ?? ""}`}>
      {/* Bannière de couverture (Phase D1 de ROADMAP_DESIGN.md, point 2) :
          seulement si le patron a envoyé une photo du lieu — sinon l'aplat
          harissa d'aujourd'hui reste tel quel, jamais un entre-deux à moitié
          garni. Le logo rond, lui, se décide indépendamment de la photo :
          celui du restaurant s'il existe, la marque Tawla sinon, dans les
          deux mises en page. */}
      {couverturePhoto ? (
        <header className="relative">
          <div
            role="img"
            aria-label={restaurant.name}
            className="relative h-32 bg-[var(--harissa)] overflow-hidden bg-cover bg-center"
            style={{ backgroundImage: `url(${couverturePhoto})` }}
          >
            <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[rgba(36,24,17,.55)]" />
            <div className="absolute top-[10px] end-[10px] flex flex-col items-end gap-[7px]">{enTeteActions}</div>
          </div>
          <div className="relative bg-[var(--harissa)] text-[var(--semoule)] pt-2 pb-3 ps-20 pe-4">
            <div className="absolute -top-7 start-3.5 w-14 h-14 rounded-full border-[3px] border-[var(--harissa)] shadow-md bg-[var(--semoule)] flex items-center justify-center overflow-hidden">
              {logoPhoto ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={logoPhoto} alt={restaurant.name} className="w-full h-full object-cover" />
              ) : (
                <TawlaMark size={32} />
              )}
            </div>
            <h1 className={`${lalezar.className} text-[28px] leading-[1.05] text-balance`}>{restaurant.name}</h1>
            <p className="text-[13px] font-medium text-[rgba(246,239,221,.82)] mt-0.5">{table.label}</p>
            {/* Ancrées à la ligne de la table, pas à celle du nom : cette
                ligne-là reste courte à gauche quelle que soit la longueur du
                nom au-dessus, donc jamais de collision (Phase D1, point 3). */}
            <ReseauxSociaux restaurant={restaurant} className="absolute bottom-3 end-4" />
          </div>
        </header>
      ) : (
        <header className="bg-[var(--harissa)] text-[var(--semoule)] px-4 pt-[10px] pb-[14px] flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            {logoPhoto ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={logoPhoto}
                alt={restaurant.name}
                className="w-[30px] h-[30px] rounded-full object-cover shrink-0 mt-0.5"
              />
            ) : (
              <TawlaMark size={30} variant="reserve" className="shrink-0 mt-0.5" />
            )}
            <div className="min-w-0">
              <h1 className={`${lalezar.className} text-[28px] leading-[1.05] text-balance`}>{restaurant.name}</h1>
              <p className="text-[13px] font-medium text-[rgba(246,239,221,.82)] mt-0.5">{table.label}</p>
            </div>
          </div>
          <div className="flex flex-col items-end gap-[7px] shrink-0">
            {enTeteActions}
            <ReseauxSociaux restaurant={restaurant} />
          </div>
        </header>
      )}

      {restaurant.ramadan_mode_enabled && restaurant.iftar_time && (
        <div className="bg-[var(--espresso)] px-4 py-[11px] flex items-start gap-2 text-[12.5px] leading-[1.45] text-[rgba(246,239,221,.88)]">
          <MoonIcon className="w-4 h-4 shrink-0 mt-0.5 text-[var(--laiton)]" />
          <p>
            <b className="text-[var(--laiton)]">{t.ramadanBannerPrefix}</b>
            {t.ramadanBannerRest(formatTime(restaurant.iftar_time))}
          </p>
        </div>
      )}

      {/* Navigation par catégories, collée en haut du défilement. Sur une carte
          de cinquante plats, atteindre les desserts demandait de faire défiler
          toute la carte — et le client qui cherche renonce avant de trouver.
          Masquée en mode café, dont la carte est justement sans catégories. */}
      {!restaurant.cafe_mode_enabled && categories.length > 1 && (
        <nav
          data-visite="client-categories"
          className="sticky top-0 z-30 bg-[rgba(246,239,221,.95)] backdrop-blur border-b border-[var(--line)]"
        >
          <ul className="flex gap-2 overflow-x-auto px-4 py-[11px] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {categories.map((category) => {
              const anchor = categoryAnchor(category);
              const active = anchor === activeCategoryAnchor;
              return (
                <li key={category}>
                  <a
                    id={`${anchor}-pill`}
                    href={`#${anchor}`}
                    className={`inline-block whitespace-nowrap rounded-full border px-[13px] py-[6px] text-[12.5px] font-semibold transition-colors active:bg-[var(--harissa)] active:text-[var(--semoule)] active:border-[var(--harissa)] ${
                      active
                        ? "bg-[var(--harissa)] text-[var(--semoule)] border-[var(--harissa)]"
                        : "bg-[var(--semoule-raised)] text-[var(--encre)] border-[var(--line)]"
                    }`}
                  >
                    {menuCategoryLabel(category, locale)}
                  </a>
                </li>
              );
            })}
          </ul>
        </nav>
      )}

      <div className="p-4 max-w-md mx-auto">
        {/* Commandes déjà passées et pas encore réglées : sans ce rappel, une
            première tournée s'oubliait dès qu'on retournait au menu, et le
            client repartait sans avoir payé. */}
        {autresCommandesOuvertes.length > 0 && (
          <div className="mb-4 rounded-2xl border border-[rgba(184,134,46,.5)] bg-[var(--creme)] p-3">
            <p className="text-sm font-semibold text-[var(--encre)]">
              {t.openOrdersTitle(autresCommandesOuvertes.length, resteAPayer)}
            </p>
            <ul className="mt-2 space-y-1.5">
              {autresCommandesOuvertes.map((ref) => (
                <li key={ref.order.id}>
                  <button
                    onClick={() => suivreCommande(ref)}
                    className="w-full text-start text-sm underline text-[var(--laiton)] flex justify-between gap-2"
                  >
                    <span>{t.openOrderLine(ref.order.id, ref.order.items.length)}</span>
                    <span className="tabular-nums shrink-0">
                      {formatAmount(ref.order.total_amount)} {t.currency}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {waiterCallError && (
          <div className="mb-4 text-sm text-[var(--harissa)] bg-[rgba(214,64,30,.1)] border border-[rgba(214,64,30,.55)] rounded-2xl p-3">
            {waiterCallError}
          </div>
        )}
        {orderError && (
          <div className="mb-4 text-sm text-[var(--harissa)] bg-[rgba(214,64,30,.1)] border border-[rgba(214,64,30,.55)] rounded-2xl p-3 flex justify-between items-start gap-2">
            <span>{orderError}</span>
            <button onClick={() => setOrderError(null)} aria-label={t.closeErrorAria} className="text-[var(--harissa)]">
              ✕
            </button>
          </div>
        )}

        <div className="mb-4 rounded-2xl border border-[rgba(184,134,46,.5)] bg-[var(--creme)] p-3">
          {!loyaltySectionOpen ? (
            <button
              onClick={() => setLoyaltySectionOpen(true)}
              className="text-[13px] font-semibold text-[var(--laiton)] inline-flex items-center gap-1.5"
            >
              <StampIcon className="w-4 h-4 shrink-0" />
              {t.loyaltyToggle}
            </button>
          ) : (
            <div className="space-y-2.5">
              {/* Le client doit savoir à quoi sert son numéro avant de le
                  taper — pas dans une page qu'il n'ouvrira jamais (Phase 16). */}
              <p className="text-xs text-[var(--ink-soft)] leading-relaxed">
                {t.loyaltyConsentNotice}{" "}
                <Link href="/confidentialite" className="underline text-[var(--laiton)]">
                  {t.loyaltyPrivacyLink}
                </Link>
              </p>
              <label className="block text-sm text-[var(--encre)]">
                {t.loyaltyPhoneLabel}
                <input
                  type="tel"
                  value={loyaltyPhone}
                  onChange={(e) => setLoyaltyPhone(e.target.value)}
                  onBlur={() => checkLoyaltyStatus(loyaltyPhone)}
                  placeholder={t.loyaltyPhonePlaceholder}
                  className="mt-1 w-full text-sm bg-white border border-[var(--line)] rounded-xl px-3 py-2"
                />
              </label>
              <label className="block text-sm text-[var(--encre)]">
                {t.loyaltyBirthDateLabel}
                <input
                  type="date"
                  value={loyaltyBirthDate}
                  onChange={(e) => setLoyaltyBirthDate(e.target.value)}
                  onBlur={() => checkLoyaltyStatus(loyaltyPhone)}
                  className="mt-1 w-full text-sm bg-white border border-[var(--line)] rounded-xl px-3 py-2"
                />
              </label>
              {loyaltyFirstVisit && (
                <p className="text-sm text-[var(--laiton)] pt-1 flex items-center gap-1.5">
                  <GiftIcon className="w-4 h-4 shrink-0" />
                  {t.loyaltyFirstVisit}
                </p>
              )}
              {loyaltyStatus && <div className="pt-1">{renderLoyaltyCard(loyaltyStatus)}</div>}
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
                <span className="text-[10.5px] font-bold uppercase tracking-[0.16em] text-[var(--laiton)] whitespace-nowrap">
                  {menuCategoryLabel(category, locale)}
                </span>
                <span className="h-px flex-1 bg-[var(--line)]" />
              </h2>
              {menu.filter((m) => m.category === category).map((item, i) => renderItem(item, i))}
            </section>
          ))
        )}

        {cartLines.length > 0 && (
          <div className="fixed bottom-0 left-0 right-0 bg-[var(--espresso)] pt-[14px] px-4 pb-[18px]">
            <div className="max-w-md mx-auto">
              {/* Posé seulement quand un plat est à partager : sinon c'est une
                  question de plus entre le client et sa commande. */}
              {cartLines.some((l) => l.shared) && (
                <label className="flex items-center justify-between gap-2 text-sm text-[rgba(246,239,221,.85)] mb-3">
                  {t.dinersLabel}
                  <input
                    type="number"
                    min={2}
                    max={12}
                    value={convives}
                    onChange={(e) => setConvives(Math.max(2, Math.min(12, Number(e.target.value) || 2)))}
                    className="w-12 bg-transparent border border-[rgba(246,239,221,.28)] rounded-lg px-[10px] py-[3px] text-center tabular-nums text-[rgba(246,239,221,.9)]"
                  />
                </label>
              )}
              {restaurant.ramadan_mode_enabled && restaurant.iftar_time && (
                <label className="flex items-center gap-2 text-sm text-[rgba(246,239,221,.85)] mb-3">
                  <input
                    type="checkbox"
                    checked={preOrderForIftar}
                    onChange={(e) => setPreOrderForIftar(e.target.checked)}
                    className="accent-[var(--laiton)]"
                  />
                  <MoonIcon className="w-4 h-4 shrink-0 text-[var(--laiton)]" />
                  {t.preorderCheckboxLabel(formatTime(restaurant.iftar_time))}
                </label>
              )}
              <div className="flex justify-between items-center gap-3" data-visite="client-panier">
                <div>
                  <p className="text-[10.5px] font-semibold uppercase tracking-[0.12em] text-[rgba(246,239,221,.6)]">
                    {t.cartItemsCount(cartLines.reduce((s, l) => s + l.quantity, 0))}
                  </p>
                  <p className={`${lalezar.className} text-[26px] leading-none tabular-nums text-[var(--semoule)] mt-0.5`}>
                    {formatAmount(total)} {t.currency}
                  </p>
                </div>
                <button
                  onClick={validateOrder}
                  disabled={sending}
                  className="shrink-0 bg-[var(--harissa)] text-[var(--semoule)] rounded-full px-[22px] py-[14px] text-[14.5px] font-bold shadow-[0_2px_0_var(--harissa-pressed)] active:shadow-none active:translate-y-[2px] disabled:opacity-50"
                >
                  {sending ? t.sending : t.validateOrder}
                </button>
              </div>
            </div>
          </div>
        )}

        {suggestFor && (
          <div
            className={`fixed left-0 right-0 bg-[var(--semoule-raised)] border-t border-[var(--line)] p-[14px] shadow-[0_-8px_20px_rgba(36,24,17,.06)] ${
              cartLines.length > 0 ? "bottom-[132px]" : "bottom-0"
            }`}
          >
            <div className="max-w-md mx-auto">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-bold text-[var(--encre)]">{t.suggestionTitle(suggestFor.name)}</p>
                  <p className="text-[11.5px] text-[var(--ink-soft)]">{t.suggestionHint}</p>
                </div>
                <button
                  onClick={() => setSuggestFor(null)}
                  aria-label={t.closeErrorAria}
                  className="text-[var(--ink-soft)] shrink-0"
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
                      <span className="flex-1 text-sm text-[var(--ink-soft)]">
                        <span className="text-[var(--encre)]">{item.name}</span> · {formatAmount(item.price)} {t.currency}
                      </span>
                      <button
                        onClick={() => addToCart(item, true)}
                        className="text-[12.5px] font-semibold px-[14px] py-2 rounded-[10px] bg-[var(--harissa)] text-[var(--semoule)]"
                      >
                        {t.suggestionAdd}
                      </button>
                    </li>
                  ))}
              </ul>
              <button
                onClick={() => setSuggestFor(null)}
                className="mt-3 text-sm text-[var(--ink-soft)] underline"
              >
                {t.suggestionDismiss}
              </button>
            </div>
          </div>
        )}

        {optionChooserFor && (
          <div
            className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-0 sm:p-4"
            role="dialog"
            aria-modal="true"
            onClick={() => setOptionChooserFor(null)}
          >
            <div
              className="w-full max-w-md max-h-[85vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl bg-[var(--semoule-raised)] p-[16px]"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-[15px] font-bold text-[var(--encre)]">{t.optionsChooseTitle(optionChooserFor.name)}</p>
                <button
                  onClick={() => setOptionChooserFor(null)}
                  aria-label={t.closeErrorAria}
                  className="text-[var(--ink-soft)] shrink-0"
                >
                  ✕
                </button>
              </div>

              <div className="mt-3 space-y-4">
                {optionChooserFor.option_groups.map((group) => (
                  <div key={group.id}>
                    <div className="flex items-baseline justify-between gap-2">
                      <p className="text-sm font-semibold text-[var(--encre)]">{group.name}</p>
                      <p className="text-xs text-[var(--ink-soft)] shrink-0">
                        {t.optionsGroupHint(group.min_select, group.max_select)}
                      </p>
                    </div>
                    <div className="mt-1.5 space-y-1.5">
                      {group.options.map((option) => {
                        const selected = (chooserSelection[group.id] ?? []).includes(option.id);
                        return (
                          <button
                            key={option.id}
                            type="button"
                            onClick={() => toggleChooserOption(group, option.id)}
                            aria-pressed={selected}
                            className={`w-full flex items-center justify-between gap-2 rounded-xl border px-3 py-2.5 text-sm text-start transition-colors ${
                              selected
                                ? "bg-[var(--harissa)] text-[var(--semoule)] border-[var(--harissa)]"
                                : "border-[var(--line)] bg-white text-[var(--encre)]"
                            }`}
                          >
                            <span>{option.name}</span>
                            {option.price_delta > 0 && (
                              <span className="tabular-nums shrink-0">
                                +{formatAmount(option.price_delta)} {t.currency}
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 flex items-center justify-between gap-3">
                <span className="text-[17px] font-bold tabular-nums text-[var(--encre)]">
                  {formatAmount(chooserTotalPrice(optionChooserFor))} {t.currency}
                </span>
                <button
                  onClick={confirmOptionChooser}
                  disabled={!chooserSatisfiesMinimums(optionChooserFor)}
                  className="shrink-0 bg-[var(--harissa)] text-[var(--semoule)] rounded-full px-[22px] py-[14px] text-[14.5px] font-bold disabled:opacity-50"
                >
                  {t.optionsConfirmAdd}
                </button>
              </div>
              <button
                onClick={() => setOptionChooserFor(null)}
                className="mt-3 text-sm text-[var(--ink-soft)] underline"
              >
                {t.optionsCancelChoice}
              </button>
            </div>
          </div>
        )}

        {googleReviewModal}

        {cartLines.length === 0 && cartClearedNotice && (
          <div className="fixed bottom-0 left-0 right-0 bg-[var(--semoule-raised)] border-t border-[var(--line)] p-4">
            <div className="max-w-md mx-auto flex items-center gap-3">
              <EmptyCartIllustration className="w-10 h-10 shrink-0 text-[var(--ink-faint)]" />
              <p className="text-sm text-[var(--ink-soft)] flex-1">{t.cartClearedNotice}</p>
              <button
                onClick={() => setCartClearedNotice(false)}
                aria-label={t.closeErrorAria}
                className="text-[var(--ink-faint)] shrink-0"
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
