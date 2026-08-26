/**
 * Couche marché — France, MARCHE_FRANCE.md phase F3. Miroir exact de
 * `app/core/markets.py` côté backend : même forme, mêmes deux marchés.
 *
 * Règle durable à partir d'ici : plus jamais de devise, de prix de palier ou
 * de taux en dur dans un composant — tout passe par `currentMarket`. Cette
 * étape pose l'objet ; le câblage (formateur monétaire, contenus par marché)
 * vient dans des PR suivantes.
 */
import type { SubscriptionTier } from "./api";

// Seule source de vérité pour « quels marchés existent » (France, Phase F4
// §5) — le sélecteur de pays et sa route de redirection en dépendent plutôt
// que de répéter la liste.
export const SUPPORTED_MARKET_CODES = ["tn", "fr"] as const;
export type SupportedMarketCode = (typeof SUPPORTED_MARKET_CODES)[number];

export type CurrencyConfig = {
  code: "TND" | "EUR";
  symbol: string;
  decimals: number;
  decimalSeparator: "." | ",";
};

export type MarketConfig = {
  code: SupportedMarketCode;
  name: string;
  currency: CurrencyConfig;
  // Identifiant IANA (pas un ZoneInfo — pas d'équivalent direct côté JS),
  // pour Intl.DateTimeFormat / date-fns-tz le jour du câblage du fuseau.
  timezone: string;
  languages: readonly string[];
  // Adaptateur technique branché — "none" tant que Stripe n'existe pas
  // (Phase F6), voir le commentaire équivalent dans core/markets.py pour la
  // distinction avec la décision "grisé en prod" de Wassim.
  paymentProvider: "konnect" | "stripe" | "none";
  // Hypothèse de départ pour la France (MARCHE_FRANCE.md §3.4, 49/89/149 €) —
  // jamais à annoncer publiquement avant validation en Phase F1.
  tierPrices: Record<SubscriptionTier, number>;
  vatRates: Record<string, number> | null;
  invoiceThreshold: number | null;
  // Liste fermée proposée dans le formulaire du dashboard manager (lib/menuCategories.ts)
  // — jamais validée côté backend (MenuItem.category est du texte libre), donc pas de
  // miroir dans core/markets.py : rien côté serveur n'en a besoin.
  menuCategories: readonly string[];
};

const TUNISIA: MarketConfig = {
  code: "tn",
  name: "Tunisie",
  currency: { code: "TND", symbol: "DT", decimals: 3, decimalSeparator: "." },
  timezone: "Africa/Tunis",
  languages: ["fr", "ar"],
  paymentProvider: "konnect",
  tierPrices: { essentiel: 49, pro: 89, business: 149 },
  vatRates: null,
  invoiceThreshold: null,
  menuCategories: ["Entrées", "Plats", "Desserts", "Boissons", "Ftour", "Autre"],
};

const FRANCE: MarketConfig = {
  code: "fr",
  name: "France",
  currency: { code: "EUR", symbol: "€", decimals: 2, decimalSeparator: "," },
  timezone: "Europe/Paris",
  languages: ["fr", "en"],
  paymentProvider: "none",
  tierPrices: { essentiel: 49, pro: 89, business: 149 },
  vatRates: { sur_place: 0.10, a_emporter: 0.055, alcool: 0.20 },
  invoiceThreshold: 25.0,
  // "Ftour" (Ramadan tunisien) retiré, sans objet en France ; remplacé par les
  // trois catégories de carte françaises usuelles (MARCHE_FRANCE.md §3.2).
  menuCategories: ["Entrées", "Plats", "Desserts", "Boissons", "Formules", "Vins", "À emporter", "Autre"],
};

const MARKETS: Record<string, MarketConfig> = { tn: TUNISIA, fr: FRANCE };

/** Résout un marché par code — `code` omis lit `NEXT_PUBLIC_MARKET` (défaut "tn"). */
export function getMarket(code?: string): MarketConfig {
  const resolved = (code ?? process.env.NEXT_PUBLIC_MARKET ?? "tn").toLowerCase();
  const market = MARKETS[resolved];
  if (!market) {
    throw new Error(`unknown market code: "${resolved}" (expected one of ${Object.keys(MARKETS).join(", ")})`);
  }
  return market;
}

// Chargé une fois au démarrage — un déploiement sert un seul marché
// (MARCHE_FRANCE.md §4, option B), jamais les deux à la fois.
export const currentMarket: MarketConfig = getMarket();
