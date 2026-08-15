import { clearToken, getToken } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
};

export type Restaurant = RestaurantPublic & {
  slug: string;
  kitchen_sound_enabled: boolean;
  subscription_tier: SubscriptionTier;
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

export type OrderStatus =
  | "pending_confirmation"
  | "confirmed"
  | "sent_to_kitchen"
  | "in_preparation"
  | "ready"
  | "served"
  | "cancelled";

export type PaymentMethod = "card" | "cash";
export type PaymentStatus = "unpaid" | "pending" | "paid";

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
  scheduled_for: string | null;
  sent_to_kitchen_at: string | null;
  ready_at: string | null;
  // Présent uniquement sur les réponses servies au staff (routes sous JWT) :
  // la vue client ne porte plus de donnée personnelle depuis la Phase 12.2.
  loyalty_phone?: string | null;
  payment_method: PaymentMethod | null;
  payment_status: PaymentStatus;
  tip_amount: number;
  total_amount: number;
  items: {
    id: number;
    menu_item_id: number;
    menu_item_name: string;
    unit_price: number;
    quantity: number;
    notes: string | null;
    is_shared: boolean;
    from_suggestion: boolean;
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
};

export type StaffPerformance = {
  staff_id: number;
  staff_name: string;
  role: StaffRole;
  orders_taken: number;
};

export type TopMenuItem = { menu_item_name: string; quantity: number };
export type HourlyCount = { hour: number; count: number };

export type DashboardStats = {
  date: string;
  /** Les deux chiffres de tête (Phase 17.1) : ce que le patron vient chercher
   *  chaque soir, et celui qui justifie l'abonnement, posé juste à côté. */
  revenue_today: number;
  lost_orders_today: number;
  active_orders_count: number;
  timing: TimingStats;
  staff_performance: StaffPerformance[];
  top_items: TopMenuItem[];
  orders_by_hour: HourlyCount[];
};

export type KitchenTodayCount = { date: string; count: number };

/**
 * Les trois chiffres de preuve d'un pilote (Phase 13.3) : commandes perdues,
 * délai commande → cuisine, panier moyen. `null` sur les moyennes veut dire
 * « aucune donnée », pas zéro — la distinction compte devant un patron.
 */
export type PeriodProof = {
  start: string;
  end: string;
  orders_count: number;
  lost_orders_count: number;
  cancelled_count: number;
  abandoned_count: number;
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
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    // Après le spread : sinon des en-têtes passés dans `options` écrasent
    // silencieusement Content-Type et l'Authorization du staff.
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(options?.headers ?? {}) },
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
  getMenu: (restaurantId: number) => request<MenuItem[]>(`/api/v1/menu-items/by-restaurant/${restaurantId}`),
  // { id du plat: [ids proposés] } — une seule requête pour toute la carte,
  // le menu client se charge d'un coup sur une connexion mobile de salle.
  getMenuSuggestions: (restaurantId: number) =>
    request<Record<string, number[]>>(`/api/v1/menu-items/by-restaurant/${restaurantId}/suggestions`),
  setMenuSuggestions: (itemId: number, suggestedItemIds: number[]) =>
    request<{ menu_item_id: number; suggested_items: MenuItem[] }>(
      `/api/v1/menu-items/${itemId}/suggestions`,
      { method: "PUT", body: JSON.stringify({ suggested_item_ids: suggestedItemIds }) }
    ),
  login: (email: string, password: string) =>
    request<LoginResponse>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (payload: { restaurant_name: string; manager_name: string; email: string; password: string }) =>
    request<LoginResponse>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(payload) }),
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
    image_url?: string | null;
    spice_level?: number;
    allergens?: string | null;
    is_halal?: boolean;
  }) => request<MenuItem>("/api/v1/menu-items", { method: "POST", body: JSON.stringify(payload) }),
  updateMenuItem: (
    itemId: number,
    payload: Partial<
      Pick<
        MenuItem,
        "name" | "description" | "category" | "price" | "image_url" | "spice_level" | "allergens" | "is_halal"
      >
    >
  ) => request<MenuItem>(`/api/v1/menu-items/${itemId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  setMenuItemAvailability: (itemId: number, isAvailable: boolean) =>
    request<MenuItem>(`/api/v1/menu-items/${itemId}/availability`, {
      method: "PATCH",
      body: JSON.stringify({ is_available: isAvailable }),
    }),
  deleteMenuItem: (itemId: number) => request<void>(`/api/v1/menu-items/${itemId}`, { method: "DELETE" }),
  importMenuCsv: (content: string, replaceExisting: boolean) =>
    request<MenuCsvImportResult>("/api/v1/menu-items/import-csv", {
      method: "POST",
      body: JSON.stringify({ content, replace_existing: replaceExisting }),
    }),
  createOrder: (payload: {
    // Le token du QR scanné, d'où le backend déduit la table et le restaurant :
    // aucun identifiant numérique n'est envoyé par le client (Phase 12.2).
    qr_token: string;
    items: {
      menu_item_id: number;
      quantity: number;
      notes?: string | null;
      is_shared?: boolean;
      from_suggestion?: boolean;
    }[];
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
  payByCard: (orderId: number, tipAmount: number, orderToken: string) =>
    request<Order>(`/api/v1/orders/${orderId}/pay/card`, {
      method: "POST",
      body: JSON.stringify({ tip_amount: tipAmount }),
      headers: orderHeaders(orderToken),
    }),
  requestCashPayment: (orderId: number, orderToken: string) =>
    request<Order>(`/api/v1/orders/${orderId}/pay/cash`, {
      method: "POST",
      headers: orderHeaders(orderToken),
    }),
  confirmCashPayment: (orderId: number) =>
    request<Order>(`/api/v1/orders/${orderId}/pay/cash/confirm`, { method: "POST" }),
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
