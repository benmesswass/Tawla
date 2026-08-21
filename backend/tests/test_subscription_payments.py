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
from app.modules.tables.models import Table
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


def test_demo_checkout_allows_paying_essentiel_early_and_extends_the_period(client, db_session):
    """Contrairement à Pro/Business, Essentiel est TOUJOURS payable
    (2026-08-21 — le rappel de paiement de l'offre de lancement doit pouvoir
    proposer un bouton qui marche vraiment, y compris pendant le mois
    gratuit) : payer avant l'échéance prolonge depuis le reste courant,
    jamais un double paiement rejeté."""
    restaurant = create_restaurant(
        slug="demo-checkout-essentiel-early",
        subscription_tier=SubscriptionTier.ESSENTIEL,
        is_active=True,
        has_paid_for_subscription=False,
    )
    restaurant.subscription_period_end = datetime.now(timezone.utc) + timedelta(days=10)
    db_session.add(restaurant)
    db_session.commit()
    headers = _manager_headers(restaurant.id)

    res = client.post(
        f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "essentiel"}, headers=headers
    )

    assert res.status_code == 200
    body = res.json()
    assert body["restaurant"]["has_paid_for_subscription"] is True
    period_end = datetime.fromisoformat(body["restaurant"]["subscription_period_end"])
    # 10 jours restants (offre de lancement) + 30 nouveaux (vrai paiement) —
    # jamais juste 30 depuis maintenant.
    expected = datetime.now(timezone.utc) + timedelta(days=10 + SUBSCRIPTION_DURATION_DAYS)
    assert abs((period_end - expected).total_seconds()) < 60


def test_demo_checkout_activates_an_inactive_restaurant_on_essentiel(client, db_session):
    """Essentiel EST un abonnement de 30 jours comme Pro/Business
    (2026-08-20, voir CLAUDE.md) : payer l'active ET pose une échéance,
    exactement comme un passage à Pro/Business — voir aussi
    test_settle_activates_and_extends_period_for_essentiel plus bas."""
    restaurant = create_restaurant(
        slug="demo-checkout-activates",
        subscription_tier=SubscriptionTier.ESSENTIEL,
        is_active=False,
        has_paid_for_subscription=False,
    )
    headers = _manager_headers(restaurant.id)

    res = client.post(
        f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "essentiel"}, headers=headers
    )

    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "demo"
    assert body["restaurant"]["is_active"] is True
    assert body["restaurant"]["has_paid_for_subscription"] is True
    assert body["restaurant"]["subscription_tier"] == "essentiel"
    period_end = datetime.fromisoformat(body["restaurant"]["subscription_period_end"])
    expected = datetime.now(timezone.utc) + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
    assert abs((period_end - expected).total_seconds()) < 60

    restaurant = db_session.get(Restaurant, restaurant.id)
    assert restaurant.is_active is True
    assert restaurant.has_paid_for_subscription is True


def test_demo_checkout_to_pro_activates_an_inactive_restaurant_directly(client):
    """Pas besoin de payer Essentiel d'abord : un compte inactif qui paie
    directement Pro/Business est activé au passage (2026-08-20)."""
    restaurant = create_restaurant(
        slug="demo-checkout-pro-activates", subscription_tier=SubscriptionTier.ESSENTIEL, is_active=False
    )
    headers = _manager_headers(restaurant.id)

    res = client.post(
        f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "pro"}, headers=headers
    )

    assert res.status_code == 200
    body = res.json()
    assert body["restaurant"]["is_active"] is True
    assert body["restaurant"]["subscription_tier"] == "pro"


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
    """
    Avant le 2026-08-20, un palier PRO/BUSINESS expiré retombait sur Essentiel
    GRATUIT : la fonctionnalité Pro se bloquait (403 UPGRADE_REQUIRED) mais le
    compte restait utilisable. Essentiel n'étant plus jamais gratuit, il n'y a
    plus de repli — `require_active_restaurant` (402) bloque tout, avant même
    que `require_tier` n'ait la main. Le 403 UPGRADE_REQUIRED reste, lui,
    couvert pour le cas "abonnement actif mais palier insuffisant" — voir
    test_subscription_gating.py.
    """
    restaurant = create_restaurant(slug="expiry-blocks-gate", subscription_tier=SubscriptionTier.PRO)
    restaurant.subscription_period_end = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.add(restaurant)
    db_session.commit()
    headers = _manager_headers(restaurant.id)

    res = client.patch(f"/api/v1/restaurants/{restaurant.id}/ramadan-mode", json={"enabled": True}, headers=headers)

    assert res.status_code == 402
    assert res.json()["detail"]["code"] == "PAYMENT_REQUIRED"


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


# --- Offre de lancement : prix réduit répercuté sur le vrai paiement -------


