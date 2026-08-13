import { getToken } from "@/lib/auth";

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
};

export type SubscriptionTier = "essentiel" | "pro" | "business";

export type Restaurant = {
  id: number;
  name: string;
  slug: string;
  ramadan_mode_enabled: boolean;
  iftar_time: string | null;
  cafe_mode_enabled: boolean;
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
  status: OrderStatus;
  taken_by_staff_id: number | null;
  taken_by_staff_name: string | null;
  scheduled_for: string | null;
  sent_to_kitchen_at: string | null;
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
  active_orders_count: number;
  timing: TimingStats;
  staff_performance: StaffPerformance[];
  top_items: TopMenuItem[];
  orders_by_hour: HourlyCount[];
};

export type KitchenTodayCount = { date: string; count: number };

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
      throw new ApiError(detail.code, detail.message ?? `Erreur API (${res.status})`, detail);
    }
    throw new ApiError("UNKNOWN", typeof detail === "string" ? detail : `Erreur API (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  getRestaurant: (restaurantId: number) => request<Restaurant>(`/api/v1/restaurants/${restaurantId}`),
  getTableByToken: (qrToken: string) => request<Table>(`/api/v1/tables/by-token/${qrToken}`),
  listTables: (restaurantId: number) => request<Table[]>(`/api/v1/tables/by-restaurant/${restaurantId}`),
  createTable: (payload: { restaurant_id: number; label: string; zone?: string | null }) =>
    request<Table>("/api/v1/tables", { method: "POST", body: JSON.stringify(payload) }),
  updateTable: (tableId: number, payload: { label: string; zone?: string | null }) =>
    request<Table>(`/api/v1/tables/${tableId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  getMenu: (restaurantId: number) => request<MenuItem[]>(`/api/v1/menu-items/by-restaurant/${restaurantId}`),
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
  createOrder: (payload: {
    // Le token du QR scanné, d'où le backend déduit la table et le restaurant :
    // aucun identifiant numérique n'est envoyé par le client (Phase 12.2).
    qr_token: string;
    items: { menu_item_id: number; quantity: number; notes?: string | null; is_shared?: boolean }[];
    scheduled_for?: string | null;
    loyalty_phone?: string | null;
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
  getDashboardStats: (restaurantId: number, date?: string) =>
    request<DashboardStats>(
      `/api/v1/stats/dashboard/${restaurantId}${date ? `?date=${date}` : ""}`
    ),
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
  callWaiter: (restaurantId: number, tableId: number) =>
    request<WaiterCall>("/api/v1/waiter-calls", {
      method: "POST",
      body: JSON.stringify({ restaurant_id: restaurantId, table_id: tableId }),
    }),
  listPendingWaiterCalls: (restaurantId: number) =>
    request<WaiterCall[]>(`/api/v1/waiter-calls/by-restaurant/${restaurantId}/pending`),
  resolveWaiterCall: (callId: number) =>
    request<WaiterCall>(`/api/v1/waiter-calls/${callId}/resolve`, { method: "POST" }),
  lookupLoyalty: (restaurantId: number, phoneNumber: string, birthDate?: string | null) =>
    request<LoyaltyMember>("/api/v1/loyalty/lookup", {
      method: "POST",
      body: JSON.stringify({ restaurant_id: restaurantId, phone_number: phoneNumber, birth_date: birthDate }),
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
