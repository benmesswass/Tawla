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
};

export type Table = {
  id: number;
  restaurant_id: number;
  label: string;
  qr_token: string;
  assigned_staff_id: number | null;
};

export type Restaurant = {
  id: number;
  name: string;
  slug: string;
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

export type Order = {
  id: number;
  restaurant_id: number;
  table_id: number;
  status: OrderStatus;
  taken_by_staff_id: number | null;
  taken_by_staff_name: string | null;
  items: {
    id: number;
    menu_item_id: number;
    menu_item_name: string;
    unit_price: number;
    quantity: number;
    notes: string | null;
  }[];
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
  getMenu: (restaurantId: number) => request<MenuItem[]>(`/api/v1/menu-items/by-restaurant/${restaurantId}`),
  login: (email: string, password: string) =>
    request<LoginResponse>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request<Staff>("/api/v1/auth/me"),
  createMenuItem: (payload: {
    restaurant_id: number;
    name: string;
    description?: string | null;
    category?: string;
    price: number;
    image_url?: string | null;
  }) => request<MenuItem>("/api/v1/menu-items", { method: "POST", body: JSON.stringify(payload) }),
  updateMenuItem: (
    itemId: number,
    payload: Partial<Pick<MenuItem, "name" | "description" | "category" | "price" | "image_url">>
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
    items: { menu_item_id: number; quantity: number; notes?: string | null }[];
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
};

export function wsUrl(path: string): string {
  return `${API_URL.replace(/^http/, "ws")}${path}`;
}
