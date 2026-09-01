import posthog from "posthog-js";
import { currentMarket } from "@/lib/market";

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://eu.i.posthog.com";

// Un seul projet PostHog pour dev/staging/prod (limite du plan actuel :
// 1 projet) — chaque événement porte donc une propriété `env` pour séparer
// le bruit de dev/démo des vrais visiteurs dans les insights, plutôt qu'une
// séparation physique par projet. Listes explicites (pas de détection
// automatique Vercel).
//
// `tawla-fr.vercel.app`/`tawla-eight.vercel.app` sont les URLs Vercel
// actuelles — déjà en ligne, mais pas le vrai domaine public : "staging",
// pas "production". `PRODUCTION_HOSTS` reste vide tant que le vrai domaine
// (tawla.fr, tawla.tn ou autre — pas encore réservé) n'est pas confirmé ;
// le dashboard admin (posthog_query.py, filtré sur env=production) restera
// donc vide jusque-là, volontairement.
const STAGING_HOSTS = ["tawla-fr.vercel.app", "tawla-eight.vercel.app"];
const PRODUCTION_HOSTS: string[] = [];

function currentEnv(): "production" | "staging" | "development" {
  if (typeof window === "undefined") return "development";
  const host = window.location.hostname;
  if (PRODUCTION_HOSTS.includes(host)) return "production";
  if (STAGING_HOSTS.includes(host)) return "staging";
  return "development";
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
  // Super properties : attachées automatiquement à tout événement capturé
  // dès maintenant, sans y penser à chaque site d'appel de trackEvent/
  // trackPageview. `market` (tn/fr) : jamais mélanger les deux marchés
  // dans les insights — même principe que `env` ci-dessus.
  posthog.register({ env: currentEnv(), market: currentMarket.code });
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
