import { clearToken, getToken } from "@/lib/auth";

/**
 * En production, l'URL de l'API est fournie explicitement (`NEXT_PUBLIC_API_URL`).
 *
 * Sans elle — donc en développement — on suit l'hôte qui a servi la page plutôt
 * que d'écrire « localhost » en dur : un téléphone qui scanne le QR charge la
 * page depuis l'adresse du Mac sur le réseau local, et « localhost » y désigne
 * le téléphone lui-même. C'est ce qui faisait échouer tous les appels dès qu'on
 * quittait la machine de développement, et ça évite de recoder une adresse IP à
 * chaque changement de réseau.
 */
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? `${window.location.protocol}//${window.location.hostname}:8000` : "http://localhost:8000");

export type MenuItemOption = {
  id: number;
  name: string;
  price_delta: number;
};

export type MenuItemOptionGroup = {
  id: number;
  name: string;
  min_select: number;
  max_select: number;
  options: MenuItemOption[];
};

export type MenuRegime = {
  id: number;
  name: string;
};

export type MenuItem = {
  id: number;
  restaurant_id: number;
  name: string;
  description: string | null;
  category: string;
  price: number;
  is_available: boolean;
  image_url: string | null;
  spice_level: number;
  allergens: string | null;
  is_halal: boolean;
  // Cuisson, sauce, accompagnement... (France, MARCHE_FRANCE.md phase F5/A2).
  // Toujours présent (liste vide par défaut) : la quasi-totalité des articles
  // n'en ont aucun tant qu'un manager ne les configure pas.
  option_groups: MenuItemOptionGroup[];
  // Régimes cochés parmi le vocabulaire du restaurant (« Halal »,
  // « Végétarien »...) — coexiste avec is_halal, ne le remplace pas.
  regimes: MenuRegime[];
};

export type Table = {
  id: number;
  restaurant_id: number;
  label: string;
  qr_token: string;
  assigned_staff_id: number | null;
  zone: string | null;
  pos_x: number | null;
  pos_y: number | null;
  shape: "round" | "square" | "rect";
  seats: number;
};

/**
 * Résultat d'un import de carte : les lignes valides sont créées même si
 * d'autres sont fautives, et `errors` dit précisément lesquelles corriger —
 * recommencer un fichier de 40 plats pour une faute de frappe serait inacceptable.
 */
export type MenuCsvImportResult = {
  created_count: number;
  updated_count: number;
  disabled_count: number;
  errors: string[];
};

export type SubscriptionTier = "essentiel" | "pro" | "business";

/** Ce que le parcours client reçoit : aucune donnée commerciale. */
export type RestaurantPublic = {
  id: number;
  name: string;
  ramadan_mode_enabled: boolean;
  iftar_time: string | null;
  cafe_mode_enabled: boolean;
  cover_photo_url: string | null;
  logo_url: string | null;
  facebook_url: string | null;
  instagram_url: string | null;
  tiktok_url: string | null;
  whatsapp_url: string | null;
  google_review_url: string | null;
};

export type Restaurant = RestaurantPublic & {
  slug: string;
  kitchen_sound_enabled: boolean;
  subscription_tier: SubscriptionTier;
  subscription_period_end: string | null;
  // Wallet Konnect PROPRE à ce restaurant, pour le paiement carte du client
  // (modèle direct, 2026-08-19) — jamais celui de Tawla. La clé API elle-même
  // n'est jamais renvoyée, seulement ces deux champs.
  konnect_configured: boolean;
  konnect_wallet_id: string | null;
  // Idem, Stripe Connect (France) — voir StripeProvider/stripe_gateway côté
  // backend. Pas d'équivalent à konnect_wallet_id à afficher : l'account_id
  // n'apporte rien de lisible au manager, seul l'état "connecté" compte.
  stripe_configured: boolean;
  // Abonnement TAWLA récurrent (mode Netflix, 2026-09-02) — distinct de
  // stripe_configured ci-dessus (paiement carte du CLIENT du restaurant).
  // Jamais l'id Stripe lui-même, juste de quoi savoir si "Gérer mon
  // abonnement" (portail Stripe) a un sens à afficher.
  stripe_subscription_active: boolean;
  // Annulation demandée par le manager depuis le portail Stripe, effective
  // à subscription_period_end (2026-09-02) — sinon l'interface continuerait
  // à afficher "renouvellement automatique" après une annulation réelle.
  subscription_cancel_at_period_end: boolean;
  // Rétrogradation programmée, pas encore appliquée (2026-09-02) — sans ce
  // champ, l'interface n'avait aucun moyen de refléter un clic réussi avant
  // la prochaine échéance.
  subscription_downgrade_pending_tier: SubscriptionTier | null;
  // Activation du compte (2026-08-20) — Essentiel n'est jamais gratuit, voir
  // is_usable côté backend (tenants/models.py). Le dashboard bloque tout tant
  // que ce n'est pas vrai (une promo personnalisée à 100 % l'active comme un
  // paiement, voir platform_admin/router.py::set_restaurant_promo).
  is_active: boolean;
  // Offre de lancement (2026-08-21, réglages configurables depuis le
  // dashboard plateforme — voir lib/platformAdmin.ts) : réduction figée à
  // l'inscription, `null` si ce restaurant n'en a jamais bénéficié.
  // has_paid_for_subscription à false tant qu'aucun vrai paiement n'a eu
  // lieu : c'est ce qui déclenche le rappel de paiement sur le dashboard,
  // avec le compte à rebours dérivé de subscription_period_end ci-dessus.
  launch_promo_discount_percent: number | null;
  has_paid_for_subscription: boolean;
  // Établissement de démo jetable — jamais payé par construction, voir
  // backend/app/modules/tenants/models.py. Empêche le rappel de paiement de
  // s'afficher sur un compte de démo (dashboard/page.tsx).
  is_demo: boolean;
  // Mentions légales de la facture PDF (invoice.py) — jamais sur
  // RestaurantPublic, contrairement aux réseaux sociaux : le client n'en a
  // jamais besoin, seule la génération de facture les lit côté serveur.
  // Verrouillées Pro+ à l'écriture (voir setLegalInfo ci-dessous).
  legal_address: string | null;
  tax_id: string | null;
  vat_number: string | null;
};

