import posthog from "posthog-js";

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://eu.i.posthog.com";

let initialized = false;

/**
 * Analytics produit (PostHog) — funnel démo → abonnement Tawla, pas une
 * fonctionnalité restaurateur/convive. Appelé une seule fois par
 * <Analytics /> au montage du layout racine. Dégradation gracieuse : sans
 * NEXT_PUBLIC_POSTHOG_KEY (voir .env.local.example), reste non initialisé —
 * trackEvent/trackPageview deviennent des no-op.
 */
export function initAnalytics() {
  if (initialized || !POSTHOG_KEY) return;
  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    capture_pageview: false,
    person_profiles: "identified_only",
  });
  initialized = true;
}

export function trackEvent(event: string, properties?: Record<string, unknown>) {
  if (!initialized) return;
  posthog.capture(event, properties);
}

export function trackPageview(url: string) {
  if (!initialized) return;
  posthog.capture("$pageview", { $current_url: url });
}
