import posthog from "posthog-js";

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://eu.i.posthog.com";

// Un seul projet PostHog pour dev/preview ET prod (limite du plan actuel :
// 1 projet) — chaque événement porte donc une propriété `env` pour séparer
// le bruit de dev/démo des vrais visiteurs dans les insights, plutôt qu'une
// séparation physique par projet. Liste explicite (pas de détection
// automatique Vercel). TODO : ajouter les vrais domaines (tawla.fr, tawla.tn
// ou autres — pas encore confirmés) une fois réservés.
const PRODUCTION_HOSTS = ["tawla-fr.vercel.app", "tawla-eight.vercel.app"];

function currentEnv(): "production" | "development" {
  if (typeof window === "undefined") return "development";
  return PRODUCTION_HOSTS.includes(window.location.hostname) ? "production" : "development";
}

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
  // Super property : attachée automatiquement à tout événement capturé dès
  // maintenant, sans y penser à chaque site d'appel de trackEvent/trackPageview.
  posthog.register({ env: currentEnv() });
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
