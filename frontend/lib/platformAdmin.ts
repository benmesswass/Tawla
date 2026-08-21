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

export type PlatformAdminInfo = {
  id: number;
  email: string;
  name: string;
  is_active: boolean;
};

export type RestaurantSummary = {
  id: number;
  name: string;
  slug: string;
  // Palier réellement actif (`effective_tier()` côté serveur) — un palier
  // payé en ligne expiré y apparaît déjà retombé à "essentiel".
  effective_tier: SubscriptionTier;
  created_at: string;
  orders_count: number;
  revenue_tnd: number;
  last_order_at: string | null;
  dashboard_views_last_7d: number;
  // Activation, promo personnalisée et offre de lancement (2026-08-20/21bis)
  // — voir la section Promo de cette page et backend Restaurant.is_active/
  // custom_promo_discount_percent/launch_promo_discount_percent/
  // has_paid_for_subscription.
  is_active: boolean;
  custom_promo_discount_percent: number | null;
  custom_promo_ends_at: string | null;
  launch_promo_discount_percent: number | null;
  has_paid_for_subscription: boolean;
};

export type WeeklyPoint = {
  week_start: string;
  restaurants_created: number;
};

/**
 * Les chiffres indispensables de l'opérateur — même discipline que
 * `PeriodProof` (`lib/api.ts`) : volontairement pas un chiffre de plus.
 */
export type PlatformOverview = {
  generated_at: string;

  restaurants_total: number;
  restaurants_created_last_30d: number;

  restaurants_by_tier: Record<SubscriptionTier, number>;

  // MRR réel : paliers payés en ligne et toujours actifs uniquement, jamais
  // les pilotes fixés à la main par setup_restaurant.py.
  mrr_tnd: number;
  paying_restaurants_count: number;

  // Rétention (signal anti-résiliation, ROADMAP.md Phase 24).
  dashboard_views_last_7d: number;
  restaurants_active_last_7d: number;

  orders_last_7d: number;
  gmv_last_7d_tnd: number;

  // `null` = aucune commande sur la période, pas 0%.
  lost_orders_rate_last_7d: number | null;

  weekly_signups: WeeklyPoint[];
  restaurants: RestaurantSummary[];
};

/**
 * Réglages de l'offre de lancement (2026-08-21) — `grants_used` n'est
 * visible qu'ici (jamais sur l'endpoint public /auth/launch-promo, qui ne
 * renvoie qu'un booléen de disponibilité pour ne pas exposer la vitesse
 * d'inscription de Tawla).
 */
export type LaunchCampaign = {
  discount_percent: number;
  max_grants: number;
  grants_used: number;
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
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string; admin: PlatformAdminInfo }>(
      "/api/v1/platform-admin/login",
      { method: "POST", body: JSON.stringify({ email, password }) }
    ),
  getOverview: () => request<PlatformOverview>("/api/v1/platform-admin/overview"),
  getLaunchCampaign: () => request<LaunchCampaign>("/api/v1/platform-admin/launch-campaign"),
  setLaunchCampaign: (discountPercent: number, maxGrants: number) =>
    request<LaunchCampaign>("/api/v1/platform-admin/launch-campaign", {
      method: "PUT",
      body: JSON.stringify({ discount_percent: discountPercent, max_grants: maxGrants }),
    }),
  // `durationDays = 0` retire la promo en cours.
  setRestaurantPromo: (restaurantId: number, discountPercent: number, durationDays: number) =>
    request<{ custom_promo_discount_percent: number | null; custom_promo_ends_at: string | null }>(
      `/api/v1/platform-admin/restaurants/${restaurantId}/promo`,
      { method: "PUT", body: JSON.stringify({ discount_percent: discountPercent, duration_days: durationDays }) }
    ),
  // Aucun `secret` envoyé ici : `request()` attache déjà le JWT admin en
  // cours (en-tête Authorization), qui suffit à autoriser côté serveur —
  // voir backend/app/modules/platform_admin/router.py::create_admin.
  createAdmin: (email: string, name: string, password: string) =>
    request<PlatformAdminInfo>("/api/v1/platform-admin/admins", {
      method: "POST",
      body: JSON.stringify({ email, name, password }),
    }),
};
