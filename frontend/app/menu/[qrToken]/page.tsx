"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import * as m from "motion/react-m";
import { AnimatePresence } from "motion/react";
import { cairo, lalezar } from "@/lib/fonts";
import { COURBE, DUREE, TRANSITION } from "@/lib/mouvement";
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
  ModificationLine,
  Order,
  OrderItemPayload,
  OrderStatus,
  RestaurantPublic,
  Table,
} from "@/lib/api";
import { urlBase64ToUint8Array } from "@/lib/webPush";
import { toLocalizedMessage } from "@/lib/errors";
import { formatAmount, parseAmountInput } from "@/lib/currency";
import { currentMarket } from "@/lib/market";
import { useReconnectingSocket } from "@/lib/useReconnectingSocket";
import { localeSwitchLabel, useLocale } from "@/lib/i18n/useLocale";
import { menuCategoryLabel } from "@/lib/menuCategories";
import { duree, elapsedSeconds, useHorloge } from "@/lib/duree";
import SplitBill from "@/components/SplitBill";
import IdentityPrompt from "@/components/IdentityPrompt";
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
  PencilIcon,
  ChevronLeftIcon,
  ClockIcon,
  LockIcon,
  BagIcon,
} from "@/components/icons";
import Skeleton from "@/components/ui/Skeleton";
import Button from "@/components/ui/Button";
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
  // Clé d'appareil de qui a ajouté cette ligne, et son prénom au moment de
  // l'ajout (identité de table, ROADMAP.md §Override) — c'est ce qui permet
  // à deux personnes de commander le même plat sans que ça fasse une seule
  // ligne partagée, et de n'afficher le retrait que sur ses propres plats.
  addedByKey: string;
  addedByName: string;
};

/**
 * Une ligne de la commande en cours de révision (fenêtre 1 : édition directe
 * tant que la commande est en attente de confirmation). Volontairement plus
 * simple que `CartLine` : pas d'options ni de partage détaillé par convive —
 * une commande déjà envoyée qui a besoin de ça se recommande plutôt que de
 * se rééditer en détail.
 */
type EditLine = {
  menuItemId: number;
  name: string;
  unitPrice: number;
  quantity: number;
  notes: string;
  isShared: boolean;
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

// --- Identité de table (ROADMAP.md §Override, extension) ------------------
// Un prénom par téléphone, conservé tant que ce navigateur revoit ce QR — une
// reconnexion ou un rafraîchissement de page reprend la même clé plutôt que
// d'en réclamer une nouvelle place à la table (même principe que
// `loyaltyPhoneStorageKey`, jamais purgé non plus).

type StoredIdentity = { deviceKey: string; name: string };

function identityStorageKey(qrToken: string): string {
  return `resto-qr-menu:identity:${qrToken}`;
}

function readStoredIdentity(qrToken: string): StoredIdentity | null {
  const raw = localStorage.getItem(identityStorageKey(qrToken));
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed?.deviceKey === "string" && typeof parsed?.name === "string") return parsed;
  } catch {
    // Contenu illisible : traité comme "pas encore d'identité", la modale
    // la redemandera plutôt que de planter sur un JSON invalide.
  }
  return null;
}

function storeIdentity(qrToken: string, identity: StoredIdentity): void {
  localStorage.setItem(identityStorageKey(qrToken), JSON.stringify(identity));
}

// --- Panier de table partagé (ROADMAP.md §Override — panier synchronisé
// multi-appareils, puis identité de table) ---------------------------------
// Le serveur est la seule source de vérité (voir orders/table_cart.py côté
// backend) : ces fonctions traduisent entre SA représentation par fil
// (OrderItemPayload, une ligne par plat ET par personne) et celle du panier
// local (CartLine, qui garde l'objet MenuItem complet pour l'affichage).
//
// La clé du panier local n'est plus le seul `menu_item_id` : deux personnes
// qui commandent le même plat doivent obtenir deux lignes distinctes, une par
// personne — `cartKey` compose donc l'id de l'article et la clé d'appareil de
// qui l'a ajouté (chaîne vide = appareil sans identité déclarée, même repli
// que côté serveur).

function cartKey(menuItemId: number, addedByKey: string): string {
  return `${menuItemId}:${addedByKey}`;
}

function cartLineToWireItem(itemId: number, line: CartLine): OrderItemPayload {
  return {
    menu_item_id: itemId,
    quantity: line.quantity,
    notes: line.note || null,
    is_shared: line.shared,
    // Envoyé indépendamment de `shared` : assigner un plat à un convive reste
    // possible même pour un plat non coché "à partager" (ROADMAP.md §Override
    // 2026-09-08) — les deux réglages ne se conditionnent plus l'un l'autre.
    shared_with: line.sharedWith,
    from_suggestion: line.fromSuggestion,
    selected_option_ids: line.selectedOptions.map((o) => o.optionId),
    added_by_key: line.addedByKey || null,
    added_by_name: line.addedByName || null,
  };
}

// `null` quand l'article a disparu de la carte entre-temps (rupture, ou carte
// changée) : mieux vaut ignorer la ligne que planter le rendu du panier
// partagé pour tout le monde à la table.
function wireItemToCartLine(wireItem: OrderItemPayload, menu: MenuItem[]): CartLine | null {
  const item = menu.find((m) => m.id === wireItem.menu_item_id);
  if (!item) return null;
  const selectedOptions: SelectedOption[] = (wireItem.selected_option_ids ?? []).flatMap((optionId) => {
    for (const group of item.option_groups) {
      const option = group.options.find((o) => o.id === optionId);
      if (option) {
        return [{ optionId, groupName: group.name, optionName: option.name, priceDelta: option.price_delta }];
      }
    }
    return [];
  });
  return {
    item,
    quantity: wireItem.quantity,
    note: wireItem.notes ?? "",
    shared: wireItem.is_shared ?? false,
    sharedWith: wireItem.shared_with ?? [],
    fromSuggestion: wireItem.from_suggestion ?? false,
    selectedOptions,
    addedByKey: wireItem.added_by_key ?? "",
    addedByName: wireItem.added_by_name ?? "",
  };
}

function cartToWireRecord(cart: Record<string, CartLine>): Record<string, OrderItemPayload> {
  const wire: Record<string, OrderItemPayload> = {};
  for (const [key, line] of Object.entries(cart)) {
    wire[key] = cartLineToWireItem(line.item.id, line);
  }
  return wire;
}

function sameWireItem(a: OrderItemPayload, b: OrderItemPayload): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

// --- Paiement par personne (identité de table, ROADMAP.md §Override,
// extension) ----------------------------------------------------------------
// Prévisualisation cliente de la part de chacun — même algorithme que
// SplitBill.tsx (mode "par plat") et orders/split.py::compute_shares côté
// serveur, qui reste seul à faire foi au moment de payer : ce calcul-ci ne
// sert qu'à AFFICHER un montant avant de cliquer, jamais à le facturer.

function computeSharesLocal(order: Order, names: string[]): number[] {
  const n = names.length;
  const totals = new Array(n).fill(0);
  for (const item of order.items) {
    const lineTotal = item.unit_price * item.quantity;
    let targets: number[];
    if (item.is_shared) {
      const places = item.shared_with.filter((p) => p >= 1 && p <= n);
      targets = places.length ? places : Array.from({ length: n }, (_, i) => i + 1);
    } else if (item.added_by_name && names.includes(item.added_by_name)) {
      targets = [names.indexOf(item.added_by_name) + 1];
    } else {
      targets = Array.from({ length: n }, (_, i) => i + 1);
    }
    const part = lineTotal / targets.length;
    for (const p of targets) totals[p - 1] += part;
  }
  return totals;
}

// Le dernier convive encore non réglé absorbe l'arrondi — même règle que
// côté serveur (orders/split.py::compute_payable_amount) : il paie
// exactement ce qu'il reste, jamais sa part théorique.
function myPayableAmount(order: Order, rosterNames: string[], myName: string): number {
  const paidNames = new Set(order.payments.filter((p) => p.status === "paid").map((p) => p.payer_name));
  const names = rosterNames.includes(myName) ? rosterNames : [...rosterNames, myName];
  const remaining = names.filter((n) => !paidNames.has(n));
  if (remaining.length <= 1) return order.amount_remaining;
  const totals = computeSharesLocal(order, names);
  const myIndex = names.indexOf(myName);
  return myIndex >= 0 ? totals[myIndex] : order.amount_remaining;
}

