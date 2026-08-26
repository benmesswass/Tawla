"""
Couche marché (France, MARCHE_FRANCE.md phase F3) — l'objet Market lui-même,
purement additif à ce stade : aucun module existant ne le lit encore, donc
rien ici ne protège contre une régression du produit tunisien (c'est le rôle
du reste de la suite, qui doit continuer à passer sans modification — voir le
critère de sortie de F3). Ces tests couvrent seulement la couche elle-même.
"""
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


def test_tunisia_market_shape_unchanged():
    """Garde-fou explicite sur les valeurs déjà en dur ailleurs dans le code
    (TIER_PRICES_TND, TUNIS timezone) : la couche marché doit les reproduire
    à l'identique, jamais improviser une nouvelle valeur."""
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
