/**
 * Formateur monétaire unique — France, MARCHE_FRANCE.md phase F3 étape 2.
 * Miroir de app/core/currency.py côté backend.
 *
 * Règle durable (voir CLAUDE.md) : plus jamais de décimales ni de séparateur
 * décimal en dur dans un composant — toujours `formatAmount`/`formatMoney`,
 * pilotés par `currentMarket`.
 *
 * Deux fonctions, pas une seule : le symbole affiché dépend de la LANGUE
 * d'affichage, pas seulement du marché — `lib/i18n/ar.ts` montre le dinar en
 * écriture arabe (« د.ت »), jamais « DT ». `formatAmount` ne rend donc que le
 * nombre (décimales + séparateur du marché) ; `formatMoney` y ajoute le
 * symbole par défaut du marché (correct en français, jamais à utiliser tel
 * quel dans un dictionnaire arabe).
 */
import { currentMarket, type MarketConfig } from "./market";

// Espace insécable en échappement explicite ( ) plutôt que tapée : un
// caractère invisible dans le code source est trop facile à "corriger" par
// erreur en simple espace au prochain passage d'un éditeur.
const NBSP = "\u00A0";

/** Le nombre seul, formaté selon le marché : « 22.000 » ou « 1234,50 ». */
export function formatAmount(amount: number, market: MarketConfig = currentMarket): string {
  const { decimals, decimalSeparator } = market.currency;
  const formatted = amount.toFixed(decimals);
  return decimalSeparator === "." ? formatted : formatted.replace(".", decimalSeparator);
}

/** Nombre + symbole par défaut du marché : « 22.000 DT », « 12,50 € ». */
export function formatMoney(amount: number, market: MarketConfig = currentMarket): string {
  return `${formatAmount(amount, market)}${NBSP}${market.currency.symbol}`;
}