export default function MenuPage({ params }: { params: { qrToken: string } }) {
  const { qrToken } = params;
  const { t, locale, toggleLocale } = useLocale();

  const [table, setTable] = useState<Table | null>(null);
  const [restaurant, setRestaurant] = useState<RestaurantPublic | null>(null);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [cart, setCart] = useState<Record<string, CartLine>>({});
  const [cartOrderId, setCartOrderId] = useState<string | null>(null);
  // Récapitulatif façon panier d'appli de livraison, ouvert AVANT de valider
  // : le bandeau bas n'ouvre plus que ça, la validation elle-même se joue
  // depuis cet écran (bouton "Retour à la carte" pour continuer à composer).
  const [showCartReview, setShowCartReview] = useState(false);
  // Article en cours de configuration dans le sélecteur d'options (France,
  // MARCHE_FRANCE.md phase F5/A2) — un seul à la fois, comme suggestFor.
  const [optionChooserFor, setOptionChooserFor] = useState<MenuItem | null>(null);
  // Modale d'avis Google post-paiement (Phase D1bis).
  const [showGoogleReview, setShowGoogleReview] = useState(false);
  // Catégorie surlignée dans la barre collante (Phase D2 de ROADMAP_DESIGN.md)
  // — stocke l'ancre (`categoryAnchor(category)`), pas le nom brut : c'est ce
  // que l'IntersectionObserver lit directement sur `section.id`.
  const [activeCategoryAnchor, setActiveCategoryAnchor] = useState<string | null>(null);
  // Position et dimensions du repère qui glisse sous la catégorie active.
  // Mesurées et non calculées : les libellés changent de longueur avec la
  // langue (« À emporter » n'a pas la largeur de « Vins »).
  const listeCategoriesRef = useRef<HTMLUListElement>(null);
  const [repereCategorie, setRepereCategorie] = useState<{
    x: number;
    y: number;
    largeur: number;
    hauteur: number;
  } | null>(null);
  // groupId -> ids des options choisies dans ce groupe, pendant la composition.
  const [chooserSelection, setChooserSelection] = useState<Record<number, number[]>>({});
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
  // Révision de la commande envoyée — panier séparé de `cart` : celui-ci sert
  // à composer une commande, celui-là à en réviser une déjà envoyée, et les
  // deux ne doivent jamais se marcher dessus. `editIntent` distingue les deux
  // fenêtres : "self" (édition directe, tant que PENDING_CONFIRMATION) écrit
  // immédiatement ; "request" (commande déjà confirmée, jusqu'en cuisine)
  // passe par une demande que le serveur valide ligne par ligne.
  const [editingOrder, setEditingOrder] = useState(false);
  const [editIntent, setEditIntent] = useState<"self" | "request">("self");
  const [editItems, setEditItems] = useState<Record<number, EditLine>>({});
  // "Ajouter d'autres plats" rouvre la carte complète par-dessus le récap de
  // la commande en cours d'édition, plutôt qu'une liste repliée sur place
  // (décision de Wassim, 2026-09-09 — ROADMAP_DESIGN.md) : un seul état de
  // navigation, `editIncrement`/`editDecrement` restent l'unique mutation.
  const [browsingCarteInEdit, setBrowsingCarteInEdit] = useState(false);
  // Photo de la quantité au moment d'ouvrir l'écran d'édition — jamais
  // modifiée ensuite : sert uniquement à afficher "ancien → nouveau" quand le
  // client change une quantité (barré/nouveau), demandé explicitement pour
  // qu'une ligne réduite ou ajoutée se voie d'un coup d'œil.
  const [originalQuantities, setOriginalQuantities] = useState<Record<number, number>>({});
  const [savingEdit, setSavingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  // Résultat de la dernière demande de modification résolue par le serveur —
  // transitoire (pas besoin de survivre à un rafraîchissement, contrairement
  // à `pending_modification_request` qui vient du backend) : juste de quoi
  // afficher "Réponse du serveur" une fois, ligne par ligne.
  const [lastResolution, setLastResolution] = useState<ModificationLine[] | null>(null);
  const [tipInput, setTipInput] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [paying, setPaying] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [preOrderForIftar, setPreOrderForIftar] = useState(false);
  const [waiterCallState, setWaiterCallState] = useState<"idle" | "calling" | "called">("idle");
  const [waiterCallError, setWaiterCallError] = useState<string | null>(null);
  // Identité de table (ROADMAP.md §Override, extension) : qui commande sous
  // quel prénom, un par appareil — remplace l'ancien "vous êtes combien à
  // table ?" posé une fois pour toute la tablée. `roster` est dans l'ordre où
  // chacun a rejoint (voir tables/roster.py côté backend), ce qui lui laisse
  // jouer le même rôle que les anciennes places 1..N pour le sélecteur
  // "Partagé entre" et le calculateur d'addition (SplitBill).
  const [myIdentity, setMyIdentity] = useState<StoredIdentity | null>(null);
  const [showIdentityPrompt, setShowIdentityPrompt] = useState(false);
  // Une seule fois par visite : sans ça, une reconnexion du canal de la
  // table (recharge, coupure réseau) qui retombe sur cet effet AVANT que le
  // stockage n'ait rattrapé le "Passer"/prénom qu'on vient de soumettre
  // rouvrait la modale à un client qui venait tout juste d'y répondre —
  // reproduit en revenant sur "commander à nouveau" juste après validation
  // (retour QA) : c'est censé rester le même convive, pas en redemander un.
  const identityPromptedRef = useRef(false);
  const [roster, setRoster] = useState<{ key: string; name: string }[]>([]);
  const [addingGuest, setAddingGuest] = useState(false);
  const [guestNameInput, setGuestNameInput] = useState("");
  const myDeviceKey = myIdentity?.deviceKey ?? "";
  // Nombre de personnes à table : entièrement dérivé du roster, jamais un état
  // séparé. Le roster compte les convives réels — ceux qui ont scanné et ceux
  // ajoutés à la main par « + Ajouter » — donc une table d'un seul convive
  // affiche un seul convive. L'ancien compteur manuel (« Personnes à table »,
  // hérité de `PartyPrompt` quand la taille était déclarée à la main) avait un
  // plancher à 2 qui inventait un « Personne 2 » fantôme dans « Pour qui ? »,
  // et se faisait de toute façon écraser dès qu'un autre convive scannait.
  const convives = Math.max(1, Math.min(12, roster.length));
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
          <StampIcon className={`w-4 h-4 shrink-0 ${complete ? "text-[var(--laiton-on-espresso-text)]" : "text-[var(--laiton-text)]"}`} />
          {complete ? (
            <h3 className={`${lalezar.className} text-[21px] leading-none text-[var(--laiton-text)]`}>
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
              complete ? "text-[var(--laiton-on-espresso-text)]" : "text-[var(--laiton-text)]"
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
    const returnedPaymentId = Number(params.get("payment_id"));
    window.history.replaceState(null, "", window.location.pathname);

    if (konnectResult === "fail") {
      setPaymentError(t.paymentFailedRetry);
      return;
    }
    if (konnectResult !== "success" || !returnedOrderId || !returnedOrderToken || !returnedPaymentId) return;

    api
      .checkCardPayment(returnedOrderId, returnedPaymentId, returnedOrderToken)
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
      // Servie ET réglée seulement : servie mais impayée doit rester
      // atteignable, sinon un client qui regarde sa commande passer "servie"
      // en direct perd l'accès à son addition avant d'avoir pu payer (même
      // condition que le chemin de rechargement, plus haut dans ce fichier).
      if (msg.status === "cancelled" || (msg.status === "served" && trackedOrder.payment_status === "paid")) {
        localStorage.removeItem(lastOrderStorageKey(qrToken));
      }
    }
    // Le paiement vient d'être confirmé (carte, cash ou terminal, encaissé
    // depuis CET appareil ou un autre appareil suivant la même commande) —
    // on relit la commande plutôt qu'un simple changement de statut local :
    // `payment_method`/`tip_amount` peuvent n'avoir jamais été connus de CET
    // appareil (paiement carte demandé et réglé ailleurs en une seule étape,
    // sans "order.payment_requested" intermédiaire).
    if (msg.event === "order.payment_confirmed" && trackedOrder && msg.order_id === trackedOrder.id && orderToken) {
      api.getOrder(trackedOrder.id, orderToken).then(setTrackedOrder).catch(() => {});
    }
    // Un autre appareil vient de demander à payer (cash, terminal, ou carte
    // en ligne) — l'écran de suivi sait déjà afficher `payment_status ===
    // "pending"`, encore faut-il que CET appareil apprenne le changement
    // sans rafraîchir, sinon rien n'empêche un deuxième convive de demander
    // un paiement concurrent par un autre moyen.
    if (msg.event === "order.payment_requested" && trackedOrder && msg.order_id === trackedOrder.id && orderToken) {
      api.getOrder(trackedOrder.id, orderToken).then(setTrackedOrder).catch(() => {});
    }
    // Dès qu'un serveur est affecté (prise en charge ou confirmation), le
    // client sait qui s'occupe de sa table sans avoir à demander.
    if (msg.event === "order.staff_assigned" && trackedOrder && msg.order_id === trackedOrder.id) {
      setTrackedOrder((prev) => (prev ? { ...prev, taken_by_staff_name: msg.staff_name } : prev));
    }
    // Le serveur a répondu à la demande de modification (fenêtre 2) — on
    // relit la commande pour ses vraies lignes/total (les lignes acceptées
    // ont été appliquées côté backend) et on garde le détail ligne par ligne
    // du message pour l'afficher : "accepté"/"refusé" ne se devine pas
    // depuis le nouveau contenu seul.
    if (msg.event === "order.modification_resolved" && trackedOrder && msg.order_id === trackedOrder.id && orderToken) {
      setLastResolution(msg.lines);
      api.getOrder(trackedOrder.id, orderToken).then(setTrackedOrder).catch(() => {});
    }
    // Un autre appareil suivant la même commande (panier de table partagé —
    // plusieurs convives valident ensemble puis suivent tous ce même
    // `order_id`) vient de la modifier — on relit ses items/total, sinon ce
    // deuxième appareil reste sur l'ancien contenu jusqu'à un rafraîchissement
    // manuel de la page.
    if (msg.event === "order.items_updated" && trackedOrder && msg.order_id === trackedOrder.id && orderToken) {
      api.getOrder(trackedOrder.id, orderToken).then(setTrackedOrder).catch(() => {});
    }
    // Un autre appareil vient de soumettre une demande de modification
    // (fenêtre 2) — on relit la commande pour que `pending_modification_request`
    // désactive ici aussi le bouton "modifier", sinon ce deuxième appareil
    // peut soumettre une demande concurrente et tomber sur
    // MODIFICATION_REQUEST_ALREADY_PENDING sans jamais comprendre pourquoi.
    if (msg.event === "order.modification_requested" && trackedOrder && msg.order_id === trackedOrder.id && orderToken) {
      api.getOrder(trackedOrder.id, orderToken).then(setTrackedOrder).catch(() => {});
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
  // Depuis le chantier « panier synchronisé multi-appareils », il porte aussi
  // le panier partagé de la table (`orders/table_cart.py` côté backend).
  const tableWsUrl = restaurant ? wsUrl(`/ws/table/${restaurant.id}/${qrToken}`) : null;
  // Dernier état confirmé par le serveur, pour ne diffuser QUE ce qui a
  // changé (voir l'effet de synchronisation plus bas) — `null` tant qu'aucun
  // instantané n'est arrivé, pour ne jamais rejouer un panier local sur un
  // serveur qui n'a pas encore parlé.
  const lastSyncedWireRef = useRef<Record<string, OrderItemPayload> | null>(null);
  // Vrai seulement entre l'envoi d'un "cart.validate" et sa réponse — sert
  // uniquement à limiter le filet de sécurité ci-dessous à CE cas précis,
  // sans réagir à une coupure du canal table pendant qu'une validation REST
  // (repli hors connexion) est par ailleurs en cours, sans rapport avec lui.
  const pendingSocketValidateRef = useRef(false);
  const { status: tableSocketStatus, send: sendTableAction } = useReconnectingSocket(tableWsUrl, (msg) => {
    if (msg.event === "waiter_call.resolved") {
      setWaiterCallState("idle");
    } else if (msg.event === "roster.updated") {
      const people: { key: string; name: string }[] = msg.people ?? [];
      setRoster(people);
      // Le serveur vient peut-être de résoudre un prénom laissé vide en
      // "PersoN" (voir tables/roster.py::set_name) — on le reprend en local
      // pour qu'une reconnexion réannonce ce nom résolu, jamais une chaîne
      // vide qui redemanderait un nouveau "PersoN" à chaque fois.
      setMyIdentity((prev) => {
        if (!prev) return prev;
        const mine = people.find((p) => p.key === prev.deviceKey);
        if (mine && mine.name !== prev.name) {
          const updated: StoredIdentity = { deviceKey: prev.deviceKey, name: mine.name };
          storeIdentity(qrToken, updated);
          return updated;
        }
        return prev;
      });
    } else if (msg.event === "cart.updated") {
      const lines: OrderItemPayload[] = msg.lines ?? [];
      const rebuilt: Record<string, CartLine> = {};
      const wire: Record<string, OrderItemPayload> = {};
      for (const wireItem of lines) {
        const line = wireItemToCartLine(wireItem, menu);
        if (line) {
          const key = cartKey(wireItem.menu_item_id, wireItem.added_by_key ?? "");
          rebuilt[key] = line;
          // Re-encodé via `cartLineToWireItem` plutôt que de garder le
          // `wireItem` brut du serveur : ce dernier peut porter un champ en
          // moins ou en plus (version du serveur en avance ou en retard sur
          // ce build du client, ex. déploiement en cours) sans que la ligne
          // elle-même diffère vraiment. En comparant plus tard deux objets
          // construits par la MÊME fonction, `sameWireItem` ne peut plus voir
          // un écart qui n'existe que dans la forme du JSON — sans ça, un
          // champ qui ne fait l'aller-retour dans aucun sens (constaté avec
          // un serveur qui ignorait encore `added_by_key`/`added_by_name`)
          // faisait échouer la comparaison à chaque rendu, et l'effet de
          // synchronisation sortant rejouait le même `cart.set` en boucle
          // infinie (des milliers de messages/seconde, audit QA).
          wire[key] = cartLineToWireItem(wireItem.menu_item_id, line);
        }
      }
      // Marqué comme déjà synchronisé AVANT `setCart` : sans ça, l'effet de
      // synchronisation sortant verrait ce même changement au rendu suivant
      // et le renverrait aussitôt au serveur, qui le rediffuserait — une
      // boucle d'échos inutiles (sans conséquence sur les données, mais du
      // trafic WebSocket qui n'a aucune raison d'exister).
      lastSyncedWireRef.current = wire;
      setCart(rebuilt);
    } else if (msg.event === "cart.validated") {
      // N'importe quel appareil de la table a pu valider — pas forcément
      // celui-ci : tous doivent basculer sur le suivi de la même commande.
      pendingSocketValidateRef.current = false;
      // Le serveur a déjà vidé le panier partagé (`pop_all`) avant de
      // diffuser cet événement — qu'on soit celui qui a validé ou un autre
      // appareil de la table, notre copie locale est désormais périmée. Sans
      // ça, revenir au menu via "commander à nouveau" réaffichait encore le
      // total de la commande qu'on vient de valider au lieu de repartir de
      // zéro (retour QA). Réf mise à jour AVANT `setCart`, même raison que
      // pour "cart.updated" ci-dessus : sinon l'effet de synchronisation
      // sortant croit que chaque ligne vient d'être retirée et le renvoie
      // aussitôt au serveur.
      lastSyncedWireRef.current = {};
      setCart({});
      // `public_token` ne revient JAMAIS de `getOrder` (Phase 12.2 : il n'est
      // renvoyé qu'à la création, `OrderCreatedOut`) — c'est celui que porte
      // cet événement qui fait foi, pas un champ de la réponse HTTP.
      const publicToken: string = msg.public_token;
      api
        .getOrder(msg.order_id, publicToken)
        .then((order) => {
          storeTrackedOrderRef(qrToken, order.id, publicToken);
          setTrackedOrder(order);
          setOrderToken(publicToken);
          setCartOrderId(null);
          setPreOrderForIftar(false);
          setShowCartReview(false);
          setShowCelebration(true);
          setSending(false);
        })
        .catch(() => setSending(false));
    } else if (msg.event === "cart.error") {
      pendingSocketValidateRef.current = false;
      setSending(false);
      if (msg.code === "ITEM_UNAVAILABLE" || msg.code === "ITEM_NOT_FOUND") {
        const staleId = msg.menu_item_id as number | undefined;
        if (staleId) {
          // Retire les lignes de CET article pour tout le monde à la table —
          // il peut y en avoir plusieurs, une par personne qui l'a commandé.
          setCart((prev) => {
            const next = { ...prev };
            for (const key of Object.keys(next)) {
              if (next[key].item.id === staleId) delete next[key];
            }
            return next;
          });
        }
        api.getMenuByToken(qrToken).then(setMenu).catch(() => {});
      }
      setOrderError(toLocalizedMessage(new ApiError(msg.code, msg.message, msg), locale));
    }
  });

  // Répercute chaque changement du panier local vers le panier partagé de la
  // table — jamais l'inverse ici (voir `cart.updated` ci-dessus) : le serveur
  // reste la seule source de vérité, cet effet ne fait que lui signaler ce
  // qui a changé depuis le dernier envoi. Tant que le canal n'est pas
  // connecté, ne fait STRICTEMENT rien : le panier reste purement local,
  // comportement identique à avant ce chantier (repli automatique).
  useEffect(() => {
    if (tableSocketStatus !== "connected") {
      // Une reconnexion redemandera un instantané complet au serveur — vider
      // la référence évite de croire, après coup, qu'un ancien état était
      // déjà connu de lui.
      lastSyncedWireRef.current = null;
      return;
    }
    const currentWire = cartToWireRecord(cart);
    const previousWire = lastSyncedWireRef.current ?? {};
    const changedKeys = new Set([...Object.keys(currentWire), ...Object.keys(previousWire)]);
    for (const key of changedKeys) {
      const current = currentWire[key];
      const previous = previousWire[key];
      if (current && (!previous || !sameWireItem(current, previous))) {
        sendTableAction({ action: "cart.set", ...current });
      } else if (!current && previous) {
        // Ligne retirée : le serveur la retrouve par (menu_item_id,
        // added_by_key) — sans reprendre exactement la même clé, ce message
        // viderait la ligne "anonyme" au lieu de la sienne (table_cart.py).
        sendTableAction({
          action: "cart.set",
          menu_item_id: previous.menu_item_id,
          added_by_key: previous.added_by_key ?? null,
          quantity: 0,
        });
      }
    }
    lastSyncedWireRef.current = currentWire;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cart, tableSocketStatus]);

  // Dès que le canal de la table est connecté : soit ce téléphone a déjà une
  // identité pour ce QR (rafraîchissement, reconnexion) et la réannonce sans
  // rien demander, soit il n'en a pas et la modale la recueille. Lu
  // directement dans le stockage plutôt que depuis l'état `myIdentity` (qui
  // pourrait ne pas encore avoir fini de se charger au même rendu).
  useEffect(() => {
    if (tableSocketStatus !== "connected") return;
    const stored = readStoredIdentity(qrToken);
    if (stored) {
      setMyIdentity(stored);
      sendTableAction({ action: "identity.set", device_key: stored.deviceKey, name: stored.name });
    } else if (!identityPromptedRef.current) {
      identityPromptedRef.current = true;
      setShowIdentityPrompt(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tableSocketStatus]);

  function confirmIdentity(name: string) {
    const deviceKey = genererIdPanier();
    const identity: StoredIdentity = { deviceKey, name: name.trim() };
    storeIdentity(qrToken, identity);
    setMyIdentity(identity);
    setShowIdentityPrompt(false);
    sendTableAction({ action: "identity.set", device_key: deviceKey, name: identity.name });
  }

  function addGuestToRoster() {
    const name = guestNameInput.trim();
    if (name) sendTableAction({ action: "identity.add_guest", name });
    setGuestNameInput("");
    setAddingGuest(false);
  }

  // Filet de sécurité : si la connexion tombe pendant qu'une validation est
  // en vol (message envoyé, mais ni "cart.validated" ni "cart.error" jamais
  // revenu), le bouton « Valider » ne doit pas rester bloqué indéfiniment —
  // une commande qui n'arrive jamais à cause d'un blocage d'écran est aussi
  // grave qu'une commande refusée par une vraie erreur.
  useEffect(() => {
    if (pendingSocketValidateRef.current && tableSocketStatus !== "connected") {
      pendingSocketValidateRef.current = false;
      setSending(false);
      setOrderError(toLocalizedMessage(new ApiError("CONNECTION_LOST", "connection lost", {}), locale));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tableSocketStatus]);

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

  // Mesure du repère qui glisse sous la catégorie active. `offsetLeft`/
  // `offsetTop` se mesurent depuis le bord intérieur de la bordure du
  // conteneur, et le repère est ancré au même endroit par `left-0 top-0` :
  // les deux coïncident. Ancrer explicitement est indispensable — sans
  // `left`, un élément absolu part de sa position statique, donc après le
  // padding, et le décalage se cumule.
  useEffect(() => {
    if (!listeCategoriesRef.current) return;

    function mesurer() {
      const ul = listeCategoriesRef.current;
      if (!ul) return;
      const rendues = Array.from(new Set(menu.map((item) => item.category)));
      const ancre = activeCategoryAnchor ?? (rendues.length > 0 ? categoryAnchor(rendues[0]) : null);
      if (!ancre) return setRepereCategorie(null);
      const cible = ul.querySelector<HTMLElement>(`[data-ancre="${ancre}"]`);
      if (!cible) return setRepereCategorie(null);
      // La hauteur est mesurée aussi : elle dépend des métriques de la police.
      setRepereCategorie({
        x: cible.offsetLeft,
        y: cible.offsetTop,
        largeur: cible.offsetWidth,
        hauteur: cible.offsetHeight,
      });
    }

    mesurer();
    // Les polices arrivent après le premier rendu : sans cette remesure, le
    // repère garde la largeur du texte en police de repli.
    document.fonts?.ready.then(mesurer).catch(() => {});
    window.addEventListener("resize", mesurer);
    return () => window.removeEventListener("resize", mesurer);
  }, [menu, activeCategoryAnchor, locale]);

  // Chacun paie SA PART, jamais l'addition entière (identité de table,
  // ROADMAP.md §Override, extension paiement par personne) — `myDeviceKey`/
  // `myIdentity.name` identifient qui paie, le montant réel est recalculé et
  // figé côté serveur (orders/split.py), jamais celui affiché ici qui n'est
  // qu'une prévisualisation (voir `myPayableAmount`).
  async function payByCard() {
    if (!trackedOrder) return;
    setPaying(true);
    setPaymentError(null);
    const tip = parseAmountInput(tipInput);
    try {
      if (!orderToken) return;
      const updated = await api.payByCard(
        trackedOrder.id, myDeviceKey, myIdentity?.name ?? "", tip, orderToken, customerEmail.trim() || undefined
      );
      // Restaurant ayant connecté son propre Konnect/Stripe (modèle direct,
      // 2026-08-19) : rediriger pour régler, cette part reste "pending"
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
      const tip = parseAmountInput(tipInput);
      const updated = await api.requestCashPayment(
        trackedOrder.id, myDeviceKey, myIdentity?.name ?? "", tip, orderToken, customerEmail.trim() || undefined
      );
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
      const tip = parseAmountInput(tipInput);
      const updated = await api.requestCardTerminalPayment(
        trackedOrder.id, myDeviceKey, myIdentity?.name ?? "", tip, orderToken, customerEmail.trim() || undefined
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
    // Toujours SA PROPRE ligne (identité de table, ROADMAP.md §Override) :
    // un appareil ne peut jamais incrémenter le plat d'un autre convive, même
    // si l'article est le même — d'où la clé composée plutôt que `item.id`
    // seul (voir `cartKey`).
    const key = cartKey(item.id, myDeviceKey);
    setCart((prev) => {
      const existing = prev[key];
      return {
        ...prev,
        [key]: {
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
          addedByKey: myDeviceKey,
          addedByName: myIdentity?.name ?? "",
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
      const proposable = suggestedIds.filter((id) => !cart[cartKey(id, myDeviceKey)]);
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

  // Prend la clé composée du panier (voir `cartKey`), jamais le seul id du
  // plat : appelée avec la clé de SA PROPRE ligne à chaque site d'appel — le
  // panier de table (écran de révision) le garantit en ne montrant le retrait
  // que sur les lignes dont `addedByKey === myDeviceKey`.
  function removeFromCart(key: string) {
    setCart((prev) => {
      const next = { ...prev };
      if (next[key] && next[key].quantity > 1) {
        next[key] = { ...next[key], quantity: next[key].quantity - 1 };
      } else {
        delete next[key];
      }
      return next;
    });
  }

  function setNote(key: string, note: string) {
    setCart((prev) => (prev[key] ? { ...prev, [key]: { ...prev[key], note } } : prev));
  }

  // --- Révision de la commande envoyée (fenêtres 1 et 2) --------------------

  function seedEditItemsFromOrder(): Record<number, EditLine> {
    const seeded: Record<number, EditLine> = {};
    for (const item of trackedOrder?.items ?? []) {
      seeded[item.menu_item_id] = {
        menuItemId: item.menu_item_id,
        name: item.menu_item_name,
        unitPrice: item.unit_price,
        quantity: item.quantity,
        notes: item.notes ?? "",
        isShared: item.is_shared,
      };
    }
    return seeded;
  }

  function snapshotOriginalQuantities(seeded: Record<number, EditLine>) {
    const snapshot: Record<number, number> = {};
    for (const line of Object.values(seeded)) snapshot[line.menuItemId] = line.quantity;
    setOriginalQuantities(snapshot);
  }

  // Fenêtre 1 : tant que rien n'a encore été confirmé, la commande s'édite
  // directement, sans validation.
  function startEditingOrder() {
    if (!trackedOrder) return;
    setEditIntent("self");
    const seeded = seedEditItemsFromOrder();
    setEditItems(seeded);
    snapshotOriginalQuantities(seeded);
    setEditError(null);
    setBrowsingCarteInEdit(false);
    setEditingOrder(true);
  }

  // Fenêtre 2 : commande déjà confirmée (jusqu'en cuisine) — composer ici ne
  // fait qu'esquisser la demande, `sendModificationRequest` l'envoie.
  function startRequestingModification() {
    if (!trackedOrder) return;
    setEditIntent("request");
    const seeded = seedEditItemsFromOrder();
    setEditItems(seeded);
    snapshotOriginalQuantities(seeded);
    setEditError(null);
    setBrowsingCarteInEdit(false);
    setEditingOrder(true);
  }

  function editIncrement(item: MenuItem) {
    setEditItems((prev) => {
      const existing = prev[item.id];
      return {
        ...prev,
        [item.id]: {
          menuItemId: item.id,
          name: item.name,
          unitPrice: item.price,
          quantity: (existing?.quantity ?? 0) + 1,
          notes: existing?.notes ?? "",
          isShared: existing?.isShared ?? false,
        },
      };
    });
  }

  function editDecrement(menuItemId: number) {
    setEditItems((prev) => {
      const existing = prev[menuItemId];
      if (!existing) return prev;
      if (existing.quantity <= 1) {
        const next = { ...prev };
        delete next[menuItemId];
        return next;
      }
      return { ...prev, [menuItemId]: { ...existing, quantity: existing.quantity - 1 } };
    });
  }

  function editSetNote(menuItemId: number, notes: string) {
    setEditItems((prev) => (prev[menuItemId] ? { ...prev, [menuItemId]: { ...prev[menuItemId], notes } } : prev));
  }

  function editSetShared(menuItemId: number, isShared: boolean) {
    setEditItems((prev) =>
      prev[menuItemId] ? { ...prev, [menuItemId]: { ...prev[menuItemId], isShared } } : prev
    );
  }

  const editTotal = Object.values(editItems).reduce((sum, l) => sum + l.unitPrice * l.quantity, 0);

  async function saveOrderEdits() {
    if (!trackedOrder || !orderToken) return;
    const items = Object.values(editItems).map((l) => ({
      menu_item_id: l.menuItemId,
      quantity: l.quantity,
      notes: l.notes || null,
      is_shared: l.isShared,
    }));
    setSavingEdit(true);
    setEditError(null);
    try {
      const updated = await api.updateOrderItems(trackedOrder.id, orderToken, items);
      setTrackedOrder(updated);
      setEditingOrder(false);
    } catch (e) {
      if (e instanceof ApiError && e.code === "ORDER_NOT_MODIFIABLE") {
        // Le serveur vient de confirmer pile pendant l'édition : la fenêtre 1
        // vient de se refermer, mais rien de ce que le client vient de
        // composer n'est perdu — ça part comme demande de modification
        // (fenêtre 2) au lieu d'un échec sec qui l'obligerait à recommencer.
        setEditIntent("request");
        await sendModificationRequest(items);
        return;
      }
      setEditError(toLocalizedMessage(e, locale));
    } finally {
      setSavingEdit(false);
    }
  }

  async function sendModificationRequest(itemsOverride?: OrderItemPayload[]) {
    if (!trackedOrder || !orderToken) return;
    const items =
      itemsOverride ??
      Object.values(editItems).map((l) => ({
        menu_item_id: l.menuItemId,
        quantity: l.quantity,
        notes: l.notes || null,
        is_shared: l.isShared,
      }));
    setSavingEdit(true);
    setEditError(null);
    try {
      const request = await api.requestModification(trackedOrder.id, orderToken, items);
      setTrackedOrder((prev) => (prev ? { ...prev, pending_modification_request: request } : prev));
      setLastResolution(null);
      setEditingOrder(false);
    } catch (e) {
      setEditError(toLocalizedMessage(e, locale));
    } finally {
      setSavingEdit(false);
    }
  }

  function setShared(key: string, shared: boolean) {
    // Cocher "à partager" pré-sélectionne sa propre place, quand elle est
    // connue : on est forcément de la partie sur un plat qu'on est en train
    // d'ajouter soi-même — sans ça, partager avec un voisin de table exigeait
    // de se cocher SOI-même en plus, un tap qu'on oublie facilement.
    // `sharedWith` n'est en revanche plus remis à zéro quand on décoche :
    // l'assignation à un convive reste un réglage indépendant de la case "à
    // partager" (ROADMAP.md §Override 2026-09-08) — décocher ne doit pas
    // faire perdre à qui un plat était destiné.
    const myPlace = roster.findIndex((p) => p.key === myDeviceKey) + 1;
    setCart((prev) =>
      prev[key]
        ? {
            ...prev,
            [key]: {
              ...prev[key],
              shared,
              sharedWith:
                shared && prev[key].sharedWith.length === 0 && myPlace > 0
                  ? [myPlace]
                  : prev[key].sharedWith,
            },
          }
        : prev
    );
  }

  function toggleConvive(key: string, place: number) {
    setCart((prev) => {
      const ligne = prev[key];
      if (!ligne) return prev;
      const sharedWith = ligne.sharedWith.includes(place)
        ? ligne.sharedWith.filter((p) => p !== place)
        : [...ligne.sharedWith, place].sort((a, b) => a - b);
      return { ...prev, [key]: { ...ligne, sharedWith } };
    });
  }

  // Panier de TOUTE la table — c'est lui qui valide, et lui que montre l'écran
  // de révision (identité de table, ROADMAP.md §Override : "seule la page du
  // panier... reste synchronisée et englobe toute la commande de tout le
  // monde"). `myCartLines` n'est qu'une vue filtrée, pour le bandeau bas de la
  // carte — qui ne doit refléter que ce que CE téléphone a lui-même ajouté.
  const cartLines = Object.values(cart);
  const myCartLines = cartLines.filter((l) => l.addedByKey === myDeviceKey);
  // Prix de base + suppléments des options choisies (France, F5/A2) — jamais
  // relu ailleurs que dans le panier : le serveur refige tout à la création
  // de la commande (voir orders/service.py::create_order côté backend).
  function lineUnitPrice(line: CartLine): number {
    return line.item.price + line.selectedOptions.reduce((sum, o) => sum + o.priceDelta, 0);
  }
  const total = cartLines.reduce((sum, l) => sum + lineUnitPrice(l) * l.quantity, 0);
  const myTotal = myCartLines.reduce((sum, l) => sum + lineUnitPrice(l) * l.quantity, 0);

  async function validateOrder() {
    if (!table || cartLines.length === 0) return;
    setSending(true);
    setOrderError(null);

    // Panier synchronisé : quand le canal de la table est connecté, valider
    // porte sur l'état tenu par le SERVEUR (potentiellement enrichi par
    // d'autres appareils), jamais sur une copie locale qui pourrait avoir
    // pris du retard. La suite (basculer sur le suivi de la commande) se
    // joue dans le gestionnaire de messages ci-dessus, sur "cart.validated" —
    // qui arrive à cet appareil comme à tous les autres de la table.
    if (tableSocketStatus === "connected") {
      pendingSocketValidateRef.current = true;
      // Même `client_order_id` que le repli REST ci-dessous : sans lui, une
      // coupure entre la création serveur de la commande et le retour de
      // "cart.validated" (voir le filet de sécurité plus haut) laissait un
      // second clic sur "Valider" recréer une commande identique — le panier
      // partagé n'avait aucune protection contre la relecture, contrairement
      // au panier local (Phase 19.2, cf. `genererIdPanier`).
      sendTableAction({ action: "cart.validate", client_order_id: cartOrderId });
      return;
    }

    const payload: CreateOrderPayload = {
      qr_token: qrToken,
      items: cartLines.map((l) => cartLineToWireItem(l.item.id, l)),
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
      setShowCartReview(false);
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
        setShowCartReview(false);
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
              !cart[cartKey(item.id, myDeviceKey)] &&
              !trackedOrder.items.some((line) => line.menu_item_id === item.id)
          )
          .slice(0, 3)
      : [];

  function addSuggestionAndOrderAgain(item: MenuItem) {
    addToCart(item, true);
    orderAgain();
  }

  // "Commander séparément" un ajout refusé (fenêtre 2, réponse partielle) —
  // même mécanique que addSuggestionAndOrderAgain : la cuisine ne peut rien
  // rattacher à la commande déjà en cours, mais rien n'empêche d'en ouvrir
  // une nouvelle pour cet article précis.
  function orderDeclinedLineSeparately(line: ModificationLine) {
    const menuItem = menu.find((m) => m.id === line.menu_item_id);
    if (!menuItem) return;
    addToCart(menuItem, false);
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
        <p className="text-[var(--harissa-text)] mb-4">{loadError}</p>
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
        <div className="flex items-center justify-center gap-1 text-[var(--laiton-text)]">
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
            <WifiOffIcon className="w-[18px] h-[18px] shrink-0 text-[var(--laiton-text)]" />
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
    if (editingOrder) {
      const editCategories = Array.from(new Set(menu.map((m) => m.category)));
      const editItemCount = Object.values(editItems).reduce((sum, l) => sum + l.quantity, 0);

      function editCategoryAnchor(category: string): string {
        return `edit-cat-${encodeURIComponent(category).replace(/%/g, "")}`;
      }

      // Fiche plat de la carte rouverte depuis l'édition — même contenu que
      // `renderItem` (photo ou VignetteCategorie, description, prix) mais
      // volontairement plus simple (pas de piment/halal/allergènes, pas de
      // sélecteur d'options : `EditLine` n'a aucun champ pour ça aujourd'hui,
      // chantier à part) et branchée sur `editIncrement`/`editDecrement`
      // plutôt que sur le panier `cart` de la composition initiale.
      function renderCarteItemForEdit(item: MenuItem) {
        const photo = mediaUrl(item.image_url);
        const quantity = editItems[item.id]?.quantity ?? 0;
        return (
          <div key={item.id} className="flex items-center gap-2.5 bg-white border border-[var(--line)] rounded-2xl p-2.5">
            <div className="relative shrink-0 w-11 h-11 rounded-xl overflow-hidden">
              {photo ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={photo} alt={item.name} loading="lazy" className="w-full h-full object-cover" />
              ) : (
                <VignetteCategorie category={item.category} />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[13.5px] font-semibold truncate">{item.name}</div>
              {item.description && (
                <div className="text-[11px] text-[var(--ink-soft)] truncate mt-0.5">{item.description}</div>
              )}
              <div className="text-[12px] font-bold tabular-nums text-[var(--harissa-text)] mt-1">
                {formatAmount(item.price)} {t.currency}
              </div>
            </div>
            {quantity > 0 ? (
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => editDecrement(item.id)}
                  aria-label={t.removeFromCartAria(item.name)}
                  className="w-[30px] h-[30px] rounded-full border border-[var(--line)] bg-white transition-transform active:scale-90"
                >
                  −
                </button>
                <span className="min-w-[16px] text-center text-[13.5px] font-bold tabular-nums">{quantity}</span>
                <button
                  onClick={() => editIncrement(item)}
                  aria-label={t.addToCartAria(item.name)}
                  className="w-[30px] h-[30px] rounded-full text-[16px] leading-none shrink-0 bg-[var(--harissa)] text-[var(--semoule)] transition-transform active:scale-90"
                >
                  +
                </button>
              </div>
            ) : (
              <button
                onClick={() => editIncrement(item)}
                aria-label={t.addToCartAria(item.name)}
                className="w-[30px] h-[30px] rounded-full text-[16px] leading-none shrink-0 bg-[var(--harissa)] text-[var(--semoule)] transition-transform active:scale-90"
              >
                +
              </button>
            )}
          </div>
        );
      }

      if (browsingCarteInEdit) {
        return (
          <div dir={dir} className={`min-h-screen bg-[var(--semoule)] pb-[104px] ${wrapperClassName ?? ""}`}>
            <div className="pt-[20px] px-[18px] max-w-md mx-auto">
              <button
                onClick={() => setBrowsingCarteInEdit(false)}
                className="inline-flex items-center gap-1 text-[13px] font-semibold text-[var(--ink-soft)] py-1.5"
              >
                <ChevronLeftIcon className="w-4 h-4 shrink-0" />
                {t.backToOrderButton}
              </button>
              <h1 className={`${lalezar.className} mt-2 text-[22px] leading-tight text-center text-[var(--encre)]`}>
                {t.browseCarteTitle}
              </h1>
              <p className="mt-1 text-[12.5px] text-center text-[var(--ink-soft)]">
                {t.orderSubtitle(table.label, trackedOrder.id)}
              </p>
            </div>

            <nav className="sticky top-0 z-10 mt-4 bg-[rgba(246,239,221,.95)] backdrop-blur border-y border-[var(--line)]">
              <ul className="flex gap-2 overflow-x-auto px-[18px] py-2.5 max-w-md mx-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                {editCategories.map((category) => (
                  <li key={category}>
                    <a
                      href={`#${editCategoryAnchor(category)}`}
                      className="inline-block whitespace-nowrap rounded-full border border-[var(--line)] bg-[var(--semoule-raised)] text-[var(--encre)] px-[13px] py-[6px] text-[12.5px] font-semibold"
                    >
                      {menuCategoryLabel(category, locale)}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>

            <div className="px-[18px] pt-4 max-w-md mx-auto">
              {editCategories.map((category) => (
                <section key={category} id={editCategoryAnchor(category)} className="mb-6 scroll-mt-24">
                  <p className="mb-2.5 text-[12px] font-semibold text-[var(--ink-soft)]">
                    {menuCategoryLabel(category, locale)}
                  </p>
                  <div className="space-y-2">
                    {menu
                      .filter((m) => m.category === category && m.is_available)
                      .map((item) => renderCarteItemForEdit(item))}
                  </div>
                </section>
              ))}
            </div>

            {editItemCount > 0 && (
              <div className="fixed bottom-0 inset-x-0 z-20 px-[18px] pb-[18px] pt-3">
                <div className="max-w-md mx-auto flex items-center justify-between gap-3 bg-[var(--encre)] text-[var(--semoule)] rounded-2xl px-4 py-3 shadow-[0_-10px_24px_-10px_rgba(0,0,0,.3)]">
                  <span className="text-[12.5px] font-semibold text-[rgba(246,239,221,.8)]">
                    {t.orderPanelCount(editItemCount)}
                  </span>
                  <button
                    onClick={() => setBrowsingCarteInEdit(false)}
                    className="text-[12.5px] font-bold bg-[var(--harissa)] text-[var(--semoule)] rounded-xl px-[14px] py-2.5 whitespace-nowrap"
                  >
                    {t.backToOrderButton} — {formatAmount(editTotal)} {t.currency}
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      }

      return (
        <div dir={dir} className={`min-h-screen bg-[var(--semoule)] pt-[20px] px-[18px] pb-[26px] max-w-md mx-auto ${wrapperClassName ?? ""}`}>
          <button
            onClick={() => setEditingOrder(false)}
            className="inline-flex items-center gap-1 text-[13px] font-semibold text-[var(--ink-soft)] py-1.5"
          >
            <ChevronLeftIcon className="w-4 h-4 shrink-0" />
            {t.editOrderCancel}
          </button>

          <h1 className={`${lalezar.className} mt-2 text-[22px] leading-tight text-center text-[var(--encre)]`}>
            {editIntent === "request" ? t.requestModificationButton : t.editOrderTitle}
          </h1>
          <p className="mt-1 text-[12.5px] text-center text-[var(--ink-soft)]">
            {t.orderSubtitle(table.label, trackedOrder.id)}
          </p>

          <div className="mt-4 flex items-start gap-2 rounded-xl py-[11px] px-3 text-[12.5px] leading-[1.45] bg-[rgba(184,134,46,.12)] text-[#8a6420] border border-[rgba(184,134,46,.55)]">
            <ClockIcon className="w-[14px] h-[14px] shrink-0 mt-0.5" />
            <span>{editIntent === "request" ? t.requestEditBanner : t.modifyOrderHint}</span>
          </div>

          {editError && (
            <p className="mt-3 text-sm text-[var(--harissa-text)] bg-[rgba(214,64,30,.1)] border border-[rgba(214,64,30,.55)] rounded-xl p-3">
              {editError}
            </p>
          )}

          {Object.keys(editItems).length > 0 && (
            <div className="mt-6 bg-[var(--semoule-raised)] border border-[var(--line-strong)] rounded-2xl p-3.5">
              <div className="flex items-center gap-2 mb-3">
                <BagIcon className="w-[15px] h-[15px] shrink-0 text-[var(--laiton-text)]" />
                <p className="text-[10.5px] font-bold uppercase tracking-[0.14em] text-[var(--laiton-text)]">
                  {t.myOrderTitle}
                </p>
              </div>
              <div className="space-y-2.5">
                {Object.values(editItems).map((line) => (
                  <div key={line.menuItemId} className="bg-white border border-[var(--line)] rounded-xl p-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[14.5px] font-semibold">{line.name}</span>
                    </div>
                    <div className="mt-2 flex items-center justify-between">
                      <span className="text-[14.5px] font-bold tabular-nums text-[var(--harissa-text)]">
                        {formatAmount(line.unitPrice)} {t.currency}
                      </span>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={() => editDecrement(line.menuItemId)}
                          aria-label={t.removeFromCartAria(line.name)}
                          className="w-[34px] h-[34px] rounded-full border border-[var(--line)] bg-white transition-transform active:scale-90"
                        >
                          −
                        </button>
                        <span className="inline-flex items-baseline justify-center gap-1 min-w-[16px] text-center text-[14px] font-bold tabular-nums">
                          {(originalQuantities[line.menuItemId] ?? 0) !== line.quantity && (
                            <span className="text-[12px] font-semibold text-[var(--ink-faint)] line-through">
                              {originalQuantities[line.menuItemId] ?? 0}
                            </span>
                          )}
                          {line.quantity}
                        </span>
                        <button
                          onClick={() => {
                            const menuItem = menu.find((m) => m.id === line.menuItemId);
                            if (menuItem) editIncrement(menuItem);
                          }}
                          aria-label={t.addToCartAria(line.name)}
                          className="w-[34px] h-[34px] rounded-full text-[19px] leading-none shadow-sm transition-transform active:scale-90 bg-[var(--harissa)] text-[var(--semoule)]"
                        >
                          +
                        </button>
                      </div>
                    </div>
                    <input
                      type="text"
                      value={line.notes}
                      onChange={(e) => editSetNote(line.menuItemId, e.target.value)}
                      placeholder={t.notePlaceholder}
                      className="mt-2.5 w-full text-xs bg-white border border-[var(--line)] rounded-[10px] px-[10px] py-2 placeholder:text-[var(--ink-soft)]"
                    />
                    <label className="mt-2 flex items-center gap-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={line.isShared}
                        onChange={(e) => editSetShared(line.menuItemId, e.target.checked)}
                        className="sr-only"
                      />
                      <span
                        className="w-[18px] h-[18px] rounded-[5px] border-[1.5px] flex items-center justify-center shrink-0"
                        style={{
                          backgroundColor: line.isShared ? "var(--menthe)" : "#fff",
                          borderColor: line.isShared ? "var(--menthe)" : "var(--line-strong)",
                        }}
                      >
                        {line.isShared && (
                          <svg viewBox="0 0 24 24" className="w-[11px] h-[11px]" fill="none" stroke="var(--semoule)" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
                            <path d="M4 12l5 5L20 6" />
                          </svg>
                        )}
                      </span>
                      <UtensilsIcon className="w-4 h-4 shrink-0 text-[var(--ink-soft)]" />
                      <span className="text-[var(--encre)]">{t.sharedCheckboxLabel}</span>
                    </label>
                  </div>
                ))}
              </div>
              <div className="flex justify-between mt-3 pt-2.5 border-t border-[var(--line)] text-[12px] font-bold text-[var(--ink-soft)]">
                <span>{t.orderPanelCount(editItemCount)}</span>
                <span className="text-[var(--encre)] tabular-nums">
                  {formatAmount(editTotal)} {t.currency}
                </span>
              </div>
            </div>
          )}

          <button
            onClick={() => setBrowsingCarteInEdit(true)}
            className="mt-4 w-full flex items-center justify-center gap-2 border-[1.5px] border-dashed border-[var(--line-strong)] bg-[var(--semoule)] rounded-xl py-3 text-[13.5px] font-bold text-[var(--ink-soft)] transition-colors active:bg-white"
          >
            {t.browseCarteButton}
          </button>

          <div className="mt-6 bg-[var(--semoule-raised)] border border-[var(--line)] rounded-2xl p-3.5">
            <div className="flex justify-between items-baseline mb-0.5">
              <span className="text-[13px] font-semibold text-[var(--ink-soft)]">
                {editIntent === "request" ? t.requestEditNewTotalLabel : t.total}
              </span>
              <span className="text-[19px] font-bold tabular-nums text-[var(--encre)]">
                {formatAmount(editTotal)} {t.currency}
              </span>
            </div>
            {editIntent === "request" && (
              <p className="mb-2.5 text-[11px] text-[var(--ink-faint)]">
                {t.requestEditCurrentTotal(`${formatAmount(trackedOrder.total_amount)} ${t.currency}`)}
              </p>
            )}
            <button
              onClick={editIntent === "request" ? () => sendModificationRequest() : saveOrderEdits}
              disabled={savingEdit || Object.keys(editItems).length === 0}
              className="w-full bg-[var(--harissa)] text-[var(--semoule)] rounded-xl py-3 font-bold text-[14.5px] shadow-[0_2px_0_var(--harissa-pressed)] active:shadow-none active:translate-y-[2px] disabled:opacity-50"
            >
              {savingEdit ? t.sending : editIntent === "request" ? t.requestEditSend : t.editOrderSave}
            </button>
            {editIntent === "request" && (
              <p className="mt-2 text-[11px] text-center text-[var(--ink-soft)] leading-[1.4]">
                {t.requestEditSubcopy}
              </p>
            )}
          </div>
        </div>
      );
    }

    const currentDisplayIndex = displayStepIndex(trackedOrder.status as StepStatus);
    const cancelled = trackedOrder.status === "cancelled";
    // Fenêtre 2 : la commande est confirmée mais pas encore prête — même
    // fenêtre que l'étape affichée "En cuisine" (displayStepIndex regroupe
    // déjà SENT_TO_KITCHEN et IN_PREPARATION), plus CONFIRMED pour le cas
    // rare où le serveur confirme sans enchaîner tout de suite sur l'envoi.
    const kitchenModificationWindow = (
      ["confirmed", "sent_to_kitchen", "in_preparation"] as OrderStatus[]
    ).includes(trackedOrder.status);
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
              <p className="mt-1 text-[12.5px] font-semibold text-center text-[var(--laiton-text)] tabular-nums">
                {t.orderElapsed(duree(secondes))}
              </p>
            );
          })()}

        {/* Même `data-visite` que le bouton d'appel de la carte, plus bas : les
            deux écrans ne coexistent jamais (celui-ci sort par un retour
            anticipé), et la visite trouve sa cible sur l'un comme sur l'autre. */}
        <div className="mt-4 flex justify-center gap-2 flex-wrap" data-visite="client-appel">
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
          {/* Fenêtre 1 : rien n'a encore été confirmé, la commande s'édite
              directement. */}
          {trackedOrder.status === "pending_confirmation" && (
            <button
              onClick={startEditingOrder}
              className="min-h-[44px] inline-flex items-center gap-1.5 text-xs font-semibold border border-[var(--line)] bg-white text-[var(--encre)] rounded-full px-3 py-[11px]"
            >
              <PencilIcon className="w-[14px] h-[14px] shrink-0" />
              {t.modifyOrderButton}
            </button>
          )}
          {/* Fenêtre 2 : commande déjà confirmée, jusqu'en cuisine — toute
              modification passe désormais par une demande. */}
          {kitchenModificationWindow && (
            <button
              onClick={startRequestingModification}
              disabled={!!trackedOrder.pending_modification_request}
              className="min-h-[44px] inline-flex items-center gap-1.5 text-xs font-semibold border border-[var(--line)] bg-white text-[var(--encre)] rounded-full px-3 py-[11px] disabled:opacity-70"
            >
              {trackedOrder.pending_modification_request ? (
                t.requestSentButton
              ) : (
                <>
                  <PencilIcon className="w-[14px] h-[14px] shrink-0" />
                  {t.requestModificationButton}
                </>
              )}
            </button>
          )}
        </div>
        {waiterCallError && <p className="mt-2 text-sm text-center text-[var(--harissa-text)]">{waiterCallError}</p>}
        {trackedOrder.status === "pending_confirmation" && (
          <p className="mt-1.5 flex items-center justify-center gap-1 text-[11.5px] text-[var(--ink-soft)] text-center">
            <ClockIcon className="w-3 h-3 shrink-0" />
            {t.modifyOrderHint}
          </p>
        )}
        {kitchenModificationWindow && !trackedOrder.pending_modification_request && (
          <p className="mt-1.5 flex items-center justify-center gap-1 text-[11.5px] text-[var(--ink-soft)] text-center">
            <ClockIcon className="w-3 h-3 shrink-0" />
            {t.requestModificationHint}
          </p>
        )}
        {trackedOrder.pending_modification_request && (
          <div className="mt-4 flex items-start gap-2 rounded-xl py-[11px] px-3 text-[12.5px] leading-[1.45] bg-[rgba(184,134,46,.12)] text-[#8a6420] border border-[rgba(184,134,46,.55)]">
            <ClockIcon className="w-[14px] h-[14px] shrink-0 mt-0.5" />
            <span>{t.requestPendingBanner}</span>
          </div>
        )}
        {lastResolution && (
          <div className="mt-4 border border-[var(--line)] bg-[var(--semoule-raised)] rounded-xl p-3">
            <p className="mb-2 text-[10.5px] font-bold uppercase tracking-[0.14em] text-[var(--laiton-text)]">
              {t.requestOutcomeTitle}
            </p>
            <div className="space-y-2">
              {lastResolution.map((line) => (
                <div key={line.id} className="flex items-start gap-2">
                  <span
                    className="w-[18px] h-[18px] rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5"
                    style={{
                      backgroundColor: line.status === "accepted" ? "var(--menthe)" : "var(--ink-soft)",
                      color: "var(--semoule)",
                    }}
                  >
                    {line.status === "accepted" ? "✓" : "✗"}
                  </span>
                  <div>
                    <span className="text-[13px] text-[var(--encre)]">
                      <strong>{line.menu_item_name}</strong>
                      {" — "}
                      {line.status === "accepted" ? t.requestLineAccepted : t.requestLineDeclined}
                    </span>
                    {/* Un retrait refusé n'a aucune suite possible (l'article
                        reste tel quel) — seul un ajout refusé peut encore
                        partir comme commande séparée. */}
                    {line.status === "declined" && line.previous_quantity === 0 && (
                      <button
                        onClick={() => orderDeclinedLineSeparately(line)}
                        className="mt-1 block text-[12px] font-semibold text-[var(--harissa-text)] underline"
                      >
                        {t.requestOrderSeparately}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!cancelled && trackedOrder.scheduled_for && (
          <p className="mt-4 text-sm text-center bg-[rgba(184,134,46,.12)] text-[#8a6420] border border-[rgba(184,134,46,.55)] rounded-xl py-2 px-3 flex items-center justify-center gap-1.5">
            <MoonIcon className="w-4 h-4 shrink-0 text-[var(--laiton-text)]" />
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
            <FlameIcon className="w-[15px] h-[15px] shrink-0 mt-0.5 text-[var(--laiton-text)]" />
            <span>{culturalFacts[culturalFactIndex]}</span>
          </div>
        )}

        <div className="mt-8 border-t border-[var(--line)] pt-[14px]">
          <div className="flex items-baseline justify-between mb-2">
            <p className="text-[10.5px] font-bold uppercase tracking-[0.14em] text-[var(--laiton-text)]">
              {t.orderDetailsTitle}
            </p>
            {trackedOrder.items_updated_at && (
              <span className="text-[11px] text-[var(--ink-faint)] italic">
                {t.itemsUpdatedAt(formatTime(trackedOrder.items_updated_at))}
              </span>
            )}
          </div>
          <ul className="text-[13px] leading-[1.75] text-[var(--ink-soft)] space-y-0">
            {trackedOrder.items.map((it) => (
              <li key={it.id}>
                {it.quantity}× {it.menu_item_name}
                {it.is_shared && (
                  <span className="text-[var(--laiton-text)] inline-flex items-center gap-1 align-middle">
                    · <UtensilsIcon className="w-3.5 h-3.5 shrink-0" /> {t.sharedTag}
                  </span>
                )}
                {it.options.length > 0 && (
                  <span className="text-[var(--ink-faint)]"> — {it.options.map((o) => o.option_name).join(", ")}</span>
                )}
                {it.notes && <span className="text-[var(--ink-faint)]"> — {it.notes}</span>}
                {/* Qui a commandé le plat, et pour qui il est — les deux sur la
                    même ligne. Le récap est collé à la section paiement
                    (`paymentTitle`, ~70 lignes plus bas) : c'est l'écran où la
                    table demande « c'est qui qui a pris le couscous ? », et
                    `shared_with` y décide de la part de chacun
                    (orders/split.py::compute_shares). Les cacher là est
                    précisément le pire endroit pour les perdre.
                    Prénom brut, sans « Vous · » comme au panier : le récap
                    n'expose pas `added_by_key`, et comparer les prénoms se
                    tromperait sur deux convives homonymes. */}
                {(it.added_by_name || it.shared_with.length > 0) && (
                  <span className="block text-legende text-[var(--ink-soft)]">
                    {[
                      it.added_by_name,
                      it.shared_with.length > 0
                        ? t.cartForWhom(it.shared_with.map(personLabel).join(" · "))
                        : null,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                )}
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
            <p className="text-[10.5px] font-bold uppercase tracking-[0.14em] text-[var(--laiton-text)] mb-3">
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
                {/* Qui a payé quoi (identité de table, ROADMAP.md §Override,
                    extension paiement par personne) — reste visible une fois
                    la commande entièrement réglée, comme un reçu. */}
                {trackedOrder.payments.length > 1 && (
                  <div className="mt-2 space-y-1">
                    {trackedOrder.payments.map((p) => (
                      <div key={p.id} className="flex justify-between text-[12.5px] text-[var(--ink-soft)]">
                        <span>{p.payer_name || t.personLabel(1)}</span>
                        <span className="tabular-nums">
                          {formatAmount(p.amount + p.tip_amount)} {t.currency}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
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

            {trackedOrder.payment_status !== "paid" && (() => {
              const rosterNames = roster.map((p) => p.name);
              const myName = myIdentity?.name ?? "";
              const paidPayments = trackedOrder.payments.filter((p) => p.status === "paid");
              const paidNames = new Set(paidPayments.map((p) => p.payer_name));
              const remainingNames = rosterNames.filter((n) => !paidNames.has(n));
              const myPayment = trackedOrder.payments.find((p) => p.payer_key === myDeviceKey);
              const myAmount = myPayableAmount(trackedOrder, rosterNames, myName);
              return (
                <div className="space-y-3">
                  {paidPayments.length > 0 && (
                    <div className="rounded-xl p-3 bg-[var(--semoule-raised)] border border-[var(--line)] space-y-1.5">
                      {paidPayments.map((p) => (
                        <p key={p.id} className="text-[12.5px] text-[var(--menthe)] font-semibold">
                          ✓ {t.paidByPerson(p.payer_name || t.personLabel(1))} ({formatAmount(p.amount + p.tip_amount)}{" "}
                          {t.currency})
                        </p>
                      ))}
                      <p className="text-[12.5px] text-[var(--ink-soft)]">
                        {t.remainingAmountLabel} {formatAmount(trackedOrder.amount_remaining)} {t.currency}
                        {remainingNames.length > 0 && ` — ${remainingNames.join(", ")}`}
                      </p>
                    </div>
                  )}

                  {paymentError && (
                    <div className="text-sm text-[var(--harissa-text)] bg-[rgba(214,64,30,.1)] border border-[rgba(214,64,30,.55)] rounded-xl p-3">
                      {paymentError}
                    </div>
                  )}
                  <SplitBill
                    order={trackedOrder}
                    t={t}
                    partySize={roster.length || undefined}
                    partyNames={rosterNames}
                  />

                  {myPayment?.status === "paid" ? (
                    <p className="text-sm font-semibold text-[var(--menthe)] bg-[rgba(31,107,79,.1)] border border-[rgba(31,107,79,.45)] rounded-xl p-3">
                      ✓ {t.myShareAlreadyPaidMessage}
                    </p>
                  ) : myPayment ? (
                    <p className="text-sm text-[#8a6420] bg-[rgba(184,134,46,.12)] border border-[rgba(184,134,46,.55)] rounded-xl p-3">
                      {myPayment.method === "card_terminal"
                        ? t.cardTerminalPendingMessage(myPayment.amount + myPayment.tip_amount)
                        : t.cashPendingMessage(myPayment.amount + myPayment.tip_amount)}
                    </p>
                  ) : (
                    <>
                      <p className="text-sm font-semibold text-[var(--encre)]">{t.myShareTitle}</p>
                      <div>
                        <p className="text-sm text-[var(--ink-soft)] mb-1.5">{t.tipLabel}</p>
                        <div className="flex gap-2">
                          {[0, 0.05, 0.1].map((pct) => {
                            const amount = Number((myAmount * pct).toFixed(currentMarket.currency.decimals));
                            const selected = (tipInput === "" && pct === 0) || Number(tipInput) === amount;
                            return (
                              <button
                                key={pct}
                                type="button"
                                onClick={() => setTipInput(pct === 0 ? "" : String(amount))}
                                className={`flex-1 rounded-[10px] py-[9px] text-center ${
                                  selected
                                    ? "border border-[var(--harissa)] bg-[var(--creme)] text-[var(--harissa-text)] text-[12.5px] font-bold"
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
                      <div className="flex justify-between text-[15px] font-bold text-[var(--encre)] pt-2 border-t border-[var(--line)]">
                        <span>{t.totalToPayLabel}</span>
                        <span className="tabular-nums">
                          {formatAmount(myAmount + parseAmountInput(tipInput))} {t.currency}
                        </span>
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
                    </>
                  )}
                </div>
              );
            })()}
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

  // Avant tout défilement, `activeCategoryAnchor` vaut null et aucune pastille
  // n'était surlignée : la barre collante n'indiquait donc pas où on se trouve
  // à l'ouverture de la carte, précisément quand on en a le plus besoin. On
  // retombe sur la première catégorie, qui est bien celle qu'on regarde.
  const ancreCategorieActive =
    activeCategoryAnchor ?? (categories.length > 0 ? categoryAnchor(categories[0]) : null);

  function categoryAnchor(category: string): string {
    // Ancre stable et sûre en URL : les catégories sont saisies par le
    // restaurant, donc accentuées et espacées.
    return `cat-${encodeURIComponent(category).replace(/%/g, "")}`;
  }

  // Prénom déclaré à la place de "Personne N", quand donné — même repli que
  // SplitBill.tsx. `roster` est dans l'ordre où chacun a rejoint la table,
  // ce qui lui donne le même rôle que l'ancien `party.names` positionnel.
  function personLabel(place: number): string {
    return roster[place - 1]?.name || t.personLabel(place);
  }

  function renderItem(item: MenuItem, index = 0) {
    // Un plat en rupture reste sur la carte, barré : le faire disparaître
    // laissait le client chercher un plat qu'il avait vu la minute d'avant, ou
    // qu'un voisin de table est en train de manger. Le dire est plus honnête
    // que l'escamoter (retour du premier service).
    const rupture = !item.is_available;
    const photo = mediaUrl(item.image_url);
    // Uniquement SA PROPRE ligne (identité de table) : la carte ne doit
    // refléter que ce que CE téléphone a lui-même ajouté, jamais ce que les
    // autres convives ont commandé depuis le leur.
    const ligne = cart[cartKey(item.id, myDeviceKey)];
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
        // `group` : la photo réagit au survol de toute la carte, pas seulement
        // d'elle-même. Le survol est conditionné à `hover: hover` — sur un
        // téléphone, un `:hover` reste collé après le tap et la carte garde
        // une élévation qui ne veut plus rien dire.
        className="group plat-apparait mb-3 rounded-carte border border-line bg-semoule-raised p-3 shadow-pose
          transition-shadow duration-rapide ease-deplacement
          [@media(hover:hover)]:hover:shadow-carte"
      >
        <div className="flex items-start gap-3">
          {/* La vignette est toujours présente, même sans photo : une carte de
              restaurant garde la même grille de lecture plat après plat. Sans
              photo, une tuile générique par catégorie (VignetteCategorie)
              plutôt qu'un vide — jamais une fausse photo qui ne ressemblerait
              pas au plat réel. */}
          <div className={`relative shrink-0 w-16 h-16 ${rupture ? "opacity-45" : ""}`}>
            {photo ? (
              <>
                {/* La même image, floutée derrière la vignette : elle projette la
                    couleur du plat sur le fond crème et fait ressortir la photo
                    sans ajouter le moindre octet. */}
                <div
                  aria-hidden
                  className="absolute inset-0 rounded-controle bg-cover bg-center blur-md opacity-40 scale-95"
                  style={{ backgroundImage: `url(${photo})` }}
                />
                {/* La photo vient du média du restaurant, servie par l'API :
                    `next/image` demanderait un domaine déclaré au build, alors
                    que l'URL dépend du déploiement. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={photo}
                  alt={item.name}
                  loading="lazy"
                  // Le grossissement est contenu (2 %) et porté par l'image
                  // seule, pas par la carte : au survol, c'est le plat qui
                  // avance d'un pas, pas l'interface qui gonfle.
                  className="relative w-16 h-16 rounded-controle object-cover border-2 border-white shadow-carte
                    transition-transform duration-normal ease-deplacement
                    [@media(hover:hover)]:group-hover:scale-[1.02]"
                />
              </>
            ) : (
              <VignetteCategorie category={item.category} />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className={`text-corps font-semibold ${rupture ? "line-through opacity-45" : ""}`}>
              {item.name}
              {item.spice_level > 0 && (
                <span className="ms-1 inline-flex items-center gap-0.5 align-middle text-[var(--harissa-text)]">
                  {Array.from({ length: item.spice_level }).map((_, i) => (
                    <FlameIcon key={i} className="w-[13px] h-[13px] shrink-0" />
                  ))}
                </span>
              )}
              {/* Le badge signale l'EXCEPTION au marché, jamais sa norme
                  (F5/A6, retour terrain 2026-09-04) — comme un régime, on
                  tague le cas notable, pas la valeur par défaut. En Tunisie
                  (défaut halal), l'exception est "Non halal" ; en France
                  (défaut non-halal), l'exception est "Halal". Jamais les
                  deux badges affichés en même temps. */}
              {currentMarket.defaultHalal
                ? !item.is_halal && (
                    <span className="ms-1 text-legende font-normal text-[var(--harissa-text)] border border-[var(--harissa)] rounded px-1 align-middle">
                      {t.notHalalBadge}
                    </span>
                  )
                : item.is_halal && (
                    <span className="ms-1 text-legende font-normal text-[var(--menthe)] border border-[var(--menthe)] rounded px-1 align-middle">
                      {t.halalBadge}
                    </span>
                  )}
            </div>
            {item.description && (
              <div className="text-legende text-[var(--ink-soft)] mt-1">{item.description}</div>
            )}
            {item.allergens && (
              <div className="text-legende text-ink-soft/70 mt-0.5">{t.allergensLabel(item.allergens)}</div>
            )}
            {item.regimes.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {item.regimes.map((r) => (
                  <span
                    key={r.id}
                    className="text-legende font-medium text-[var(--menthe)] border border-[var(--menthe)] rounded px-1.5 py-px"
                  >
                    {r.name}
                  </span>
                ))}
              </div>
            )}
            {rupture && (
              <div className="text-legende font-semibold text-[var(--harissa-text)] mt-1">{t.itemOutOfStock}</div>
            )}

            {/* Prix et boutons sur la même ligne, au bas de la carte : le prix
                est ce qu'on cherche, le bouton ce qu'on vise. Les séparer de
                part et d'autre les rendait tous les deux difficiles à trouver. */}
            <div className="flex items-center justify-between gap-2 mt-2">
              <span
                // Le prix passe en encre : il n'est pas une action. Deux
                // harissa sur la même ligne — le prix et le bouton — mettaient
                // l'œil en concurrence et contredisaient la règle « un seul
                // harissa cliquable par zone de décision » de ui/Button.
                className={`text-corps font-bold tabular-nums text-encre ${
                  rupture ? "line-through opacity-45" : ""
                }`}
              >
                {formatAmount(item.price)} {t.currency}
              </span>
              <div className="flex items-center gap-2 shrink-0">
                <AnimatePresence initial={false}>
                  {ligne && (
                    <m.div
                      key="pas-quantite"
                      initial={{ opacity: 0, width: 0 }}
                      animate={{ opacity: 1, width: "auto", transition: TRANSITION.deplacement }}
                      exit={{ opacity: 0, width: 0, transition: TRANSITION.sortie }}
                      className="flex items-center gap-2 overflow-hidden"
                    >
                    <button
                      onClick={() => removeFromCart(cartKey(item.id, myDeviceKey))}
                      aria-label={t.removeFromCartAria(item.name)}
                      className="w-10 h-10 shrink-0 rounded-full border border-line bg-white text-encre
                        transition-transform duration-micro ease-deplacement active:scale-90
                        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-harissa focus-visible:ring-offset-2 focus-visible:ring-offset-semoule-raised"
                    >
                      −
                    </button>
                    <span
                      className={`inline-block min-w-[16px] text-center text-etiquette font-bold tabular-nums ${
                        bumpedItemId === item.id ? "animate-cart-bump" : ""
                      }`}
                    >
                      {ligne.quantity}
                    </span>
                    </m.div>
                  )}
                </AnimatePresence>
                {/* 40 px et non 34 : sous 40, la cible se rate au pouce en
                    tenant le téléphone d'une main, et le client tape deux fois.
                    Le « 19px » du glyphe reste en dur — c'est un dessin de
                    caractère, pas du texte courant. */}
                <button
                  onClick={() => (hasOptionGroups && !ligne ? openOptionChooser(item) : addToCart(item))}
                  disabled={rupture}
                  aria-label={t.addToCartAria(item.name)}
                  className={`w-10 h-10 shrink-0 rounded-full text-[19px] leading-none shadow-carte
                    transition-transform duration-micro ease-deplacement active:scale-90
                    disabled:cursor-not-allowed disabled:active:scale-100 disabled:shadow-none
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-harissa focus-visible:ring-offset-2 focus-visible:ring-offset-semoule-raised ${
                      rupture ? "bg-line-strong text-semoule" : "bg-harissa text-[var(--on-harissa)]"
                    }`}
                >
                  +
                </button>
              </div>
            </div>
          </div>
        </div>
        {/* Le dépliement était le défaut le plus visible de la carte : ajouter
            un plat révélait d'un coup ~250 px (note, plat à partager, convives)
            et poussait toute la carte vers le bas, sans transition. L'œil
            perdait sa place au moment précis où il vérifiait son geste.
            L'enveloppe porte l'animation et `overflow-hidden` ; le panneau
            garde sa marge et son filet, sinon un `height: 0` laisserait un
            talon de 21 px (box-sizing: border-box). */}
        <AnimatePresence initial={false}>
          {ligne && (
            <m.div
              key="detail-plat"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1, transition: TRANSITION.entree }}
              exit={{ height: 0, opacity: 0, transition: TRANSITION.sortie }}
              className="overflow-hidden"
            >
          <div className="mt-2.5 pt-2.5 border-t border-line">
            {ligne.selectedOptions.length > 0 && (
              <p className="text-legende text-ink-soft mb-2">
                {ligne.selectedOptions.map((o) => o.optionName).join(" · ")}
              </p>
            )}
            <input
              type="text"
              value={ligne.note}
              onChange={(e) => setNote(cartKey(item.id, myDeviceKey), e.target.value)}
              placeholder={t.notePlaceholder}
              className="w-full text-etiquette bg-white border border-[var(--line)] rounded-controle px-2.5 py-2 placeholder:text-[var(--ink-soft)]"
            />
            <label className="mt-2 flex items-center gap-2 text-etiquette cursor-pointer">
              <input
                type="checkbox"
                checked={ligne.shared}
                onChange={(e) => setShared(cartKey(item.id, myDeviceKey), e.target.checked)}
                className="sr-only"
              />
              <span
                className="w-[18px] h-[18px] rounded-champ border-[1.5px] flex items-center justify-center shrink-0"
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
            {/* Indépendant de la case "à partager" ci-dessus : assigner un
                plat à un ou plusieurs convives reste facultatif et vaut pour
                n'importe quel plat, pas seulement les plats à partager
                (ROADMAP.md §Override 2026-09-08) — alimente directement
                SplitBill au moment de payer plutôt que de reposer la
                question. */}
            <div className="mt-2">
              <p className="text-legende text-ink-soft">{t.sharedWithLabel}</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {Array.from({ length: convives }, (_, i) => i + 1).map((place) => {
                  const choisi = ligne.sharedWith.includes(place);
                  return (
                    <button
                      key={place}
                      type="button"
                      onClick={() => toggleConvive(cartKey(item.id, myDeviceKey), place)}
                      aria-pressed={choisi}
                      className={`rounded-full border px-3 py-1.5 text-etiquette transition-colors duration-rapide ease-deplacement ${
                        choisi
                          ? "bg-[var(--harissa)] text-[var(--semoule)] border-[var(--harissa)]"
                          : "border-[var(--line)] bg-white text-[var(--encre)]"
                      }`}
                    >
                      {personLabel(place)}
                    </button>
                  );
                })}
              </div>
              {ligne.sharedWith.length === 0 ? (
                <p className="mt-1 text-legende text-ink-soft">{t.sharedWithEveryone}</p>
              ) : (
                <p className="mt-1 text-legende text-ink-soft">{t.sharedPerPersonAmount(perPerson)}</p>
              )}
            </div>
          </div>
            </m.div>
          )}
        </AnimatePresence>
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
        {localeSwitchLabel(locale)}
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
      {/* Identité de table (ROADMAP.md §Override, extension) : bloquante, dès
          que le canal de la table est connecté et que ce téléphone n'a pas
          déjà une identité pour ce QR (voir l'effet plus haut). */}
      {showIdentityPrompt && (
        <IdentityPrompt restaurantName={restaurant.name} tableLabel={table.label} onSubmit={confirmIdentity} t={t} />
      )}
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
          <div className="relative bg-harissa text-[var(--on-harissa)] pt-2 pb-3 ps-20 pe-4">
            <div className="absolute -top-7 start-3.5 w-14 h-14 rounded-full border-[3px] border-[var(--harissa)] shadow-md bg-[var(--semoule)] flex items-center justify-center overflow-hidden">
              {logoPhoto ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={logoPhoto} alt={restaurant.name} className="w-full h-full object-cover" />
              ) : (
                <TawlaMark size={32} />
              )}
            </div>
            <h1 className={`${lalezar.className} text-affiche text-balance`}>{restaurant.name}</h1>
            {/* Même correction de contraste que la variante sans couverture. */}
            <p className="text-etiquette font-medium mt-0.5">{table.label}</p>
            {/* Ancrées à la ligne de la table, pas à celle du nom : cette
                ligne-là reste courte à gauche quelle que soit la longueur du
                nom au-dessus, donc jamais de collision (Phase D1, point 3). */}
            <ReseauxSociaux restaurant={restaurant} className="absolute bottom-3 end-4" />
          </div>
        </header>
      ) : (
        /* Sur téléphone, l'en-tête tient sur deux rangs : le nom du restaurant
           d'abord, sur toute la largeur, les actions en dessous. Côte à côte,
           les deux pastilles prenaient 170 des 390 px et « Dar Chaabane » se
           coupait en deux lignes — le nom du restaurant est le seul moment de
           marque de la page, il ne se casse pas pour laisser place à un
           bouton. À partir de `sm`, la place existe et on revient sur un rang. */
        <header className="bg-harissa text-[var(--on-harissa)] px-4 pt-2.5 pb-3.5 flex flex-col gap-2.5 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
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
              <h1 className={`${lalezar.className} text-affiche text-balance`}>{restaurant.name}</h1>
              {/* Blanc plein, pas un semoule à 82 % : mesuré à 3,13:1 sur
                  l'aplat harissa, très en dessous du seuil AA. La hiérarchie
                  passe par la taille et la graisse, jamais par l'opacité — sur
                  un accent saturé, l'opacité mange le contraste avant de
                  produire de la nuance. */}
              <p className="text-etiquette font-medium mt-0.5">{table.label}</p>
            </div>
          </div>
          <div className="flex items-center justify-end gap-2 shrink-0 sm:flex-col sm:items-end sm:gap-2">
            {enTeteActions}
            <ReseauxSociaux restaurant={restaurant} />
          </div>
        </header>
      )}

      {restaurant.ramadan_mode_enabled && restaurant.iftar_time && (
        <div className="bg-[var(--espresso)] px-4 py-[11px] flex items-start gap-2 text-[12.5px] leading-[1.45] text-[rgba(246,239,221,.88)]">
          <MoonIcon className="w-4 h-4 shrink-0 mt-0.5 text-[var(--laiton-text)]" />
          <p>
            <b className="text-[var(--laiton-text)]">{t.ramadanBannerPrefix}</b>
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
          <ul
            ref={listeCategoriesRef}
            className="relative flex gap-2 overflow-x-auto px-4 py-2.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          >
            {/* Un seul repère qui glisse d'une catégorie à l'autre, au lieu
                d'une couleur qui s'éteint ici et se rallume là : le glissement
                dit d'où on vient. Piloté par mesure plutôt que par une
                animation de layout — le socle ne charge que `domAnimation`, et
                CSS suffit pour un déplacement dans le même écran. */}
            {repereCategorie && (
              <span
                aria-hidden
                className="absolute left-0 top-0 rounded-full bg-harissa transition-[transform,width] duration-rapide ease-deplacement motion-reduce:transition-none"
                style={{
                  width: repereCategorie.largeur,
                  height: repereCategorie.hauteur,
                  transform: `translate(${repereCategorie.x}px, ${repereCategorie.y}px)`,
                }}
              />
            )}
            {categories.map((category) => {
              const anchor = categoryAnchor(category);
              const active = anchor === ancreCategorieActive;
              return (
                <li key={category} data-ancre={anchor} className="relative z-[1]">
                  <a
                    id={`${anchor}-pill`}
                    href={`#${anchor}`}
                    aria-current={active ? "true" : undefined}
                    className={`inline-block whitespace-nowrap rounded-full border px-[13px] py-1.5 text-legende font-semibold
                      transition-colors duration-rapide ease-deplacement
                      focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-harissa focus-visible:ring-offset-2 focus-visible:ring-offset-semoule ${
                        active
                          ? "text-[var(--on-harissa)] border-transparent"
                          : "bg-semoule-raised text-encre border-line"
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
                    className="w-full text-start text-sm underline text-[var(--laiton-text)] flex justify-between gap-2"
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
          <div className="mb-4 text-sm text-[var(--harissa-text)] bg-[rgba(214,64,30,.1)] border border-[rgba(214,64,30,.55)] rounded-2xl p-3">
            {waiterCallError}
          </div>
        )}
        {orderError && (
          <div className="mb-4 text-sm text-[var(--harissa-text)] bg-[rgba(214,64,30,.1)] border border-[rgba(214,64,30,.55)] rounded-2xl p-3 flex justify-between items-start gap-2">
            <span>{orderError}</span>
            <button onClick={() => setOrderError(null)} aria-label={t.closeErrorAria} className="text-[var(--harissa-text)]">
              ✕
            </button>
          </div>
        )}

        {/* Replié, ce n'est qu'une proposition facultative : elle ne porte donc
            plus le cadre laiton plein, qui la faisait lire comme une offre
            promue juste au-dessus du premier plat. Le cadre revient une fois la
            section ouverte, où il délimite un vrai formulaire. */}
        <div
          className={
            loyaltySectionOpen
              ? "mb-4 rounded-carte border border-[rgba(184,134,46,.5)] bg-creme p-3"
              : "mb-4"
          }
        >
          {!loyaltySectionOpen ? (
            <button
              onClick={() => setLoyaltySectionOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-champ text-etiquette font-semibold text-laiton-text
                transition-colors duration-micro ease-deplacement
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-harissa focus-visible:ring-offset-2 focus-visible:ring-offset-semoule"
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
                <Link href="/confidentialite" className="underline text-[var(--laiton-text)]">
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
                <p className="text-sm text-[var(--laiton-text)] pt-1 flex items-center gap-1.5">
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
                <span className="h-px flex-1 bg-line" />
                <span className="text-surtitre font-bold uppercase text-laiton-text whitespace-nowrap">
                  {menuCategoryLabel(category, locale)}
                </span>
                <span className="h-px flex-1 bg-line" />
              </h2>
              {menu.filter((m) => m.category === category).map((item, i) => renderItem(item, i))}
            </section>
          ))
        )}

        {/* Uniquement CE que ce téléphone a lui-même ajouté (identité de
            table) : la carte ne doit pas réagir aux ajouts des autres
            convives, seul le panier de table (ci-dessous) englobe tout le
            monde. */}
        {/* La barre arrive par le bas et repart par le bas. Elle apparaissait
            sèchement au premier plat ajouté — au moment précis où l'œil est
            ailleurs, sur la ligne qui vient de se déplier — donc on ne la
            voyait pas arriver. `AnimatePresence` sert la sortie : un élément
            démonté ne peut pas s'animer en CSS. */}
        <AnimatePresence>
          {myCartLines.length > 0 && !showCartReview && (
            <m.div
              key="barre-panier"
              initial={{ y: "100%" }}
              animate={{ y: 0, transition: TRANSITION.entree }}
              exit={{ y: "100%", transition: TRANSITION.sortie }}
              className="fixed bottom-0 left-0 right-0 bg-espresso pt-3.5 px-4 pb-[max(1.125rem,env(safe-area-inset-bottom))] shadow-barre"
            >
              <div className="max-w-md mx-auto">
                <div className="flex justify-between items-center gap-3" data-visite="client-panier">
                  <div>
                    <p className="text-surtitre font-semibold text-[var(--ink-on-espresso)]">
                      {t.cartItemsCount(myCartLines.reduce((s, l) => s + l.quantity, 0))}
                    </p>
                    {/* Le total se remplace en fondu à chaque changement. La clé
                        porte la valeur : React remonte le nœud, donc
                        AnimatePresence peut faire sortir l'ancien montant
                        pendant que le nouveau entre. Un chiffre qui se substitue
                        d'un coup se lit comme un rafraîchissement de données,
                        pas comme la conséquence du clic (principe 6).

                        Le gabarit en flux donne sa taille à la boîte : les deux
                        copies qui se croisent sont en position absolue et ne
                        mesurent rien, sans lui le montant serait tronqué à la
                        largeur du libellé du dessus. C'est aussi lui que lisent
                        les lecteurs d'écran, les copies animées étant masquées
                        — pendant le fondu, deux montants coexistent. */}
                    <span className="relative mt-0.5 block overflow-hidden">
                      <span className={`${lalezar.className} block text-[26px] leading-none tabular-nums opacity-0`}>
                        {formatAmount(myTotal)} {t.currency}
                      </span>
                      <AnimatePresence initial={false}>
                        <m.span
                          key={myTotal}
                          aria-hidden
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0, transition: TRANSITION.deplacement }}
                          exit={{ opacity: 0, y: -10, transition: { duration: DUREE.rapide, ease: COURBE.sortie } }}
                          className={`${lalezar.className} absolute inset-0 whitespace-nowrap text-[26px] leading-none tabular-nums text-semoule`}
                        >
                          {formatAmount(myTotal)} {t.currency}
                        </m.span>
                      </AnimatePresence>
                    </span>
                  </div>
                  <Button
                    size="lg"
                    shape="pilule"
                    onClick={() => setShowCartReview(true)}
                    className="shrink-0 px-[22px] font-bold"
                  >
                    {t.viewCartButton}
                  </Button>
                </div>
              </div>
            </m.div>
          )}
        </AnimatePresence>

        {/* Récapitulatif façon panier d'appli de livraison, ouvert avant de
            valider : tout ce qui compose la commande (articles, quantités,
            notes, options, réglages de partage/pré-commande) en un seul
            endroit, plus le total — la validation elle-même se joue d'ici,
            jamais depuis le bandeau du dessus. */}
        {showCartReview && cartLines.length > 0 && (
          <div className="fixed inset-0 z-50 flex flex-col bg-[var(--semoule)]">
            <div className="shrink-0 flex items-center gap-3 border-b border-[var(--line)] bg-[var(--semoule-raised)] px-4 py-3">
              <button
                onClick={() => setShowCartReview(false)}
                className="text-sm font-semibold text-[var(--encre)]"
              >
                {t.backToMenuButton}
              </button>
              <p className="flex-1 text-center text-[15px] font-bold text-[var(--encre)] pe-[88px]">
                {t.cartSummaryTitle}
              </p>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-3">
              <div className="max-w-md mx-auto space-y-2">
                {/* Dupliqué de la bannière d'erreur de la carte (plus bas dans
                    le DOM) : cet écran plein cadre la recouvre entièrement,
                    sans ça un échec de validation (article devenu indisponible,
                    connexion perdue...) resterait invisible derrière lui. */}
                {orderError && (
                  <div className="text-sm text-[var(--harissa-text)] bg-[rgba(214,64,30,.1)] border border-[rgba(214,64,30,.55)] rounded-2xl p-3 flex justify-between items-start gap-2">
                    <span>{orderError}</span>
                    <button
                      onClick={() => setOrderError(null)}
                      aria-label={t.closeErrorAria}
                      className="text-[var(--harissa-text)]"
                    >
                      ✕
                    </button>
                  </div>
                )}
                {/* À table (identité de table, ROADMAP.md §Override) : qui a
                    déjà scanné, avec possibilité d'ajouter un convive qui ne
                    scanne pas — sert au tag sous chaque plat ci-dessous et à
                    la répartition de l'addition (SplitBill). */}
                <div className="rounded-[14px] border border-[var(--line)] bg-[var(--semoule-raised)] p-3">
                  <p className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-[var(--ink-faint)]">
                    {t.rosterSectionTitle}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {roster.map((p) => (
                      <span
                        key={p.key}
                        className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                          p.key === myDeviceKey
                            ? "bg-[var(--harissa)] border-[var(--harissa)] text-[var(--semoule)]"
                            : "border-[var(--line)] bg-white text-[var(--encre)]"
                        }`}
                      >
                        {p.key === myDeviceKey ? t.rosterYouTag(p.name) : p.name}
                      </span>
                    ))}
                    {!addingGuest && (
                      <button
                        type="button"
                        onClick={() => setAddingGuest(true)}
                        className="rounded-full border border-dashed border-[var(--line-strong)] px-3 py-1 text-xs font-semibold text-[var(--ink-soft)]"
                      >
                        {t.rosterAddGuestChip}
                      </button>
                    )}
                  </div>
                  {addingGuest && (
                    <div className="mt-2 flex items-center gap-2">
                      <input
                        type="text"
                        value={guestNameInput}
                        onChange={(e) => setGuestNameInput(e.target.value)}
                        placeholder={t.rosterAddGuestPlaceholder}
                        maxLength={30}
                        autoFocus
                        className="flex-1 bg-white border border-[var(--line)] rounded-[10px] px-3 py-1.5 text-sm text-[var(--encre)]"
                      />
                      <button
                        type="button"
                        onClick={addGuestToRoster}
                        className="rounded-[10px] px-3 py-1.5 text-xs font-bold bg-[var(--harissa)] text-[var(--semoule)] whitespace-nowrap"
                      >
                        {t.rosterAddGuestConfirm}
                      </button>
                    </div>
                  )}
                </div>

                {cartLines.map((line) => {
                  const key = cartKey(line.item.id, line.addedByKey);
                  const mine = line.addedByKey === myDeviceKey;
                  return (
                    <div
                      key={key}
                      className="rounded-[14px] border border-[var(--line)] bg-[var(--semoule-raised)] p-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="text-[14.5px] font-semibold text-[var(--encre)]">{line.item.name}</p>
                          {line.selectedOptions.length > 0 && (
                            <p className="text-xs text-[var(--ink-soft)] mt-0.5">
                              {line.selectedOptions.map((o) => o.optionName).join(" · ")}
                            </p>
                          )}
                          {line.note && <p className="text-xs text-[var(--ink-soft)] mt-0.5">{line.note}</p>}
                          <div className="mt-1 flex items-center gap-1.5 flex-wrap">
                            {line.shared && (
                              <span className="text-xs text-[var(--laiton-text)] inline-flex items-center gap-1">
                                <UtensilsIcon className="w-3.5 h-3.5 shrink-0" /> {t.sharedTag}
                              </span>
                            )}
                            {/* Prénom de qui a ajouté ce plat (identité de table) —
                                le tag qui permet à l'addition de le retrouver plus
                                tard, plutôt qu'une ligne anonyme. */}
                            <span
                              className={`text-[10.5px] font-semibold px-2 py-[2px] rounded-full ${
                                mine
                                  ? "bg-[rgba(214,64,30,.1)] text-[var(--harissa-dark)]"
                                  : "bg-[rgba(107,89,71,.1)] text-[var(--ink-soft)]"
                              }`}
                            >
                              {mine ? t.rosterYouTag(line.addedByName) : line.addedByName}
                            </span>
                          </div>
                          {/* « Pour qui ? » assigné sur la carte : le panier
                              doit le refléter, sinon l'assignation paraît
                              perdue (retour QA). Le tag ci-dessus dit qui a
                              ajouté le plat — deux informations distinctes :
                              Karim peut commander un plat pour Sami. */}
                          {line.sharedWith.length > 0 && (
                            <p className="mt-1 text-legende text-[var(--ink-soft)]">
                              {t.cartForWhom(line.sharedWith.map(personLabel).join(" · "))}
                            </p>
                          )}
                        </div>
                        <span className="shrink-0 text-[14.5px] font-bold tabular-nums text-[var(--harissa-text)]">
                          {formatAmount(lineUnitPrice(line) * line.quantity)} {t.currency}
                        </span>
                      </div>
                      <div className="mt-2 flex items-center justify-end gap-2">
                        {mine ? (
                          <>
                            <button
                              onClick={() => removeFromCart(key)}
                              aria-label={t.removeFromCartAria(line.item.name)}
                              className="w-[30px] h-[30px] rounded-full border border-[var(--line)] bg-white transition-transform active:scale-90"
                            >
                              −
                            </button>
                            <span className="inline-block min-w-[16px] text-center text-[14px] font-bold tabular-nums">
                              {line.quantity}
                            </span>
                            <button
                              onClick={() => addToCart(line.item)}
                              aria-label={t.addToCartAria(line.item.name)}
                              className="w-[30px] h-[30px] rounded-full bg-[var(--harissa)] text-[var(--semoule)] text-[17px] leading-none shadow-sm transition-transform active:scale-90"
                            >
                              +
                            </button>
                          </>
                        ) : (
                          // Vu, jamais modifiable : seul l'appareil qui a ajouté
                          // ce plat peut en changer la quantité ou le retirer.
                          <span className="inline-flex items-center gap-1.5 text-[13px] text-[var(--ink-soft)]">
                            <LockIcon className="w-3.5 h-3.5 shrink-0" />
                            {line.quantity}×
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
                {cartLines.some((l) => l.addedByKey !== myDeviceKey) && (
                  <p className="text-[11px] text-[var(--ink-faint)]">{t.rosterOwnItemsOnlyNote}</p>
                )}

                {/* Plus de compteur « Personnes à table » ici : les convives se
                    déclarent eux-mêmes en scannant, et « + Ajouter » (section
                    « À table ») nomme ceux qui n'ont pas scanné — ce qui les
                    fait apparaître sous leur prénom dans « Pour qui ? » plutôt
                    qu'en « Personne N » anonyme. */}
                {restaurant.ramadan_mode_enabled && restaurant.iftar_time && (
                  <label className="flex items-center gap-2 text-sm text-[var(--encre)] pt-2">
                    <input
                      type="checkbox"
                      checked={preOrderForIftar}
                      onChange={(e) => setPreOrderForIftar(e.target.checked)}
                      className="accent-[var(--laiton)]"
                    />
                    <MoonIcon className="w-4 h-4 shrink-0 text-[var(--laiton-text)]" />
                    {t.preorderCheckboxLabel(formatTime(restaurant.iftar_time))}
                  </label>
                )}
              </div>
            </div>

            <div className="shrink-0 bg-[var(--espresso)] pt-[14px] px-4 pb-[18px]">
              <div className="max-w-md mx-auto flex justify-between items-center gap-3">
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
                  .filter((item): item is MenuItem => !!item && item.is_available && !cart[cartKey(item.id, myDeviceKey)])
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
