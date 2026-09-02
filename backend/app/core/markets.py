"""
Couche marché — France, MARCHE_FRANCE.md phase F3.

Un objet `Market` unique par pays, chargé une fois au démarrage depuis
`MARKET` (voir core/config.py). Règle durable à partir d'ici : plus jamais de
devise, de fuseau, de taux ou de prix de palier en dur dans un module — tout
passe par `current_market`. C'est la seule protection contre la divergence
entre les deux marchés.

Câblage progressif au fil des étapes de la Phase F3 (voir son tableau dans
MARCHE_FRANCE.md) : formateur monétaire (`core/currency.py`) et fuseau des
journées de service (`core/dates.py::service_day_start`) branchés ; port de
paiement encore à extraire de `orders/service.py`.
"""
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.modules.tenants.models import SubscriptionTier


@dataclass(frozen=True)
class CurrencyConfig:
    code: str  # code ISO 4217 ("TND", "EUR")
    symbol: str
    decimals: int  # 3 en Tunisie, 2 en France
    decimal_separator: str  # "." en Tunisie, "," en France (MARCHE_FRANCE.md §3.2)


@dataclass(frozen=True)
class Market:
    code: str  # "tn" | "fr"
    name: str
    currency: CurrencyConfig
    timezone: ZoneInfo
    languages: tuple[str, ...]
    # Adaptateur de paiement technique branché pour ce marché. Distinct de la
    # question de savoir si l'encaissement réel est exposé en production :
    # ça, c'est le drapeau `PAYMENT_MODE` posé par déploiement (décision de
    # Wassim du 2026-08-26, Annexe C/C2 de MARCHE_FRANCE.md, « grisé en prod,
    # actif en démo » — voir `stripe_gateway.is_stripe_enabled()`), jamais ce
    # champ-ci.
    payment_provider: str
    # Prix des paliers dans la devise du marché. Les valeurs françaises sont
    # l'hypothèse de départ de MARCHE_FRANCE.md §3.4 (49/89/149 €) — **jamais
    # à annoncer publiquement avant validation en Phase F1**, cf. la garde
    # dans le même document.
    tier_prices: dict[SubscriptionTier, int]
    # Taux de TVA par catégorie, ventilation à construire en Phase F5/A4 (S2).
    # None tant que le marché ne gère aucune TVA (Tunisie).
    vat_rates: dict[str, float] | None
    # Seuil de note obligatoire (25 € TTC en France, arrêté du 3 octobre 1983).
    invoice_threshold: float | None


TUNISIA = Market(
    code="tn",
    name="Tunisie",
    currency=CurrencyConfig(code="TND", symbol="DT", decimals=3, decimal_separator="."),
    timezone=ZoneInfo("Africa/Tunis"),
    languages=("fr", "ar"),
    payment_provider="konnect",
    tier_prices={
        SubscriptionTier.ESSENTIEL: 49,
        SubscriptionTier.PRO: 89,
        SubscriptionTier.BUSINESS: 149,
    },
    vat_rates=None,
    invoice_threshold=None,
)

FRANCE = Market(
    code="fr",
    name="France",
    currency=CurrencyConfig(code="EUR", symbol="€", decimals=2, decimal_separator=","),
    timezone=ZoneInfo("Europe/Paris"),
    languages=("fr", "en"),
    payment_provider="stripe",
    tier_prices={
        SubscriptionTier.ESSENTIEL: 49,
        SubscriptionTier.PRO: 89,
        SubscriptionTier.BUSINESS: 149,
    },
    vat_rates={"sur_place": 0.10, "a_emporter": 0.055, "alcool": 0.20},
    invoice_threshold=25.0,
)

_MARKETS: dict[str, Market] = {"tn": TUNISIA, "fr": FRANCE}


def get_market(code: str | None = None) -> Market:
    """Résout un marché par code — `code=None` lit `settings.market`
    (variable d'environnement `MARKET`, défaut "tn")."""
    resolved = (code or settings.market).lower()
    market = _MARKETS.get(resolved)
    if market is None:
        raise ValueError(f"unknown market code: {resolved!r} (expected one of {sorted(_MARKETS)})")
    return market


# Chargé une fois au démarrage du processus — un déploiement sert un seul
# marché (MARCHE_FRANCE.md §4, option B), jamais les deux à la fois.
current_market = get_market()