/**
 * `mode: "demo"` : palier déjà appliqué, `restaurant` à jour, aucun paiement
 * réel (fournisseur du marché pas encore activé pour Tawla elle-même — voir
 * backend app/core/konnect.py / stripe_gateway.py). `mode: "konnect"` /
 * `mode: "stripe"` : rediriger vers `pay_url`, le palier ne change qu'au
 * règlement effectif du paiement.
 */
export type SubscriptionCheckoutResult = {
  mode: "demo" | "konnect" | "stripe";
  restaurant: Restaurant | null;
  pay_url: string | null;
};

/** Offre de lancement (2026-08-21) — voir GET /auth/launch-promo. Termes de
 * la campagne EN COURS, pas ce qu'un restaurant déjà inscrit a obtenu (voir
 * Restaurant.launch_promo_discount_percent, figé à l'inscription). */
export type LaunchPromoStatus = {
  available: boolean;
  discount_percent: number;
  max_grants: number;
};

export type StaffRole = "waiter" | "kitchen" | "manager";

export type Staff = {
  id: number;
  restaurant_id: number;
  name: string;
  role: StaffRole;
  email: string;
  is_active: boolean;
};

// Le mot de passe temporaire n'est renvoyé qu'à la création (quand le manager
// n'en fournit pas) et à la réinitialisation — il n'est stocké que haché côté
// serveur, donc il n'y a aucun moyen de le réafficher ensuite.
export type StaffCreated = {
  staff: Staff;
  temporary_password: string | null;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  staff: Staff;
};

/**
 * Établissement de démonstration jetable, monté à la demande quand un visiteur
 * clique « Voir la démo ». Un par visiteur — voir
 * `backend/app/modules/demo/service.py` pour pourquoi jamais un compte
 * partagé. `qr_token` est ce qui rend le parcours client atteignable : sans
 * lui, la page d'accueil ne connaît aucune table.
 */
export type DemoSession = {
  access_token: string;
  staff: Staff;
  restaurant_id: number;
  restaurant_name: string;
  qr_token: string;
  expires_at: string;
  waiter_access_token: string;
  kitchen_access_token: string;
};

export type OrderStatus =
  | "pending_confirmation"
  | "confirmed"
  | "sent_to_kitchen"
  | "in_preparation"
  | "ready"
  | "served"
  | "cancelled";

export type PaymentMethod = "card" | "card_terminal" | "cash";
export type PaymentStatus = "unpaid" | "pending" | "paid";

/**
 * Une ligne de panier telle qu'envoyée au backend — forme commune à la
 * création d'une commande, son édition directe (fenêtre 1) et une demande de
 * modification (fenêtre 2), pour que les trois ne divergent jamais.
 */
export type OrderItemPayload = {
  menu_item_id: number;
  quantity: number;
  notes?: string | null;
  is_shared?: boolean;
  shared_with?: number[];
  from_suggestion?: boolean;
  selected_option_ids?: number[];
};

export type ModificationLineStatus = "pending" | "accepted" | "declined";

/** Une ligne d'une demande de modification (fenêtre 2) : un article dont la
 *  quantité demandée diffère de la quantité actuelle de la commande —
 *  `previous_quantity` à 0 pour un ajout, `requested_quantity` à 0 pour un
 *  retrait complet. */
export type ModificationLine = {
  id: number;
  menu_item_id: number;
  menu_item_name: string;
  unit_price: number;
  previous_quantity: number;
  requested_quantity: number;
  notes: string | null;
  is_shared: boolean;
  status: ModificationLineStatus;
};

export type ModificationRequest = {
  id: number;
  order_id: number;
  table_id: number;
  table_label: string;
  status: "pending" | "resolved";
  created_at: string;
  resolved_at: string | null;
  lines: ModificationLine[];
};