def test_konnect_checkout_uses_the_discounted_essentiel_price(client, monkeypatch):
    """La réduction figée à l'inscription (2026-08-21,
    Restaurant.launch_promo_discount_percent) doit se refléter dans le
    montant réellement envoyé à Konnect, pas seulement dans l'affichage
    frontend — voir essentiel_price_tnd()."""
    monkeypatch.setenv("PAYMENT_MODE", "konnect")
    monkeypatch.setenv("KONNECT_API_KEY", "tawla-test-key")
    monkeypatch.setenv("KONNECT_RECEIVER_WALLET_ID", "tawla-test-wallet")
    restaurant = create_restaurant(
        slug="konnect-checkout-discounted", subscription_tier=SubscriptionTier.ESSENTIEL,
        is_active=False, launch_promo_discount_percent=50,
    )
    headers = _manager_headers(restaurant.id)

    captured = {}

    def _fake_init(**kwargs):
        captured.update(kwargs)
        return "https://pay.konnect.example/x", "ref-discounted"

    monkeypatch.setattr(tenants_router, "init_konnect_payment", _fake_init)

    res = client.post(
        f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "essentiel"}, headers=headers
    )

    assert res.status_code == 200
    assert captured["amount_tnd"] == 25


def test_konnect_checkout_uses_the_full_price_once_already_active(client, monkeypatch):
    """La réduction ne s'applique qu'à la toute première activation
    (essentiel_price_tnd() : `not restaurant.is_active`) — un renouvellement
    après le mois gratuit se paie plein tarif, même si la réduction reste
    encore posée en base comme historique."""
    monkeypatch.setenv("PAYMENT_MODE", "konnect")
    monkeypatch.setenv("KONNECT_API_KEY", "tawla-test-key")
    monkeypatch.setenv("KONNECT_RECEIVER_WALLET_ID", "tawla-test-wallet")
    restaurant = create_restaurant(
        slug="konnect-checkout-already-active", subscription_tier=SubscriptionTier.ESSENTIEL,
        is_active=True, launch_promo_discount_percent=100,
    )
    headers = _manager_headers(restaurant.id)

    captured = {}

    def _fake_init(**kwargs):
        captured.update(kwargs)
        return "https://pay.konnect.example/x", "ref-full-price"

    monkeypatch.setattr(tenants_router, "init_konnect_payment", _fake_init)

    res = client.post(
        f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "essentiel"}, headers=headers
    )

    assert res.status_code == 200
    assert captured["amount_tnd"] == 50


def test_settle_accepts_the_discounted_essentiel_amount(db_session, monkeypatch):
    """Le règlement recalcule le prix attendu via essentiel_price_tnd() : un
    restaurant avec une réduction de lancement figée à 50 % ne doit pas se
    faire rejeter pour n'avoir payé "que" 25 DT."""
    restaurant = create_restaurant(
        slug="settle-essentiel-discounted", subscription_tier=SubscriptionTier.ESSENTIEL,
        is_active=False, has_paid_for_subscription=False, launch_promo_discount_percent=50,
    )
    restaurant.subscription_payment_ref = "ref-discounted"
    restaurant.subscription_pending_tier = SubscriptionTier.ESSENTIEL
    db_session.add(restaurant)
    db_session.commit()
    monkeypatch.setattr(
        subscription_payments_module, "get_konnect_payment",
        lambda ref: KonnectPayment(id=ref, status="completed", amount=25_000, reached_amount=25_000),
    )

    result = settle_subscription_payment(db_session, restaurant.id)

    assert result == "active"
    restaurant = db_session.get(Restaurant, restaurant.id)
    assert restaurant.is_active is True
    assert restaurant.has_paid_for_subscription is True


def test_settle_rejects_less_than_the_discounted_essentiel_amount(db_session, monkeypatch):
    restaurant = create_restaurant(
        slug="settle-essentiel-discounted-mismatch", subscription_tier=SubscriptionTier.ESSENTIEL,
        is_active=False, has_paid_for_subscription=False, launch_promo_discount_percent=50,
    )
    restaurant.subscription_payment_ref = "ref-discounted-low"
    restaurant.subscription_pending_tier = SubscriptionTier.ESSENTIEL
    db_session.add(restaurant)
    db_session.commit()
    monkeypatch.setattr(
        subscription_payments_module, "get_konnect_payment",
        lambda ref: KonnectPayment(id=ref, status="completed", amount=25_000, reached_amount=1_000),
    )

    result = settle_subscription_payment(db_session, restaurant.id)

    assert result == "error"
    restaurant = db_session.get(Restaurant, restaurant.id)
    assert restaurant.is_active is False
    assert restaurant.subscription_payment_ref == "ref-discounted-low"  # rien consommé


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


