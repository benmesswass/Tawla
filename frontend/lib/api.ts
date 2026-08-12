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
  loyalty_phone: string | null;
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

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...authHeaders() },
    ...options,
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
    restaurant_id: number;
    table_id: number;
    items: { menu_item_id: number; quantity: number; notes?: string | null; is_shared?: boolean }[];
    scheduled_for?: string | null;
    loyalty_phone?: string | null;
  }) => request<Order>("/api/v1/orders", { method: "POST", body: JSON.stringify(payload) }),
  getOrder: (orderId: number) => request<Order>(`/api/v1/orders/${orderId}`),
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
  payByCard: (orderId: number, tipAmount: number) =>
    request<Order>(`/api/v1/orders/${orderId}/pay/card`, {
      method: "POST",
      body: JSON.stringify({ tip_amount: tipAmount }),
    }),
  requestCashPayment: (orderId: number) =>
    request<Order>(`/api/v1/orders/${orderId}/pay/cash`, { method: "POST" }),
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
  savePushSubscription: (orderId: number, subscription: PushSubscriptionJSON) =>
    request<void>(`/api/v1/orders/${orderId}/push-subscription`, {
      method: "POST",
      body: JSON.stringify(subscription),
    }),
};

export function wsUrl(path: string): string {
  return `${API_URL.replace(/^http/, "ws")}${path}`;
}
