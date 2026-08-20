import { API_URL } from "@/lib/api";

/**
 * Client isolé du dashboard plateforme (vue cross-tenant de l'opérateur,
 * `/admin`) — volontairement séparé de `lib/api.ts` et de sa session staff
 * (`lib/auth.ts`). Les deux domaines ne doivent jamais se mélanger : un 401
 * sur ce client ne doit jamais effacer le token staff ni rediriger vers
 * `/login`, et réciproquement.
 */
const TOKEN_KEY = "tawla_admin_token";

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setAdminToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAdminToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class PlatformAdminApiError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

export type SubscriptionTier = "essentiel" | "pro" | "business";

export type RestaurantSummary = {
  id: number;
  name: string;
  slug: string;
  subscription_tier: SubscriptionTier;
  created_at: string;
  orders_count: number;
  revenue_tnd: number;
  last_order_at: string | null;
};

export type WeeklyPoint = {
  week_start: string;
  restaurants_created: number;
  orders_count: number;
  revenue_tnd: number;
};

export type PlatformOverview = {
  generated_at: string;
  restaurants_total: number;
  restaurants_by_tier: Record<SubscriptionTier, number>;
  restaurants_created_last_30d: number;
  orders_total: number;
  orders_last_30d: number;
  revenue_total_tnd: number;
  revenue_last_30d_tnd: number;
  weekly: WeeklyPoint[];
  restaurants: RestaurantSummary[];
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAdminToken();
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail;
    const code = detail && typeof detail === "object" ? detail.code : "UNKNOWN";
    const message = detail && typeof detail === "object" ? detail.message : `Erreur API (${res.status})`;
    // Session admin devenue invalide (token expiré après 12h, ou secret
    // changé) : on efface uniquement le token admin, jamais le token staff —
    // ces deux sessions n'ont rien à voir l'une avec l'autre.
    if (res.status === 401 && token) {
      clearAdminToken();
    }
    throw new PlatformAdminApiError(code ?? "UNKNOWN", message ?? `Erreur API (${res.status})`);
  }
  return res.json();
}

export const platformAdminApi = {
  login: (password: string) =>
    request<{ access_token: string; token_type: string }>("/api/v1/platform-admin/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  getOverview: () => request<PlatformOverview>("/api/v1/platform-admin/overview"),
};
