/**
 * Configuration par marché (`NEXT_PUBLIC_MARKET=tn|fr`) — miroir frontend de
 * `backend/app/core/markets.py`. Un déploiement sert un seul marché, jamais
 * une bascule par requête : voir `MARCHE_FRANCE.md` §4 (architecture à deux
 * marchés — un dépôt, une couche marché, deux déploiements séparés).
 *
 * Plus jamais de devise, de décimales ou de symbole en dur ailleurs dans le
 * code — toujours `formatAmount()` d'ici (règle posée dans `CLAUDE.md`).
 */
export type MarketCode = "tn" | "fr";

export type Currency = {
  /** ISO 4217, ex: "TND", "EUR" — pas encore affiché nulle part, gardé pour l'export/la compta. */
  code: string;
  symbol: string;
  /** Précision réelle de la devise : 3 pour le TND (millimes), 2 pour l'EUR (centimes). */
  decimals: number;
  symbolBefore: boolean;
};

export type Market = {
  code: MarketCode;
  label: string;
  currency: Currency;
  /** Langues du parcours client, dans l'ordre d'affichage du sélecteur. */
  languages: readonly string[];
  /**
   * L'arbitrage S1 (ne pas être un système de caisse) / S2 (être conforme
   * ISCA) n'est PAS tranché avec l'expert-comptable (MARCHE_FRANCE.md §3.1,
   * C2). Passé à `true` le 2026-08-25 UNIQUEMENT pour la période de test
   * technique (compte Stripe Connect de test, aucun restaurant réel, aucun
   * vrai règlement) — à remettre à `false` avant toute exposition à de
   * vrais clients français tant que S1/S2 n'est pas écrit.
   */
  onlinePaymentAvailable: boolean;
};

const MARKETS: Record<MarketCode, Market> = {
  tn: {
    code: "tn",
    label: "Tunisie",
    currency: { code: "TND", symbol: "DT", decimals: 3, symbolBefore: false },
    languages: ["fr", "ar"],
    onlinePaymentAvailable: true,
  },
  fr: {
    code: "fr",
    label: "France",
    currency: { code: "EUR", symbol: "€", decimals: 2, symbolBefore: false },
    languages: ["fr", "en"],
    onlinePaymentAvailable: true,
  },
};

const DEFAULT_MARKET_CODE: MarketCode = "tn";

function isMarketCode(value: string | undefined): value is MarketCode {
  return value === "tn" || value === "fr";
}

/**
 * Le marché de CE déploiement, lu une fois au build (`NEXT_PUBLIC_MARKET` est
 * inlinée par Next.js). Absente ou inconnue → Tunisie, pour ne jamais casser
 * un déploiement existant qui n'a pas encore posé la variable.
 */
export function currentMarket(): Market {
  const code = process.env.NEXT_PUBLIC_MARKET;
  return MARKETS[isMarketCode(code) ? code : DEFAULT_MARKET_CODE];
}

/**
 * Formatage canonique d'un montant. `decimals` ne sert qu'aux affichages qui
 * ont leur propre convention indépendante de la devise (ex : un prix de
 * palier d'abonnement toujours montré en entier) — sinon la précision réelle
 * de la devise du marché s'applique.
 */
export function formatAmount(amount: number, opts?: { market?: Market; decimals?: number }): string {
  const market = opts?.market ?? currentMarket();
  const decimals = opts?.decimals ?? market.currency.decimals;
  const value = amount.toFixed(decimals);
  return market.currency.symbolBefore ? `${market.currency.symbol} ${value}` : `${value} ${market.currency.symbol}`;
}
