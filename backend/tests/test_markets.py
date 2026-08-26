"""
Couche marché (France, MARCHE_FRANCE.md phase F3) — l'objet Market lui-même.
`core/dates.py` (étape 3) et `core/currency.py`/`core/invoice.py` (étape 2)
le lisent désormais ; rien d'autre encore. Le reste de la suite doit
continuer à passer sans modification quand `MARKET` n'est pas posé (défaut
"tn") — c'est le critère de sortie de F3. Ces tests couvrent la couche
elle-même.
"""
from datetime import datetime

import pytest

from app.core.markets import FRANCE, TUNISIA, get_market
from app.modules.tenants.models import SubscriptionTier


def test_tunisia_is_the_default_market():
    assert get_market() is TUNISIA
    assert get_market("tn") is TUNISIA


def test_france_market_shape():
    market = get_market("fr")
    assert market is FRANCE
    assert market.currency.code == "EUR"
    assert market.currency.decimals == 2
    assert market.currency.decimal_separator == ","
    assert str(market.timezone) == "Europe/Paris"
    assert market.payment_provider == "none"
    assert market.invoice_threshold == 25.0
    assert market.vat_rates is not None
    assert market.tier_prices == {
        SubscriptionTier.ESSENTIEL: 49,
        SubscriptionTier.PRO: 89,
        SubscriptionTier.BUSINESS: 149,
    }


def test_tunisia_market_shape_unchanged():
    """Garde-fou explicite sur les valeurs qui étaient en dur ailleurs dans
    le code avant la Phase F3 (`TIER_PRICES_TND`, `TUNIS` — désormais
    supprimés, migrés vers cet objet) : la couche marché devait les
    reproduire à l'identique lors de la migration, jamais improviser une
    nouvelle valeur — ce test le garantit dans la durée."""
    assert TUNISIA.currency.code == "TND"
    assert TUNISIA.currency.decimals == 3
    assert TUNISIA.currency.decimal_separator == "."
    assert str(TUNISIA.timezone) == "Africa/Tunis"
    assert TUNISIA.tier_prices == {
        SubscriptionTier.ESSENTIEL: 50,
        SubscriptionTier.PRO: 100,
        SubscriptionTier.BUSINESS: 150,
    }
    assert TUNISIA.vat_rates is None
    assert TUNISIA.invoice_threshold is None


def test_market_is_case_insensitive():
    assert get_market("FR") is FRANCE
    assert get_market("Tn") is TUNISIA


def test_unknown_market_code_raises():
    with pytest.raises(ValueError, match="unknown market code"):
        get_market("xx")


def test_france_timezone_observes_daylight_saving_time():
    """La raison d'être du choix `zoneinfo` plutôt qu'un décalage fixe
    (MARCHE_FRANCE.md Phase F3, `core/dates.py:9`) : Paris est UTC+2 l'été,
    UTC+1 l'hiver."""
    ete = datetime(2026, 7, 15, 12, tzinfo=FRANCE.timezone)
    hiver = datetime(2026, 1, 15, 12, tzinfo=FRANCE.timezone)

    assert ete.utcoffset().total_seconds() / 3600 == 2
    assert hiver.utcoffset().total_seconds() / 3600 == 1


def test_tunisia_timezone_has_no_daylight_saving_time():
    """Tunis n'observe plus l'heure d'été depuis 2009 : UTC+1 toute
    l'année, contrairement à Paris — voir le test France ci-dessus."""
    ete = datetime(2026, 7, 15, 12, tzinfo=TUNISIA.timezone)
    hiver = datetime(2026, 1, 15, 12, tzinfo=TUNISIA.timezone)

    assert ete.utcoffset().total_seconds() / 3600 == 1
    assert hiver.utcoffset().total_seconds() / 3600 == 1