export type Order = {
  id: number;
  restaurant_id: number;
  table_id: number;
  /** Le nom écrit sur la table. `table_id` est un identifiant de base, pas
   *  quelque chose qu'un serveur puisse retrouver en salle. */
  table_label: string;
  status: OrderStatus;
  taken_by_staff_id: number | null;
  taken_by_staff_name: string | null;
  created_at: string;
  // Posé uniquement par une édition directe du client (fenêtre "modifier la
  // commande" tant qu'elle est en attente de confirmation) — jamais par une
  // transition de statut. Sert à afficher "Modifiée à HH:MM" côté client et
  // le badge "Modifiée" côté pool serveur.
  items_updated_at: string | null;
  // Non-null tant qu'au moins une ligne de la dernière demande de
  // modification (fenêtre 2) attend une réponse du serveur.
  pending_modification_request: ModificationRequest | null;
  scheduled_for: string | null;
  sent_to_kitchen_at: string | null;
  preparation_started_at: string | null;
  ready_at: string | null;
  // Présent uniquement sur les réponses servies au staff (routes sous JWT) :
  // la vue client ne porte plus de donnée personnelle depuis la Phase 12.2.
  loyalty_phone?: string | null;
  payment_method: PaymentMethod | null;
  payment_status: PaymentStatus;
  tip_amount: number;
  total_amount: number;
  // Posé uniquement par la réponse de `payByCard` quand le restaurant a
  // connecté son propre Konnect : rediriger le client vers cette URL pour
  // qu'il règle. `payment_status` reste "pending" tant que ce n'est pas fait.
  pay_url?: string | null;
  items: {
    id: number;
    menu_item_id: number;
    menu_item_name: string;
    unit_price: number;
    quantity: number;
    notes: string | null;
    is_shared: boolean;
    /** Numéros de places entre lesquelles le plat est partagé. Vide = toute la table. */
    shared_with: number[];
    from_suggestion: boolean;
    /** Choix figés au moment de la commande (« Cuisson : à point »). Le
     *  supplément est indicatif, déjà compté dans unit_price. */
    options: { group_name: string; option_name: string; price_delta: number }[];
  }[];
};

/**
 * Réponse de création d'une commande — la seule qui porte le `public_token`.
 * Le navigateur doit le conserver : c'est son seul moyen de suivre, payer ou
 * s'abonner aux notifications de cette commande ensuite.
 */
export type OrderCreated = Order & { public_token: string };

export type WaiterCall = {
  id: number;
  restaurant_id: number;
  table_id: number;
  table_label: string;
  created_at: string;
  resolved_at: string | null;
  resolved_by_staff_id: number | null;
};

export type LoyaltyMember = {
  id: number;
  restaurant_id: number;
  phone_number: string;
  birth_date: string | null;
  order_count: number;
  reward_available: boolean;
  orders_until_reward: number;
  is_birthday_today: boolean;
};

export type TimingStats = {
  avg_wait_confirmation_seconds: number | null;
  avg_confirmation_to_kitchen_seconds: number | null;
  avg_kitchen_to_served_seconds: number | null;
  avg_served_to_paid_seconds: number | null;
};

export type StaffPerformance = {
  staff_id: number;
  staff_name: string;
  role: StaffRole;
  orders_taken: number;
};

/** Charge d'un serveur **en ce moment** (2026-08-28) : combien de tables il a
 *  actuellement sur les bras, distinct du cumul du jour (`StaffPerformance`). */
export type StaffActiveLoad = {
  staff_id: number;
  staff_name: string;
  role: StaffRole;
  tables_count: number;
};

export type TopMenuItem = { menu_item_name: string; quantity: number };
export type HourlyCount = { hour: number; count: number };

export type DashboardStats = {
  date: string;
  /** Les deux chiffres de tête (Phase 17.1, remaniés le 2026-08-28) : ce que
   *  le patron vient chercher chaque soir, et le temps d'attente moyen posé
   *  juste à côté — un signal opérationnel du jour même. */
  revenue_today: number;
  cancelled_orders_today: number;
  active_orders_count: number;
  timing: TimingStats;
  staff_performance: StaffPerformance[];
  staff_active_load: StaffActiveLoad[];
  top_items: TopMenuItem[];
  orders_by_hour: HourlyCount[];
};

export type KitchenTodayCount = { date: string; count: number };

/**
 * Les trois chiffres de preuve d'un pilote (Phase 13.3) : commandes annulées,
 * délai commande → cuisine, panier moyen. `null` sur les moyennes veut dire
 * « aucune donnée », pas zéro — la distinction compte devant un patron.
 */
export type PeriodProof = {
  start: string;
  end: string;
  orders_count: number;
  cancelled_orders_count: number;
  avg_order_to_kitchen_seconds: number | null;
  avg_basket_amount: number | null;
  orders_with_suggestion_count: number;
  avg_basket_with_suggestion: number | null;
  avg_basket_without_suggestion: number | null;
};

/**
 * Ligne de rapport d'équipe (Phase 14.2) — base d'une prime de rendement.
 * Réservé au manager : c'est un document de direction, pas un classement à
 * afficher en salle.
 */
export type StaffPeriodReport = {
  staff_id: number;
  staff_name: string;
  role: StaffRole;
  orders_taken: number;
  avg_seconds_to_claim: number | null;
  total_amount_handled: number;
  total_tips_collected: number;
  timing: TimingStats;
};

/** Ce qu'un membre d'équipe voit de sa propre soirée (Phase 17.3) : ses
 *  chiffres seuls, aucun collègue, aucun classement. */
export type MyShift = {
  date: string;
  orders_taken: number;
  total_amount_handled: number;
  avg_seconds_to_claim: number | null;
};

export type TableShape = "round" | "square" | "rect";

/** Vue plan d'une table — sans `qr_token` : il n'a rien à faire sur un écran
 *  de service (Phase 18). */
export type PlanTable = {
  id: number;
  label: string;
  zone: string | null;
  pos_x: number | null;
  pos_y: number | null;
  shape: TableShape;
  seats: number;
};

export type TeamReport = {
  start: string;
  end: string;
  staff: StaffPeriodReport[];
};

export type ProofStats = {
  current: PeriodProof;
  previous: PeriodProof;
};