def test_settle_activates_and_sets_period_end_for_essentiel(db_session, monkeypatch):
    """Essentiel EST un abonnement de 30 jours comme Pro/Business
    (2026-08-20, voir CLAUDE.md) : le règlement pose une échéance comme
    n'importe quel autre palier — is_active bascule EN PLUS, une bonne fois
    pour toutes (voir Restaurant.is_active/is_usable)."""
    restaurant = create_restaurant(
        slug="settle-essentiel-activates",
        subscription_tier=SubscriptionTier.ESSENTIEL,
        is_active=False,
        has_paid_for_subscription=False,
    )
    restaurant.subscription_payment_ref = "ref-essentiel"
    restaurant.subscription_pending_tier = SubscriptionTier.ESSENTIEL
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)
    monkeypatch.setattr(
        subscription_payments_module, "get_konnect_payment",
        lambda ref: KonnectPayment(id=ref, status="completed", amount=50_000, reached_amount=50_000),
    )

    result = settle_subscription_payment(db_session, restaurant.id)

    assert result == "active"
    db_session.refresh(restaurant)
    assert restaurant.is_active is True
    assert restaurant.has_paid_for_subscription is True
    assert restaurant.subscription_tier == SubscriptionTier.ESSENTIEL
    assert as_utc(restaurant.subscription_period_end) > datetime.now(timezone.utc) + timedelta(
        days=SUBSCRIPTION_DURATION_DAYS - 1
    )
    assert restaurant.subscription_payment_ref is None
    assert restaurant.subscription_pending_tier is None


def test_is_usable_reverts_to_false_once_an_essentiel_period_expires():
    """Le cœur de la correction du 2026-08-20 : contrairement à Pro/Business
    qui retombent sur Essentiel gratuit à l'expiration, Essentiel est le
    palier plancher — sans lui, le compte redevient bloqué, pas gratuit."""
    restaurant = Restaurant(
        name="x", slug="y", subscription_tier=SubscriptionTier.ESSENTIEL, is_active=True,
        subscription_period_end=datetime.now(timezone.utc) - timedelta(days=1),
    )
    assert restaurant.is_usable is False


def test_is_usable_true_while_essentiel_period_is_still_future():
    restaurant = Restaurant(
        name="x", slug="y", subscription_tier=SubscriptionTier.ESSENTIEL, is_active=True,
        subscription_period_end=datetime.now(timezone.utc) + timedelta(days=1),
    )
    assert restaurant.is_usable is True


def test_is_usable_false_when_never_activated_even_without_period_end():
    """Un restaurant tout juste inscrit (is_active=False, period_end=None par
    défaut) ne doit jamais être confondu avec un pilote fixé à la main
    (is_active=True, period_end=None = sans expiration) — voir is_usable."""
    restaurant = Restaurant(name="x", slug="y", is_active=False, subscription_period_end=None)
    assert restaurant.is_usable is False


def test_is_usable_promo_gratuit_overrides_an_expired_or_missing_period():
    restaurant = Restaurant(
        name="x", slug="y", is_active=False, promo_gratuit=True, subscription_period_end=None,
    )
    assert restaurant.is_usable is True


def test_a_staff_route_is_blocked_again_once_the_essentiel_period_expires(client, db_session):
    """Bout en bout : une route staff ordinaire (pas juste is_usable en
    isolation) refuse un restaurant dont l'abonnement Essentiel a expiré."""
    restaurant = create_restaurant(
        slug="essentiel-expiry-blocks-route",
        subscription_tier=SubscriptionTier.ESSENTIEL,
        is_active=True,
    )
    restaurant.subscription_period_end = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.add(restaurant)
    db_session.commit()
    headers = _manager_headers(restaurant.id)

    res = client.get(f"/api/v1/tables/by-restaurant/{restaurant.id}", headers=headers)

    assert res.status_code == 402
    assert res.json()["detail"]["code"] == "PAYMENT_REQUIRED"


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


# --- Parcours client public (QR) : même blocage, jamais distinguable -------


def _table_for(db_session, restaurant_id: int) -> Table:
    table = Table(restaurant_id=restaurant_id, label="Table 1")
    db_session.add(table)
    db_session.commit()
    db_session.refresh(table)
    return table


def test_public_qr_surface_404s_like_an_unknown_token_when_restaurant_inactive(client, db_session):
    """get_table_by_qr_token (tables/service.py) est le point d'entrée unique
    du parcours client (menu, commande, appel serveur, fiche restaurant,
    fidélité) — un seul test ici suffit à couvrir les cinq, voir la docstring
    de cette fonction. Même 404 INVALID_TABLE_CODE qu'un token inconnu : ne
    jamais dire à un client qu'un établissement existe mais n'a pas payé."""
    restaurant = create_restaurant(slug="public-qr-inactive", is_active=False)
    table = _table_for(db_session, restaurant.id)

    res = client.get(f"/api/v1/restaurants/by-token/{table.qr_token}")

    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "INVALID_TABLE_CODE"


def test_public_qr_surface_works_again_once_active(client, db_session):
    restaurant = create_restaurant(slug="public-qr-active", is_active=True)
    table = _table_for(db_session, restaurant.id)

    res = client.get(f"/api/v1/restaurants/by-token/{table.qr_token}")

    assert res.status_code == 200


def test_public_qr_surface_works_with_promo_even_if_never_paid(client, db_session):
    restaurant = create_restaurant(slug="public-qr-promo", is_active=False, promo_gratuit=True)
    table = _table_for(db_session, restaurant.id)

    res = client.get(f"/api/v1/restaurants/by-token/{table.qr_token}")

    assert res.status_code == 200
