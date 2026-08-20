"""
Paiement en ligne du passage à un palier supérieur (paiement en ligne du
2026-08-19). Mode démonstration par défaut (aucune clé Konnect réelle pour
Tawla elle-même) : `test_demo_*` couvrent ce mode, exercé par tous les
clients aujourd'hui. `test_konnect_*` couvrent le chemin réel, dormant tant
que `PAYMENT_MODE=konnect` n'est pas posé — Konnect lui-même est simulé via
monkeypatch, jamais un vrai appel réseau.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.core import subscription_payments as subscription_payments_module
from app.core.dates import as_utc
from app.core.konnect import KonnectError, KonnectPayment
from app.core.subscription import SUBSCRIPTION_DURATION_DAYS, effective_tier
from app.core.subscription_payments import settle_subscription_payment
from app.modules.staff.models import StaffRole
from app.modules.tenants import router as tenants_router
from app.modules.tenants.models import Restaurant, SubscriptionTier
from tests.conftest import auth_headers, create_restaurant, create_staff


def _manager_headers(restaurant_id: int) -> dict[str, str]:
    return auth_headers(create_staff(restaurant_id, StaffRole.MANAGER))


# --- Mode démonstration (par défaut, aucune clé Konnect) -------------------


def test_demo_checkout_upgrades_tier_and_sets_period_end(client, db_session):
    restaurant = create_restaurant(slug="demo-checkout-upgrade", subscription_tier=SubscriptionTier.ESSENTIEL)
    headers = _manager_headers(restaurant.id)

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "pro"}, headers=headers)

    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "demo"
    assert body["restaurant"]["subscription_tier"] == "pro"
    period_end = datetime.fromisoformat(body["restaurant"]["subscription_period_end"])
    expected = datetime.now(timezone.utc) + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
    assert abs((period_end - expected).total_seconds()) < 60


def test_demo_checkout_rejects_essentiel_as_a_target(client):
    restaurant = create_restaurant(slug="demo-checkout-essentiel", subscription_tier=SubscriptionTier.ESSENTIEL)
    headers = _manager_headers(restaurant.id)

    res = client.post(
        f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "essentiel"}, headers=headers
    )

    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "INVALID_TIER"


def test_demo_checkout_rejects_a_tier_already_covered(client):
    restaurant = create_restaurant(slug="demo-checkout-not-upgrade", subscription_tier=SubscriptionTier.BUSINESS)
    headers = _manager_headers(restaurant.id)

    res = client.post(
        f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "pro"}, headers=headers
    )

    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "NOT_AN_UPGRADE"


def test_demo_checkout_extends_from_remaining_period_not_from_now(client, db_session):
    restaurant = create_restaurant(slug="demo-checkout-extend", subscription_tier=SubscriptionTier.PRO)
    restaurant.subscription_period_end = datetime.now(timezone.utc) + timedelta(days=10)
    db_session.add(restaurant)
    db_session.commit()
    headers = _manager_headers(restaurant.id)

    res = client.post(
        f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "business"}, headers=headers
    )

    assert res.status_code == 200
    period_end = datetime.fromisoformat(res.json()["restaurant"]["subscription_period_end"])
    # 10 jours restants + 30 nouveaux, pas juste 30 depuis maintenant : payer
    # en avance ne doit jamais faire perdre les jours restants.
    expected = datetime.now(timezone.utc) + timedelta(days=10 + SUBSCRIPTION_DURATION_DAYS)
    assert abs((period_end - expected).total_seconds()) < 60


def test_someone_elses_manager_cannot_checkout(client):
    restaurant = create_restaurant(slug="demo-checkout-forbidden", subscription_tier=SubscriptionTier.ESSENTIEL)
    other_restaurant = create_restaurant(slug="demo-checkout-other")
    headers = _manager_headers(other_restaurant.id)

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "pro"}, headers=headers)

    assert res.status_code == 403


# --- effective_tier : expiration d'un palier payé en ligne ------------------


def test_effective_tier_reverts_to_essentiel_once_period_end_has_passed():
    restaurant = Restaurant(
        name="x", slug="y", subscription_tier=SubscriptionTier.PRO,
        subscription_period_end=datetime.now(timezone.utc) - timedelta(days=1),
    )
    assert effective_tier(restaurant) == SubscriptionTier.ESSENTIEL


def test_effective_tier_keeps_tier_while_period_end_is_future():
    restaurant = Restaurant(
        name="x", slug="y", subscription_tier=SubscriptionTier.PRO,
        subscription_period_end=datetime.now(timezone.utc) + timedelta(days=1),
    )
    assert effective_tier(restaurant) == SubscriptionTier.PRO


def test_effective_tier_never_expires_a_manually_set_tier():
    """subscription_period_end=None (setup_restaurant.py, relation commerciale
    directe) : jamais d'expiration automatique, quelle que soit la date."""
    restaurant = Restaurant(name="x", slug="y", subscription_tier=SubscriptionTier.BUSINESS, subscription_period_end=None)
    assert effective_tier(restaurant) == SubscriptionTier.BUSINESS


