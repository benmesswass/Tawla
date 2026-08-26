"""Port de paiement (France, MARCHE_FRANCE.md §4, Phase F3 étape 4)."""
import pytest

from app.core import konnect
from app.core.markets import FRANCE, TUNISIA
from app.core.payment_provider import (
    KonnectProvider,
    NullProvider,
    PaymentProviderError,
    get_payment_provider,
)


def test_no_credentials_resolves_to_null_provider():
    provider = get_payment_provider(None, market=TUNISIA)
    assert isinstance(provider, NullProvider)


def test_tunisia_with_credentials_resolves_to_konnect_provider():
    provider = get_payment_provider(("key", "wallet"), market=TUNISIA)
    assert isinstance(provider, KonnectProvider)


def test_france_resolves_to_null_provider_even_with_credentials():
    """`FRANCE.payment_provider == "none"` (StripeProvider n'existe pas
    encore, Phase F6) : un `NullProvider`, jamais Konnect pour ce marché,
    quels que soient les identifiants passés."""
    provider = get_payment_provider(("key", "wallet"), market=FRANCE)
    assert isinstance(provider, NullProvider)


def test_null_provider_is_never_available():
    assert NullProvider().is_available() is False


def test_null_provider_raises_a_generic_error_if_called_anyway():
    provider = NullProvider()
    with pytest.raises(PaymentProviderError):
        provider.init_payment(
            amount=10, order_id="1", description="x", success_url="https://x", fail_url="https://x",
            lifespan_minutes=30,
        )
    with pytest.raises(PaymentProviderError):
        provider.get_payment("ref")
    with pytest.raises(PaymentProviderError):
        provider.to_smallest_unit(10)


def test_null_provider_does_not_support_refund():
    assert NullProvider().supports_refund() is False


def test_konnect_provider_does_not_support_refund():
    """§AHC8 : l'API Konnect n'expose aucun endpoint de remboursement
    programmatique — un vrai remboursement reste manuel, jamais un faux
    appel API."""
    assert KonnectProvider("key", "wallet").supports_refund() is False


def test_konnect_provider_converts_to_millimes_like_the_underlying_client():
    provider = KonnectProvider("key", "wallet")
    assert provider.to_smallest_unit(12.5) == konnect.tnd_to_millimes(12.5)


def test_konnect_provider_wraps_init_errors_as_payment_provider_error(monkeypatch):
    def _boom(**kwargs):
        raise konnect.KonnectError("réseau indisponible")

    monkeypatch.setattr(konnect, "init_konnect_payment", _boom)
    provider = KonnectProvider("key", "wallet")

    with pytest.raises(PaymentProviderError):
        provider.init_payment(
            amount=10, order_id="1", description="x", success_url="https://x", fail_url="https://x",
            lifespan_minutes=30,
        )


def test_konnect_provider_wraps_get_payment_errors_as_payment_provider_error(monkeypatch):
    def _boom(ref, api_key=None):
        raise konnect.KonnectError("réseau indisponible")

    monkeypatch.setattr(konnect, "get_konnect_payment", _boom)
    provider = KonnectProvider("key", "wallet")

    with pytest.raises(PaymentProviderError):
        provider.get_payment("ref")