// Code stable renvoyé par le backend pour chaque erreur (voir
// backend/app/modules/*/router.py et orders/service.py) — permet de
// traduire proprement côté client au lieu d'afficher le message brut
// anglais renvoyé par l'API (bug relevé à l'audit du 2026-08-10).
export class ApiError extends Error {
  code: string;
  context: Record<string, unknown>;

  constructor(code: string, message: string, context: Record<string, unknown> = {}) {
    super(message);
    this.code = code;
    this.context = context;
  }
}

// Codes qui signifient « cette session ne vaut plus rien », par opposition à un
// simple identifiant refusé sur l'écran de connexion (INVALID_CREDENTIALS).
const SESSION_LOST_CODES = new Set(["NOT_AUTHENTICATED", "INVALID_TOKEN", "ACCOUNT_DISABLED"]);

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Routes client d'une commande : le `public_token` reçu à sa création prouve
 * que l'appel vient bien du navigateur qui l'a passée (Phase 12.2). Sans lui,
 * le backend répond 404 — un identifiant de commande seul ne donne plus accès
 * à rien.
 */
function orderHeaders(orderToken: string): Record<string, string> {
  return { "X-Order-Token": orderToken };
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  // Un envoi de fichier ne doit pas porter de Content-Type : c'est le
  // navigateur qui le pose, avec le `boundary` du multipart qu'il vient de
  // tirer au hasard. L'imposer ici casserait le découpage côté serveur.
  const envoiFichier = options?.body instanceof FormData;
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    // Après le spread : sinon des en-têtes passés dans `options` écrasent
    // silencieusement Content-Type et l'Authorization du staff.
    headers: {
      ...(envoiFichier ? {} : { "Content-Type": "application/json" }),
      ...authHeaders(),
      ...(options?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail;
    if (detail && typeof detail === "object" && detail.code) {
      // Session devenue invalide en pleine session : JWT expiré (12 h) ou
      // compte désactivé par le manager pendant le service. Le garde
      // `useCurrentStaff` ne s'exécute qu'au montage : sans ce traitement
      // global, le serveur reste devant un écran qui ne répond plus et croit
      // à une panne. On ne touche jamais au parcours client, qui n'a pas de
      // token, ni à l'écran de connexion lui-même.
      if (res.status === 401 && SESSION_LOST_CODES.has(detail.code) && getToken()) {
        clearToken();
        if (typeof window !== "undefined") window.location.replace("/login");
      }
      throw new ApiError(detail.code, detail.message ?? `Erreur API (${res.status})`, detail);
    }
    throw new ApiError("UNKNOWN", typeof detail === "string" ? detail : `Erreur API (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

/**
 * Comme `request`, mais pour une réponse binaire (PDF) : pas de `res.json()`
 * possible sur le succès, donc pas réutilisable telle quelle.
 */
async function requestBlob(path: string): Promise<Blob> {
  const res = await fetch(`${API_URL}${path}`, { headers: authHeaders() });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail;
    if (detail && typeof detail === "object" && detail.code) {
      throw new ApiError(detail.code, detail.message ?? `Erreur API (${res.status})`, detail);
    }
    throw new ApiError("UNKNOWN", typeof detail === "string" ? detail : `Erreur API (${res.status})`);
  }
  return res.blob();
}

/**
 * Résout une adresse d'image servie par l'API. Les photos déposées par le
 * manager sont renvoyées en chemin relatif (`/api/v1/...`) : tel quel, le
 * navigateur le résoudrait sur l'origine du frontend, où il n'y a rien. Les
 * URL externes saisies à la main, elles, sont déjà absolues et passent
 * inchangées.
 */
export function mediaUrl(url: string | null): string | null {
  if (!url) return null;
  return url.startsWith("/") ? `${API_URL}${url}` : url;
}

/**
 * Lien direct vers la facture PDF d'une commande payée — ouvrable tel quel
 * dans un navigateur (scan du QR affiché après paiement), donc le jeton
 * voyage en paramètre plutôt qu'en en-tête `X-Order-Token` (confirmations de
 * paiement, 2026-08-19).
 */
export function invoiceUrl(orderId: number, orderToken: string): string {
  return `${API_URL}/api/v1/orders/${orderId}/invoice?token=${encodeURIComponent(orderToken)}`;
}

export const api = {
  // Fiche complète — écrans staff uniquement, sous JWT.
  getRestaurant: (restaurantId: number) => request<Restaurant>(`/api/v1/restaurants/${restaurantId}`),
  // Vue client, liée à la table scannée. La lecture par identifiant était
  // publique et incrémentale : elle listait tous les établissements clients.
  getRestaurantByToken: (qrToken: string) =>
    request<RestaurantPublic>(`/api/v1/restaurants/by-token/${qrToken}`),
  getTableByToken: (qrToken: string) => request<Table>(`/api/v1/tables/by-token/${qrToken}`),
  listTables: (restaurantId: number) => request<Table[]>(`/api/v1/tables/by-restaurant/${restaurantId}`),
  createTable: (payload: { restaurant_id: number; label: string; zone?: string | null }) =>
    request<Table>("/api/v1/tables", { method: "POST", body: JSON.stringify(payload) }),
  updateTable: (tableId: number, payload: { label: string; zone?: string | null }) =>
    request<Table>(`/api/v1/tables/${tableId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  // Affiche QR en PDF pour les tables ajoutées en self-service, à imprimer et
  // coller en salle — pas de chevalet fourni à l'installation dans ce cas,
  // contrairement aux pilotes de setup_restaurant.py (2026-08-20).
  downloadTablePoster: (tableId: number) => requestBlob(`/api/v1/tables/${tableId}/poster`),
  // Dashboard manager uniquement, sous JWT — la lecture par identifiant était
  // publique et incrémentale : la carte et les prix de n'importe quel
  // établissement se lisaient sans jeton (S-1, audit 2026-08-18).
  getMenu: (restaurantId: number) => request<MenuItem[]>(`/api/v1/menu-items/by-restaurant/${restaurantId}`),
  // Vue client, liée à la table scannée — voir getMenuByToken plus bas.
  // { id du plat: [ids proposés] } — une seule requête pour toute la carte,
  // le menu client se charge d'un coup sur une connexion mobile de salle.
  getMenuSuggestions: (restaurantId: number) =>
    request<Record<string, number[]>>(`/api/v1/menu-items/by-restaurant/${restaurantId}/suggestions`),
  getMenuByToken: (qrToken: string) => request<MenuItem[]>(`/api/v1/menu-items/by-table/${qrToken}`),
  getMenuSuggestionsByToken: (qrToken: string) =>
    request<Record<string, number[]>>(`/api/v1/menu-items/by-table/${qrToken}/suggestions`),
  setMenuSuggestions: (itemId: number, suggestedItemIds: number[]) =>
    request<{ menu_item_id: number; suggested_items: MenuItem[] }>(
      `/api/v1/menu-items/${itemId}/suggestions`,
      { method: "PUT", body: JSON.stringify({ suggested_item_ids: suggestedItemIds }) }
    ),
  // Remplacement en bloc de tous les groupes d'options d'un article — même
  // principe que setMenuSuggestions (France, MARCHE_FRANCE.md phase F5/A2).
  setMenuItemOptionGroups: (
    itemId: number,
    groups: { name: string; min_select: number; max_select: number; options: { name: string; price_delta: number }[] }[]
  ) =>
    request<MenuItem>(`/api/v1/menu-items/${itemId}/option-groups`, {
      method: "PUT",
      body: JSON.stringify({ groups }),
    }),
  // Vocabulaire de régimes du restaurant, remplacement en bloc (France,
  // 2026-08-26 : demande de Wassim).
  getMenuRegimes: (restaurantId: number) =>
    request<MenuRegime[]>(`/api/v1/menu-items/by-restaurant/${restaurantId}/regimes`),
  setMenuRegimes: (restaurantId: number, names: string[]) =>
    request<MenuRegime[]>(`/api/v1/menu-items/by-restaurant/${restaurantId}/regimes`, {
      method: "PUT",
      body: JSON.stringify({ names }),
    }),
  setMenuItemRegimes: (itemId: number, regimeIds: number[]) =>
    request<MenuItem>(`/api/v1/menu-items/${itemId}/regimes`, {
      method: "PUT",
      body: JSON.stringify({ regime_ids: regimeIds }),
    }),
  login: (email: string, password: string) =>
    request<LoginResponse>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (payload: {
    restaurant_name: string;
    manager_name: string;
    email: string;
    password: string;
    tier: SubscriptionTier;
  }) => request<LoginResponse>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  createDemoSession: () => request<DemoSession>("/api/v1/demo/sessions", { method: "POST" }),
  // Offre de lancement (2026-08-21) : public, interrogé par /signup avant
  // même l'inscription pour savoir s'il faut afficher la bannière.
  getLaunchPromoStatus: () => request<LaunchPromoStatus>("/api/v1/auth/launch-promo"),
  me: () => request<Staff>("/api/v1/auth/me"),
  listStaff: (restaurantId: number) => request<Staff[]>(`/api/v1/staff/by-restaurant/${restaurantId}`),
  createStaff: (payload: { name: string; email: string; role: StaffRole; password?: string }) =>
    request<StaffCreated>("/api/v1/staff", { method: "POST", body: JSON.stringify(payload) }),
  updateStaff: (staffId: number, payload: { name?: string; role?: StaffRole; is_active?: boolean }) =>
    request<Staff>(`/api/v1/staff/${staffId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  resetStaffPassword: (staffId: number) =>
    request<StaffCreated>(`/api/v1/staff/${staffId}/reset-password`, { method: "POST" }),
  createMenuItem: (payload: {
    restaurant_id: number;
    name: string;
    description?: string | null;
    category?: string;
    price: number;
    spice_level?: number;
    allergens?: string | null;
    is_halal?: boolean;
  }) => request<MenuItem>("/api/v1/menu-items", { method: "POST", body: JSON.stringify(payload) }),
  // `image_url` n'est pas éditable ici : le backend rejette le champ (422),
  // seules les routes /image gèrent la photo — voir MenuItemUpdate côté serveur.
  updateMenuItem: (
    itemId: number,
    payload: Partial<Pick<MenuItem, "name" | "description" | "category" | "price" | "spice_level" | "allergens" | "is_halal">>
  ) => request<MenuItem>(`/api/v1/menu-items/${itemId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  setMenuItemAvailability: (itemId: number, isAvailable: boolean) =>
    request<MenuItem>(`/api/v1/menu-items/${itemId}/availability`, {
      method: "PATCH",
      body: JSON.stringify({ is_available: isAvailable }),
    }),
  deleteMenuItem: (itemId: number) => request<void>(`/api/v1/menu-items/${itemId}`, { method: "DELETE" }),
  uploadMenuItemPhoto: (itemId: number, photo: Blob) => {
    const form = new FormData();
    form.append("file", photo, "photo.jpg");
    return request<MenuItem>(`/api/v1/menu-items/${itemId}/image`, { method: "PUT", body: form });
  },
  deleteMenuItemPhoto: (itemId: number) =>
    request<MenuItem>(`/api/v1/menu-items/${itemId}/image`, { method: "DELETE" }),
  importMenuCsv: (content: string, replaceExisting: boolean) =>
    request<MenuCsvImportResult>("/api/v1/menu-items/import-csv", {
      method: "POST",
      body: JSON.stringify({ content, replace_existing: replaceExisting }),
    }),
  createOrder: (payload: {
    // Le token du QR scanné, d'où le backend déduit la table et le restaurant :
    // aucun identifiant numérique n'est envoyé par le client (Phase 12.2).
    qr_token: string;
    items: OrderItemPayload[];
    scheduled_for?: string | null;
    loyalty_phone?: string | null;
    loyalty_birth_date?: string | null;
    // Identifiant du panier, fabriqué au moment où le client le compose : c'est
    // lui qui fait qu'un renvoi (double clic, file hors ligne rejouée) retombe
    // sur la même commande au lieu d'en faire préparer une seconde.
    client_order_id?: string | null;
  }) => request<OrderCreated>("/api/v1/orders", { method: "POST", body: JSON.stringify(payload) }),
  getOrder: (orderId: number, orderToken: string) =>
    request<Order>(`/api/v1/orders/${orderId}`, { headers: orderHeaders(orderToken) }),
  /**
   * Édition directe par le client — uniquement tant que la commande est
   * encore en attente de confirmation (409 `ORDER_NOT_MODIFIABLE` sinon, à
   * rejouer vers `requestModification`). Le panier envoyé remplace
   * entièrement le contenu de la commande, jamais un delta.
   */
  updateOrderItems: (orderId: number, orderToken: string, items: OrderItemPayload[]) =>
    request<Order>(`/api/v1/orders/${orderId}/items`, {
      method: "PUT",
      headers: orderHeaders(orderToken),
      body: JSON.stringify({ items }),
    }),
  /**
   * Fenêtre 2 — la commande est déjà confirmée : ceci n'applique rien tout de
   * suite, ça crée une demande que le serveur doit valider avec la cuisine.
   * Même forme de panier que `updateOrderItems`.
   */
  requestModification: (orderId: number, orderToken: string, items: OrderItemPayload[]) =>
    request<ModificationRequest>(`/api/v1/orders/${orderId}/modification-requests`, {
      method: "POST",
      headers: orderHeaders(orderToken),
      body: JSON.stringify({ items }),
    }),
  listPendingModificationRequests: (restaurantId: number) =>
    request<ModificationRequest[]>(
      `/api/v1/orders/by-restaurant/${restaurantId}/pending-modification-requests`
    ),
  resolveModificationRequest: (
    orderId: number,
    requestId: number,
    decisions: { line_id: number; accepted: boolean }[]
  ) =>
    request<ModificationRequest>(`/api/v1/orders/${orderId}/modification-requests/${requestId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ decisions }),
    }),
  listActiveOrders: (restaurantId: number) =>
    request<Order[]>(`/api/v1/orders/by-restaurant/${restaurantId}/active`),
  claimOrder: (orderId: number) => request<Order>(`/api/v1/orders/${orderId}/claim`, { method: "POST" }),
  confirmOrder: (orderId: number) => request<Order>(`/api/v1/orders/${orderId}/confirm`, { method: "POST" }),
  sendToKitchen: (orderId: number) =>
    request<Order>(`/api/v1/orders/${orderId}/send-to-kitchen`, { method: "POST" }),
  startPreparation: (orderId: number) =>
    request<Order>(`/api/v1/orders/${orderId}/start-preparation`, { method: "POST" }),
  markReady: (orderId: number) => request<Order>(`/api/v1/orders/${orderId}/mark-ready`, { method: "POST" }),
  markServed: (orderId: number) => request<Order>(`/api/v1/orders/${orderId}/mark-served`, { method: "POST" }),
  getMyShift: () => request<MyShift>("/api/v1/stats/ma-soiree"),
  getPlan: (restaurantId: number) => request<PlanTable[]>(`/api/v1/tables/plan/${restaurantId}`),
  savePlan: (
    restaurantId: number,
    placements: { table_id: number; pos_x: number; pos_y: number; shape: TableShape; seats: number }[]
  ) =>
    request<Table[]>(`/api/v1/tables/plan/${restaurantId}`, {
      method: "PUT",
      body: JSON.stringify({ placements }),
    }),
  getDashboardStats: (restaurantId: number, date?: string) =>
    request<DashboardStats>(
      `/api/v1/stats/dashboard/${restaurantId}${date ? `?date=${date}` : ""}`
    ),
  getProofStats: (restaurantId: number, start?: string, end?: string) => {
    const params = new URLSearchParams();
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    const query = params.toString();
    return request<ProofStats>(`/api/v1/stats/preuve/${restaurantId}${query ? `?${query}` : ""}`);
  },
  getTeamReport: (restaurantId: number, start?: string, end?: string) => {
    const params = new URLSearchParams();
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    const query = params.toString();
    return request<TeamReport>(`/api/v1/stats/equipe/${restaurantId}${query ? `?${query}` : ""}`);
  },
  getKitchenTodayCount: (restaurantId: number) =>
    request<KitchenTodayCount>(`/api/v1/stats/kitchen-today-count/${restaurantId}`),
  payByCard: (orderId: number, tipAmount: number, orderToken: string, customerEmail?: string) =>
    request<Order>(`/api/v1/orders/${orderId}/pay/card`, {
      method: "POST",
      body: JSON.stringify({ tip_amount: tipAmount, customer_email: customerEmail || undefined }),
      headers: orderHeaders(orderToken),
    }),
  requestCashPayment: (orderId: number, tipAmount: number, orderToken: string, customerEmail?: string) =>
    request<Order>(`/api/v1/orders/${orderId}/pay/cash`, {
      method: "POST",
      body: JSON.stringify({ tip_amount: tipAmount, customer_email: customerEmail || undefined }),
      headers: orderHeaders(orderToken),
    }),
  confirmCashPayment: (orderId: number) =>
    request<Order>(`/api/v1/orders/${orderId}/pay/cash/confirm`, { method: "POST" }),
  // Carte physique : le client demande, un serveur apporte le terminal —
  // même mécanique que les espèces, moyen distinct (2026-08-19).
  requestCardTerminalPayment: (orderId: number, tipAmount: number, orderToken: string, customerEmail?: string) =>
    request<Order>(`/api/v1/orders/${orderId}/pay/card-terminal`, {
      method: "POST",
      body: JSON.stringify({ tip_amount: tipAmount, customer_email: customerEmail || undefined }),
      headers: orderHeaders(orderToken),
    }),
  confirmCardTerminalPayment: (orderId: number) =>
    request<Order>(`/api/v1/orders/${orderId}/pay/card-terminal/confirm`, { method: "POST" }),
  listPendingCardTerminalPayments: (restaurantId: number) =>
    request<Order[]>(`/api/v1/orders/by-restaurant/${restaurantId}/pending-card-terminal-payments`),
  // Filet de sécurité appelé au retour de Konnect (`?konnect=success`) : en
  // dev, Konnect ne peut jamais joindre le webhook sur localhost.
  checkCardPayment: (orderId: number, orderToken: string) =>
    request<Order>(`/api/v1/orders/${orderId}/pay/card/check`, {
      method: "POST",
      headers: orderHeaders(orderToken),
    }),
  listPendingCashPayments: (restaurantId: number) =>
    request<Order[]>(`/api/v1/orders/by-restaurant/${restaurantId}/pending-cash-payments`),
  setRamadanMode: (restaurantId: number, enabled: boolean, iftarTime: string | null) =>
    request<Restaurant>(`/api/v1/restaurants/${restaurantId}/ramadan-mode`, {
      method: "PATCH",
      body: JSON.stringify({ enabled, iftar_time: iftarTime }),
    }),
  setCafeMode: (restaurantId: number, enabled: boolean) =>
    request<Restaurant>(`/api/v1/restaurants/${restaurantId}/cafe-mode`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),
  setKitchenSound: (restaurantId: number, enabled: boolean) =>
    request<Restaurant>(`/api/v1/restaurants/${restaurantId}/kitchen-sound`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),
  // Bannière de couverture + logo du menu client (Phase D1 de
  // ROADMAP_DESIGN.md) — ouverts à tous les paliers, contrairement à la
  // photo des plats.
  uploadRestaurantCoverPhoto: (restaurantId: number, photo: Blob) => {
    const form = new FormData();
    form.append("file", photo, "couverture.jpg");
    return request<Restaurant>(`/api/v1/restaurants/${restaurantId}/cover-photo`, { method: "PUT", body: form });
  },
  deleteRestaurantCoverPhoto: (restaurantId: number) =>
    request<Restaurant>(`/api/v1/restaurants/${restaurantId}/cover-photo`, { method: "DELETE" }),
  uploadRestaurantLogo: (restaurantId: number, photo: Blob) => {
    const form = new FormData();
    form.append("file", photo, "logo.jpg");
    return request<Restaurant>(`/api/v1/restaurants/${restaurantId}/logo`, { method: "PUT", body: form });
  },
  deleteRestaurantLogo: (restaurantId: number) =>
    request<Restaurant>(`/api/v1/restaurants/${restaurantId}/logo`, { method: "DELETE" }),
  setSocialLinks: (
    restaurantId: number,
    links: {
      facebook_url: string | null;
      instagram_url: string | null;
      tiktok_url: string | null;
      whatsapp_url: string | null;
      google_review_url: string | null;
    }
  ) =>
    request<Restaurant>(`/api/v1/restaurants/${restaurantId}/social-links`, {
      method: "PATCH",
      body: JSON.stringify(links),
    }),
  setLegalInfo: (
    restaurantId: number,
    info: { legal_address: string | null; tax_id: string | null; vat_number: string | null }
  ) =>
    request<Restaurant>(`/api/v1/restaurants/${restaurantId}/legal-info`, {
      method: "PATCH",
      body: JSON.stringify(info),
    }),
  // Connexion du wallet Konnect PROPRE au restaurant (modèle direct,
  // 2026-08-19) — jamais réaffiché après coup, seul `konnect_configured` le
  // confirme ensuite (voir Restaurant).
  setKonnectCredentials: (restaurantId: number, apiKey: string, walletId: string) =>
    request<Restaurant>(`/api/v1/restaurants/${restaurantId}/konnect-credentials`, {
      method: "PUT",
      body: JSON.stringify({ api_key: apiKey, wallet_id: walletId }),
    }),
  // Démarre (ou reprend) l'onboarding Stripe Connect — renvoie l'URL hébergée
  // par Stripe où rediriger le manager, jamais un formulaire local (voir
  // tenants/router.py::start_stripe_connect).
  startStripeConnect: (restaurantId: number) =>
    request<{ onboarding_url: string }>(`/api/v1/restaurants/${restaurantId}/stripe-connect/start`, {
      method: "POST",
    }),
  // Portail Stripe hébergé (mode Netflix, 2026-09-02) — annuler, changer de
  // moyen de paiement, voir ses factures. Jamais un écran à écrire côté
  // Tawla, voir tenants/router.py::open_billing_portal.
  openBillingPortal: (restaurantId: number) =>
    request<{ portal_url: string }>(`/api/v1/restaurants/${restaurantId}/subscription/manage`, {
      method: "POST",
    }),
  // Palier INFÉRIEUR à la prochaine échéance, en restant abonné — distinct
  // d'une annulation complète (mode Netflix, 2026-09-02). Voir
  // tenants/router.py::schedule_subscription_downgrade.
  scheduleDowngrade: (restaurantId: number, tier: SubscriptionTier) =>
    request<Restaurant>(`/api/v1/restaurants/${restaurantId}/subscription/downgrade`, {
      method: "POST",
      body: JSON.stringify({ tier }),
    }),
  // Résiliation SIMULÉE, réservée aux établissements de démo — pas de vrai
  // portail Stripe à ouvrir pour un compte sans vrai abonnement, voir
  // tenants/router.py::simulate_subscription_cancellation.
  simulateSubscriptionCancel: (restaurantId: number) =>
    request<Restaurant>(`/api/v1/restaurants/${restaurantId}/subscription/simulate-cancel`, { method: "POST" }),
  startSubscriptionCheckout: (restaurantId: number, tier: SubscriptionTier) =>
    request<SubscriptionCheckoutResult>(`/api/v1/restaurants/${restaurantId}/subscription/checkout`, {
      method: "POST",
      body: JSON.stringify({ tier }),
    }),
  checkSubscriptionPayment: (restaurantId: number) =>
    request<Restaurant>(`/api/v1/restaurants/${restaurantId}/subscription/check`, { method: "POST" }),
  // Le token du QR, jamais des identifiants : sans ça, une boucle sur
  // `table_id` faisait sonner tous les écrans serveur, depuis n'importe où.
  callWaiter: (qrToken: string) =>
    request<WaiterCall>("/api/v1/waiter-calls", {
      method: "POST",
      body: JSON.stringify({ qr_token: qrToken }),
    }),
  listPendingWaiterCalls: (restaurantId: number) =>
    request<WaiterCall[]>(`/api/v1/waiter-calls/by-restaurant/${restaurantId}/pending`),
  resolveWaiterCall: (callId: number) =>
    request<WaiterCall>(`/api/v1/waiter-calls/${callId}/resolve`, { method: "POST" }),
  // Lecture seule et liée à la table scannée depuis la Phase 19.1 : la route
  // ne crée plus de fiche et répond 404 sur un numéro inconnu (première
  // visite). La date de naissance, elle, part avec la commande.
  lookupLoyalty: (qrToken: string, phoneNumber: string) =>
    request<LoyaltyMember>("/api/v1/loyalty/lookup", {
      method: "POST",
      body: JSON.stringify({ qr_token: qrToken, phone_number: phoneNumber }),
    }),
  getLoyaltyMemberForStaff: (restaurantId: number, phoneNumber: string) =>
    request<LoyaltyMember>(
      `/api/v1/loyalty/by-restaurant/${restaurantId}/member?phone_number=${encodeURIComponent(phoneNumber)}`
    ),
  redeemLoyaltyReward: (memberId: number) =>
    request<LoyaltyMember>(`/api/v1/loyalty/${memberId}/redeem`, { method: "POST" }),
  getVapidPublicKey: () => request<{ public_key: string }>("/api/v1/notifications/vapid-public-key"),
  savePushSubscription: (orderId: number, subscription: PushSubscriptionJSON, orderToken: string) =>
    request<void>(`/api/v1/orders/${orderId}/push-subscription`, {
      method: "POST",
      body: JSON.stringify(subscription),
      headers: orderHeaders(orderToken),
    }),
  // Abonnement du membre du personnel connecté (JWT déjà attaché par
  // request()) — pendant de savePushSubscription côté équipe, voir
  // app/staff/page.tsx.
  saveStaffPushSubscription: (subscription: PushSubscriptionJSON) =>
    request<void>("/api/v1/auth/push-subscription", {
      method: "POST",
      body: JSON.stringify(subscription),
    }),
};

export function wsUrl(path: string): string {
  return `${API_URL.replace(/^http/, "ws")}${path}`;
}

/**
 * Canaux WebSocket staff et cuisine : authentifiés depuis la Phase 12.2. Le
 * token passe en paramètre de requête et non en en-tête — la poignée de main
 * WebSocket du navigateur ne permet pas d'en-tête personnalisé.
 */
export function staffWsUrl(path: string): string | null {
  const token = getToken();
  if (!token) return null;
  return `${wsUrl(path)}?token=${encodeURIComponent(token)}`;
}

/** Canal de suivi d'une commande : autorisé par son `public_token`. */
export function orderWsUrl(path: string, orderToken: string): string {
  return `${wsUrl(path)}?token=${encodeURIComponent(orderToken)}`;
}