def test_a_gated_feature_is_blocked_again_once_the_paid_period_expires(client, db_session):
    restaurant = create_restaurant(slug="expiry-blocks-gate", subscription_tier=SubscriptionTier.PRO)
    restaurant.subscription_period_end = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.add(restaurant)
    db_session.commit()
    headers = _manager_headers(restaurant.id)

    res = client.patch(f"/api/v1/restaurants/{restaurant.id}/ramadan-mode", json={"enabled": True}, headers=headers)

    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "UPGRADE_REQUIRED"


def test_demo_checkout_used_even_with_payment_mode_konnect_if_tawlas_own_keys_are_missing(client, monkeypatch):
    """Régression : PAYMENT_MODE=konnect est l'interrupteur UNIQUE partagé
    avec le paiement carte du client (wallet par restaurant, pas besoin des
    clés Tawla). L'activer pour lui seul ne doit jamais faire sortir le
    checkout d'abonnement du mode démo tant que Tawla n'a pas SES PROPRES
    KONNECT_API_KEY/KONNECT_RECEIVER_WALLET_ID — sinon 502 systématique
    (KonnectError: clé/wallet manquante) au lieu de rester en démo."""
    monkeypatch.setenv("PAYMENT_MODE", "konnect")
    restaurant = create_restaurant(slug="konnect-mode-on-no-tawla-keys", subscription_tier=SubscriptionTier.ESSENTIEL)
    headers = _manager_headers(restaurant.id)

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "pro"}, headers=headers)

    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "demo"
    assert body["restaurant"]["subscription_tier"] == "pro"


# --- Chemin Konnect réel (dormant, simulé via monkeypatch) ------------------


def test_konnect_checkout_stores_pending_payment_without_changing_tier_yet(client, db_session, monkeypatch):
    monkeypatch.setenv("PAYMENT_MODE", "konnect")
    monkeypatch.setenv("KONNECT_API_KEY", "tawla-test-key")
    monkeypatch.setenv("KONNECT_RECEIVER_WALLET_ID", "tawla-test-wallet")
    restaurant = create_restaurant(slug="konnect-checkout-init", subscription_tier=SubscriptionTier.ESSENTIEL)
    headers = _manager_headers(restaurant.id)

    monkeypatch.setattr(
        tenants_router, "init_konnect_payment", lambda **kwargs: ("https://pay.konnect.example/x", "ref-123")
    )

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "pro"}, headers=headers)

    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "konnect"
    assert body["pay_url"] == "https://pay.konnect.example/x"

    restaurant = db_session.get(Restaurant, restaurant.id)
    assert restaurant.subscription_tier == SubscriptionTier.ESSENTIEL  # inchangé tant que non réglé
    assert restaurant.subscription_payment_ref == "ref-123"
    assert restaurant.subscription_pending_tier == SubscriptionTier.PRO


def test_konnect_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setenv("PAYMENT_MODE", "konnect")
    restaurant = create_restaurant(slug="konnect-webhook-bad-sig")

    res = client.get(f"/api/v1/restaurants/{restaurant.id}/subscription/webhook", params={"sig": "not-the-real-one"})

    assert res.status_code == 401


def test_konnect_webhook_disabled_when_payment_mode_is_not_konnect(client):
    restaurant = create_restaurant(slug="konnect-webhook-disabled")

    res = client.get(f"/api/v1/restaurants/{restaurant.id}/subscription/webhook", params={"sig": "whatever"})

    assert res.status_code == 404


