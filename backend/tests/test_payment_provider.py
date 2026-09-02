"""Port de paiement (France, MARCHE_FRANCE.md §4, Phase F3 étape 4 / Phase F6 étape 2)."""
import pytest

from app.core import konnect, stripe_gateway
from app.core.markets import FRANCE, TUNISIA
from app.core.payment_provider import (
    KonnectProvider,
    NullProvider,
    PaymentProviderError,
    StripeProvider,
    get_payment_provider,
)


def test_no_credentials_resolves_to_null_provider():
    provider = get_payment_provider(None, market=TUNISIA)
    assert isinstance(provider, NullProvider)


def test_tunisia_with_credentials_resolves_to_konnect_provider():
    provider = get_payment_provider(("key", "wallet"), market=TUNISIA)
    assert isinstance(provider, KonnectProvider)


def test_france_resolves_to_null_provider_with_konnect_shaped_credentials():
    """`FRANCE.payment_provider == "stripe"` : des identifiants Konnect
    (tuple) n'ont pas la forme attendue (`str` seul) pour ce marché, donc
    `NullProvider` — jamais un mélange entre fournisseurs."""
    provider = get_payment_provider(("key", "wallet"), market=FRANCE)
    assert isinstance(provider, NullProvider)


def test_france_with_account_id_resolves_to_stripe_provider():
    provider = get_payment_provider("acct_123", market=FRANCE)
    assert isinstance(provider, StripeProvider)


def test_tunisia_resolves_to_null_provider_with_stripe_shaped_credentials():
    """Symétrique : un `account_id` Stripe passé au marché tunisien ne
    ressemble pas à des identifiants Konnect, donc `NullProvider`."""
    provider = get_payment_provider("acct_123", market=TUNISIA)
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


def test_stripe_provider_is_available_only_when_payment_mode_is_stripe(monkeypatch):
    """Même anti-activation accidentelle que Konnect : la présence d'un
    `account_id` ne suffit pas, il faut `PAYMENT_MODE=stripe` explicite —
    c'est le drapeau démo/prod de l'Annexe C2."""
    monkeypatch.delenv("PAYMENT_MODE", raising=False)
    assert StripeProvider("acct_123").is_available() is False

    monkeypatch.setenv("PAYMENT_MODE", "stripe")
    assert StripeProvider("acct_123").is_available() is True


def test_stripe_provider_supports_refund():
    """Contrairement à Konnect (§AHC8), l'API Stripe expose un vrai
    remboursement programmatique."""
    assert StripeProvider("acct_123").supports_refund() is True


def test_stripe_provider_converts_to_cents_like_the_underlying_gateway():
    provider = StripeProvider("acct_123")
    assert provider.to_smallest_unit(12.5) == stripe_gateway.eur_to_cents(12.5)


def test_stripe_provider_wraps_init_errors_as_payment_provider_error(monkeypatch):
    def _boom(**kwargs):
        raise stripe_gateway.StripeGatewayError("réseau indisponible")

    monkeypatch.setattr(stripe_gateway, "create_checkout_session", _boom)
    provider = StripeProvider("acct_123")

    with pytest.raises(PaymentProviderError):
        provider.init_payment(
            amount=10, order_id="1", description="x", success_url="https://x", fail_url="https://x",
            lifespan_minutes=30,
        )


def test_stripe_provider_wraps_get_payment_errors_as_payment_provider_error(monkeypatch):
    def _boom(ref, account_id=None):
        raise stripe_gateway.StripeGatewayError("réseau indisponible")

    monkeypatch.setattr(stripe_gateway, "retrieve_checkout_session", _boom)
    provider = StripeProvider("acct_123")

    with pytest.raises(PaymentProviderError):
        provider.get_payment("ref")