def _pending_konnect_restaurant(db_session, *, slug: str) -> Restaurant:
    restaurant = create_restaurant(slug=slug, subscription_tier=SubscriptionTier.ESSENTIEL)
    restaurant.subscription_payment_ref = "ref-abc"
    restaurant.subscription_pending_tier = SubscriptionTier.PRO
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)
    return restaurant


def test_settle_applies_tier_and_clears_payment_ref_when_completed(db_session, monkeypatch):
    restaurant = _pending_konnect_restaurant(db_session, slug="settle-completed")
    monkeypatch.setattr(
        subscription_payments_module, "get_konnect_payment",
        lambda ref: KonnectPayment(id=ref, status="completed", amount=100_000, reached_amount=100_000),
    )

    result = settle_subscription_payment(db_session, restaurant.id)

    assert result == "active"
    db_session.refresh(restaurant)
    assert restaurant.subscription_tier == SubscriptionTier.PRO
    assert restaurant.subscription_payment_ref is None
    assert restaurant.subscription_pending_tier is None
    assert as_utc(restaurant.subscription_period_end) > datetime.now(timezone.utc) + timedelta(
        days=SUBSCRIPTION_DURATION_DAYS - 1
    )


def test_settle_is_a_noop_when_payment_still_pending(db_session, monkeypatch):
    restaurant = _pending_konnect_restaurant(db_session, slug="settle-pending")
    monkeypatch.setattr(
        subscription_payments_module, "get_konnect_payment",
        lambda ref: KonnectPayment(id=ref, status="pending", amount=100_000, reached_amount=0),
    )

    result = settle_subscription_payment(db_session, restaurant.id)

    assert result == "pending"
    db_session.refresh(restaurant)
    assert restaurant.subscription_tier == SubscriptionTier.ESSENTIEL
    assert restaurant.subscription_payment_ref == "ref-abc"


def test_settle_rejects_an_amount_lower_than_the_tier_price(db_session, monkeypatch):
    restaurant = _pending_konnect_restaurant(db_session, slug="settle-amount-mismatch")
    monkeypatch.setattr(
        subscription_payments_module, "get_konnect_payment",
        lambda ref: KonnectPayment(id=ref, status="completed", amount=100_000, reached_amount=1_000),
    )

    result = settle_subscription_payment(db_session, restaurant.id)

    assert result == "error"
    db_session.refresh(restaurant)
    assert restaurant.subscription_tier == SubscriptionTier.ESSENTIEL
    assert restaurant.subscription_payment_ref == "ref-abc"  # rien consommé, un vrai règlement pourra suivre


def test_settle_is_idempotent_against_a_concurrent_replay(db_session, monkeypatch):
    restaurant = _pending_konnect_restaurant(db_session, slug="settle-idempotent")
    monkeypatch.setattr(
        subscription_payments_module, "get_konnect_payment",
        lambda ref: KonnectPayment(id=ref, status="completed", amount=100_000, reached_amount=100_000),
    )

    first = settle_subscription_payment(db_session, restaurant.id)
    second = settle_subscription_payment(db_session, restaurant.id)  # webhook rejoué / course avec /check

    assert first == "active"
    assert second == "pending"  # plus rien en attente, pas une deuxième prolongation
    db_session.refresh(restaurant)
    assert as_utc(restaurant.subscription_period_end) < datetime.now(timezone.utc) + timedelta(
        days=SUBSCRIPTION_DURATION_DAYS + 1
    )


def test_settle_returns_error_on_konnect_fetch_failure(db_session, monkeypatch):
    restaurant = _pending_konnect_restaurant(db_session, slug="settle-fetch-error")

    def _boom(ref):
        raise KonnectError("réseau indisponible")

    monkeypatch.setattr(subscription_payments_module, "get_konnect_payment", _boom)

    result = settle_subscription_payment(db_session, restaurant.id)

    assert result == "error"


def test_check_endpoint_settles_a_completed_pending_payment(client, db_session, monkeypatch):
    restaurant = _pending_konnect_restaurant(db_session, slug="check-endpoint-settles")
    headers = _manager_headers(restaurant.id)
    monkeypatch.setattr(
        subscription_payments_module, "get_konnect_payment",
        lambda ref: KonnectPayment(id=ref, status="completed", amount=100_000, reached_amount=100_000),
    )

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/check", headers=headers)

    assert res.status_code == 200
    assert res.json()["subscription_tier"] == "pro"
