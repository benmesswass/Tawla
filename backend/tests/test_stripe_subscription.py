"""
Abonnement récurrent Tawla (France, mode Netflix — retour utilisateur
2026-09-02). Aucun de ces chemins n'était couvert avant : tout avait été
vérifié à la main contre l'API Stripe réelle (voir MARCHE_FRANCE.md Phase F6
étape 4), ce qui a bien trouvé plusieurs bugs réels (double facturation,
`current_period_end` déplacé, produit réutilisé marqué inactif, schedule déjà
attachée) — chacun a maintenant sa régression ici, jamais un vrai appel
réseau Stripe (tout `stripe.*` est monkeypatché).

Trois couches, comme le module qu'elles couvrent :
- `stripe_gateway` : les appels SDK eux-mêmes (mock du module `stripe`).
- `handle_stripe_subscription_event` : la logique métier du webhook (event
  factice, jamais de signature réelle à vérifier ici).
- Les endpoints du routeur : `current_market` basculé sur FRANCE (seul
  marché Stripe), `stripe_gateway` mocké au niveau fonction — même
  convention que test_subscription_payments.py pour Konnect.
"""
from datetime import datetime, timezone

import pytest
import stripe as stripe_sdk

from app.core import markets as markets_module
from app.core import stripe_gateway
from app.core import subscription_payments as subscription_payments_module
from app.core.dates import as_utc
from app.core.markets import FRANCE, TUNISIA
from app.core.subscription_payments import handle_stripe_subscription_event
from app.modules.staff.models import StaffRole
from app.modules.tenants import router as tenants_router
from app.modules.tenants.models import Restaurant, SubscriptionTier
from tests.conftest import auth_headers, create_restaurant, create_staff


def _manager_headers(restaurant_id: int) -> dict[str, str]:
    return auth_headers(create_staff(restaurant_id, StaffRole.MANAGER))


def _subscribed_restaurant(db_session, *, slug: str, tier: SubscriptionTier = SubscriptionTier.PRO, **extra) -> Restaurant:
    restaurant = create_restaurant(slug=slug, subscription_tier=tier)
    restaurant.stripe_customer_id = "cus_test"
    restaurant.stripe_subscription_id = "sub_test"
    for key, value in extra.items():
        setattr(restaurant, key, value)
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)
    return restaurant


# --- stripe_gateway : appels SDK (stripe.* monkeypatché) --------------------


class _FakeStripeObject(dict):
    """Un `StripeObject` réel supporte À LA FOIS l'accès par attribut
    (`product.id`, utilisé par `stripe.Product.create(...).id` dans
    stripe_gateway.py) et `.to_dict()` (jamais `.get()` sur l'objet brut) —
    reproduit ici pour que le code sous test ne voie pas la différence."""

    def to_dict(self):
        return dict(self)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as err:
            raise AttributeError(name) from err


def test_retrieve_subscription_reads_period_end_from_the_item_not_the_root(monkeypatch):
    """Régression du 2026-09-02 : `current_period_end` a migré de la racine
    de l'abonnement vers `items.data[0]` dans les versions API Stripe
    récentes — lire la racine lève un KeyError silencieux ou périmé."""
    fake_sub = _FakeStripeObject(
        {
            "metadata": {"tier": "pro"},
            "items": {"data": [{"current_period_end": 1_800_000_000}]},
        }
    )
    monkeypatch.setattr(stripe_sdk.Subscription, "retrieve", lambda *a, **kw: fake_sub)

    result = stripe_gateway.retrieve_subscription("sub_test")

    assert result.tier == "pro"
    assert result.current_period_end == datetime.fromtimestamp(1_800_000_000, tz=timezone.utc)


def test_retrieve_subscription_raises_when_metadata_tier_is_missing(monkeypatch):
    fake_sub = _FakeStripeObject({"metadata": {}, "items": {"data": [{"current_period_end": 1_800_000_000}]}})
    monkeypatch.setattr(stripe_sdk.Subscription, "retrieve", lambda *a, **kw: fake_sub)

    with pytest.raises(stripe_gateway.StripeGatewayError):
        stripe_gateway.retrieve_subscription("sub_test")


def test_change_tier_immediately_creates_a_fresh_product_never_reuses_the_old_one(monkeypatch):
    """Régression du 2026-09-02 : réutiliser le produit de l'ancien prix
    échoue dès que l'abonnement qui l'utilisait a été annulé une fois
    ("product ... is marked as inactive") — un produit frais à chaque
    changement, jamais `current_item["price"]["product"]`."""
    fake_sub = _FakeStripeObject(
        {"items": {"data": [{"id": "si_1", "price": {"product": "prod_old_inactive"}}]}}
    )
    monkeypatch.setattr(stripe_sdk.Subscription, "retrieve", lambda *a, **kw: fake_sub)
    monkeypatch.setattr(stripe_sdk.Product, "create", lambda **kw: _FakeStripeObject({"id": "prod_fresh"}))

    captured = {}

    def _fake_modify(subscription_id, **kwargs):
        captured["subscription_id"] = subscription_id
        captured.update(kwargs)

    monkeypatch.setattr(stripe_sdk.Subscription, "modify", _fake_modify)

    stripe_gateway.change_tier_immediately(
        subscription_id="sub_test", new_tier="business", new_amount_eur=149, description="Tawla — abonnement business"
    )

    assert captured["subscription_id"] == "sub_test"
    assert captured["items"][0]["id"] == "si_1"
    assert captured["items"][0]["price_data"]["product"] == "prod_fresh"
    assert captured["proration_behavior"] == "always_invoice"
    assert captured["metadata"] == {"tier": "business"}


def test_schedule_tier_change_creates_a_new_schedule_when_none_exists(monkeypatch):
    fake_sub = _FakeStripeObject(
        {
            "items": {"data": [{"current_period_end": 1_800_000_000, "price": {"id": "price_current"}}]},
            "schedule": None,
        }
    )
    fake_schedule = _FakeStripeObject({"id": "sub_sched_new", "phases": [{"start_date": 1_700_000_000}]})
    monkeypatch.setattr(stripe_sdk.Subscription, "retrieve", lambda *a, **kw: fake_sub)
    monkeypatch.setattr(stripe_sdk.SubscriptionSchedule, "create", lambda **kw: fake_schedule)
    monkeypatch.setattr(stripe_sdk.Product, "create", lambda **kw: _FakeStripeObject({"id": "prod_fresh"}))
    captured = {}
    monkeypatch.setattr(stripe_sdk.SubscriptionSchedule, "modify", lambda sid, **kw: captured.update(id=sid, **kw))

    stripe_gateway.schedule_tier_change(
        subscription_id="sub_test", new_tier="essentiel", new_amount_eur=49, description="Tawla — abonnement essentiel"
    )

    assert captured["id"] == "sub_sched_new"
    assert captured["phases"][1]["metadata"] == {"tier": "essentiel"}
    assert captured["phases"][1]["start_date"] == 1_800_000_000


def test_schedule_tier_change_modifies_the_existing_schedule_instead_of_creating_a_second_one(monkeypatch):
    """Régression du 2026-09-02 : un abonnement ne peut être attaché qu'à UNE
    SEULE Subscription Schedule — recréer par `from_subscription` alors
    qu'une existe déjà lève "cannot migrate a subscription that is already
    attached to a schedule" (un manager qui change deux fois d'avis)."""
    fake_sub = _FakeStripeObject(
        {
            "items": {"data": [{"current_period_end": 1_800_000_000, "price": {"id": "price_current"}}]},
            "schedule": "sub_sched_existing",
        }
    )
    fake_schedule = _FakeStripeObject({"id": "sub_sched_existing", "phases": [{"start_date": 1_700_000_000}]})
    monkeypatch.setattr(stripe_sdk.Subscription, "retrieve", lambda *a, **kw: fake_sub)
    monkeypatch.setattr(stripe_sdk.SubscriptionSchedule, "retrieve", lambda sid, **kw: fake_schedule)
    monkeypatch.setattr(stripe_sdk.Product, "create", lambda **kw: _FakeStripeObject({"id": "prod_fresh"}))

    def _boom_create(**kw):
        raise AssertionError("ne doit jamais recréer une schedule quand une existe déjà")

    monkeypatch.setattr(stripe_sdk.SubscriptionSchedule, "create", _boom_create)
    captured = {}
    monkeypatch.setattr(stripe_sdk.SubscriptionSchedule, "modify", lambda sid, **kw: captured.update(id=sid, **kw))

    stripe_gateway.schedule_tier_change(
        subscription_id="sub_test", new_tier="essentiel", new_amount_eur=49, description="Tawla — abonnement essentiel"
    )

    assert captured["id"] == "sub_sched_existing"


def test_release_schedule_if_any_releases_when_a_schedule_is_attached(monkeypatch):
    fake_sub = _FakeStripeObject({"schedule": "sub_sched_existing"})
    monkeypatch.setattr(stripe_sdk.Subscription, "retrieve", lambda *a, **kw: fake_sub)
    released = {}
    monkeypatch.setattr(stripe_sdk.SubscriptionSchedule, "release", lambda sid, **kw: released.update(id=sid))

    stripe_gateway.release_schedule_if_any(subscription_id="sub_test")

    assert released["id"] == "sub_sched_existing"


def test_release_schedule_if_any_is_a_noop_without_a_schedule(monkeypatch):
    fake_sub = _FakeStripeObject({"schedule": None})
    monkeypatch.setattr(stripe_sdk.Subscription, "retrieve", lambda *a, **kw: fake_sub)

    def _boom_release(sid, **kw):
        raise AssertionError("rien à relâcher, ne doit jamais appeler l'API")

    monkeypatch.setattr(stripe_sdk.SubscriptionSchedule, "release", _boom_release)

    stripe_gateway.release_schedule_if_any(subscription_id="sub_test")  # ne lève rien


# --- handle_stripe_subscription_event : logique métier du webhook ----------


def _event(event_type: str, obj: dict) -> dict:
    return {"type": event_type, "data": {"object": _FakeStripeObject(obj)}}


def test_checkout_completed_links_customer_and_subscription(db_session):
    restaurant = create_restaurant(slug="stripe-webhook-link", subscription_tier=SubscriptionTier.ESSENTIEL)
    event = _event(
        "checkout.session.completed",
        {"mode": "subscription", "client_reference_id": str(restaurant.id), "customer": "cus_1", "subscription": "sub_1"},
    )

    result = handle_stripe_subscription_event(db_session, event)

    assert result == "linked"
    restaurant = db_session.get(Restaurant, restaurant.id)
    assert restaurant.stripe_customer_id == "cus_1"
    assert restaurant.stripe_subscription_id == "sub_1"


def test_checkout_completed_ignores_non_subscription_mode(db_session):
    restaurant = create_restaurant(slug="stripe-webhook-ignore-mode")
    event = _event(
        "checkout.session.completed",
        {"mode": "payment", "client_reference_id": str(restaurant.id), "customer": "cus_1", "subscription": "sub_1"},
    )

    assert handle_stripe_subscription_event(db_session, event) == "ignored"


def test_invoice_paid_applies_tier_and_clears_pending_downgrade(db_session, monkeypatch):
    """`invoice.paid` doit effacer `subscription_downgrade_pending_tier` :
    une rétrogradation programmée (ou la phase suivante d'un renouvellement
    normal) vient de s'appliquer, plus rien "en attente" à partir de cette
    échéance."""
    restaurant = _subscribed_restaurant(
        db_session, slug="stripe-webhook-renew", tier=SubscriptionTier.BUSINESS,
        subscription_downgrade_pending_tier=SubscriptionTier.ESSENTIEL,
    )
    monkeypatch.setattr(
        subscription_payments_module, "retrieve_subscription",
        lambda sid: stripe_gateway.StripeSubscriptionStatus(
            tier="essentiel", current_period_end=datetime(2026, 10, 2, tzinfo=timezone.utc)
        ),
    )
    event = _event("invoice.paid", {"subscription": "sub_test"})

    result = handle_stripe_subscription_event(db_session, event)

    assert result == "renewed"
    db_session.refresh(restaurant)
    assert restaurant.subscription_tier == SubscriptionTier.ESSENTIEL
    assert as_utc(restaurant.subscription_period_end) == datetime(2026, 10, 2, tzinfo=timezone.utc)
    assert restaurant.is_active is True
    assert restaurant.has_paid_for_subscription is True
    assert restaurant.subscription_downgrade_pending_tier is None


def test_invoice_paid_is_not_found_when_no_restaurant_matches_the_subscription(db_session):
    event = _event("invoice.paid", {"subscription": "sub_unknown"})

    assert handle_stripe_subscription_event(db_session, event) == "not_found"


def test_subscription_updated_records_cancellation_scheduled(db_session):
    restaurant = _subscribed_restaurant(db_session, slug="stripe-webhook-cancel-scheduled")
    event = _event("customer.subscription.updated", {"id": "sub_test", "cancel_at_period_end": True})

    result = handle_stripe_subscription_event(db_session, event)

    assert result == "cancellation_scheduled"
    db_session.refresh(restaurant)
    assert restaurant.subscription_cancel_at_period_end is True


def test_subscription_updated_records_cancellation_reversed(db_session):
    restaurant = _subscribed_restaurant(
        db_session, slug="stripe-webhook-cancel-reversed", subscription_cancel_at_period_end=True
    )
    event = _event("customer.subscription.updated", {"id": "sub_test", "cancel_at_period_end": False})

    result = handle_stripe_subscription_event(db_session, event)

    assert result == "cancellation_reversed"
    db_session.refresh(restaurant)
    assert restaurant.subscription_cancel_at_period_end is False


def test_subscription_updated_is_a_noop_replay_of_the_same_value(db_session):
    _subscribed_restaurant(db_session, slug="stripe-webhook-cancel-replay", subscription_cancel_at_period_end=True)
    event = _event("customer.subscription.updated", {"id": "sub_test", "cancel_at_period_end": True})

    assert handle_stripe_subscription_event(db_session, event) == "ignored"


def test_subscription_deleted_deactivates_without_falling_back_to_essentiel(db_session):
    """Cœur du retour utilisateur du 2026-09-02 : annuler N'IMPORTE QUEL
    palier (y compris Essentiel) veut dire plus aucun service — jamais un
    retour gratuit à Essentiel comme le ferait `effective_tier()` sur une
    simple expiration Konnect."""
    restaurant = _subscribed_restaurant(db_session, slug="stripe-webhook-deleted", tier=SubscriptionTier.BUSINESS)
    event = _event("customer.subscription.deleted", {"id": "sub_test"})

    result = handle_stripe_subscription_event(db_session, event)

    assert result == "cancelled"
    db_session.refresh(restaurant)
    assert restaurant.is_active is False
    assert restaurant.stripe_subscription_id is None
    assert restaurant.subscription_cancel_at_period_end is False
    # Palier volontairement inchangé : ActivationRequired propose de repayer
    # CE palier, pas un repli sur Essentiel.
    assert restaurant.subscription_tier == SubscriptionTier.BUSINESS


def test_unknown_event_type_is_ignored(db_session):
    event = _event("customer.created", {"id": "cus_whatever"})

    assert handle_stripe_subscription_event(db_session, event) == "ignored"


# --- Endpoints du routeur : current_market basculé sur FRANCE --------------


@pytest.fixture(autouse=True)
def _france_market(monkeypatch):
    monkeypatch.setattr(tenants_router, "current_market", FRANCE)
    monkeypatch.setenv("PAYMENT_MODE", "stripe")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")


def test_first_subscription_creates_a_checkout_session_not_yet_applying_the_tier(client, db_session, monkeypatch):
    restaurant = create_restaurant(slug="stripe-checkout-first", subscription_tier=SubscriptionTier.ESSENTIEL)
    headers = _manager_headers(restaurant.id)
    monkeypatch.setattr(
        tenants_router.stripe_gateway, "create_subscription_checkout_session",
        lambda **kw: ("https://checkout.stripe.example/x", "cs_123"),
    )

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "pro"}, headers=headers)

    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "stripe"
    assert body["pay_url"] == "https://checkout.stripe.example/x"
    restaurant = db_session.get(Restaurant, restaurant.id)
    assert restaurant.subscription_tier == SubscriptionTier.ESSENTIEL  # inchangé tant que non réglé


def test_upgrade_while_already_subscribed_changes_the_existing_subscription_in_place(client, db_session, monkeypatch):
    """Régression du 2026-09-02 (bug de double/triple facturation) : un
    manager déjà abonné qui clique sur un palier supérieur ne doit JAMAIS
    créer une seconde session de paiement — seulement modifier l'abonnement
    existant."""
    restaurant = _subscribed_restaurant(db_session, slug="stripe-upgrade-inplace", tier=SubscriptionTier.ESSENTIEL)
    headers = _manager_headers(restaurant.id)

    def _boom_new_session(**kw):
        raise AssertionError("ne doit jamais créer une seconde session de paiement")

    monkeypatch.setattr(tenants_router.stripe_gateway, "create_subscription_checkout_session", _boom_new_session)
    captured = {}
    monkeypatch.setattr(
        tenants_router.stripe_gateway, "change_tier_immediately", lambda **kw: captured.update(kw)
    )

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "business"}, headers=headers)

    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "stripe"
    assert body["restaurant"]["subscription_tier"] == "business"
    assert captured["subscription_id"] == "sub_test"
    assert captured["new_tier"] == "business"
    db_session.refresh(restaurant)
    assert restaurant.subscription_tier == SubscriptionTier.BUSINESS
    assert restaurant.is_active is True
    assert restaurant.has_paid_for_subscription is True


def test_upgrade_releases_a_pending_downgrade_schedule_first(client, db_session, monkeypatch):
    """Régression du 2026-09-02 : Pro avec un retour à Essentiel déjà
    programmé, puis upgrade vers Business — la programmation doit être
    ANNULÉE, jamais laissée à écraser l'upgrade à l'échéance."""
    restaurant = _subscribed_restaurant(
        db_session, slug="stripe-upgrade-releases-pending", tier=SubscriptionTier.PRO,
        subscription_downgrade_pending_tier=SubscriptionTier.ESSENTIEL,
    )
    headers = _manager_headers(restaurant.id)
    released = {}
    monkeypatch.setattr(
        tenants_router.stripe_gateway, "release_schedule_if_any", lambda **kw: released.update(kw)
    )
    monkeypatch.setattr(tenants_router.stripe_gateway, "change_tier_immediately", lambda **kw: None)

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "business"}, headers=headers)

    assert res.status_code == 200
    assert released["subscription_id"] == "sub_test"
    db_session.refresh(restaurant)
    assert restaurant.subscription_downgrade_pending_tier is None


def test_checkout_rejects_a_same_or_lower_tier_once_already_subscribed(client, db_session):
    restaurant = _subscribed_restaurant(db_session, slug="stripe-checkout-not-upgrade", tier=SubscriptionTier.BUSINESS)
    headers = _manager_headers(restaurant.id)

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/checkout", json={"tier": "pro"}, headers=headers)

    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "NOT_AN_UPGRADE"


def test_downgrade_schedules_the_tier_change_and_marks_it_pending(client, db_session, monkeypatch):
    restaurant = _subscribed_restaurant(db_session, slug="stripe-downgrade-schedules", tier=SubscriptionTier.BUSINESS)
    headers = _manager_headers(restaurant.id)
    captured = {}
    monkeypatch.setattr(tenants_router.stripe_gateway, "schedule_tier_change", lambda **kw: captured.update(kw))

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/downgrade", json={"tier": "essentiel"}, headers=headers)

    assert res.status_code == 200
    assert res.json()["subscription_downgrade_pending_tier"] == "essentiel"
    assert captured["subscription_id"] == "sub_test"
    assert captured["new_tier"] == "essentiel"
    db_session.refresh(restaurant)
    assert restaurant.subscription_downgrade_pending_tier == SubscriptionTier.ESSENTIEL
    # Le palier AFFICHÉ ne change qu'à invoice.paid, jamais ici.
    assert restaurant.subscription_tier == SubscriptionTier.BUSINESS


def test_downgrade_rejects_a_target_tier_that_is_not_strictly_lower(client, db_session):
    restaurant = _subscribed_restaurant(db_session, slug="stripe-downgrade-not-lower", tier=SubscriptionTier.PRO)
    headers = _manager_headers(restaurant.id)

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/downgrade", json={"tier": "business"}, headers=headers)

    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "NOT_A_DOWNGRADE"


def test_downgrade_requires_an_existing_subscription(client, db_session):
    restaurant = create_restaurant(slug="stripe-downgrade-no-sub", subscription_tier=SubscriptionTier.BUSINESS)
    headers = _manager_headers(restaurant.id)

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/downgrade", json={"tier": "essentiel"}, headers=headers)

    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "NO_SUBSCRIPTION"


def test_billing_portal_returns_a_url_when_a_customer_id_is_on_file(client, db_session, monkeypatch):
    restaurant = _subscribed_restaurant(db_session, slug="stripe-portal-ok")
    headers = _manager_headers(restaurant.id)
    monkeypatch.setattr(
        tenants_router.stripe_gateway, "create_billing_portal_session",
        lambda **kw: "https://billing.stripe.example/p",
    )

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/manage", headers=headers)

    assert res.status_code == 200
    assert res.json()["portal_url"] == "https://billing.stripe.example/p"


def test_billing_portal_404s_without_a_customer_id(client, db_session):
    restaurant = create_restaurant(slug="stripe-portal-none")
    headers = _manager_headers(restaurant.id)

    res = client.post(f"/api/v1/restaurants/{restaurant.id}/subscription/manage", headers=headers)

    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "NO_SUBSCRIPTION"


def test_webhook_endpoint_routes_a_verified_event_to_the_handler(client, db_session, monkeypatch):
    restaurant = create_restaurant(slug="stripe-webhook-endpoint-ok", subscription_tier=SubscriptionTier.ESSENTIEL)
    event = _event(
        "checkout.session.completed",
        {"mode": "subscription", "client_reference_id": str(restaurant.id), "customer": "cus_x", "subscription": "sub_x"},
    )
    monkeypatch.setattr(tenants_router.stripe_gateway, "construct_webhook_event", lambda **kw: event)

    res = client.post(
        "/api/v1/restaurants/stripe-subscription-webhook", content=b"{}", headers={"stripe-signature": "whatever"}
    )

    assert res.status_code == 200
    assert res.json()["result"] == "linked"
    restaurant = db_session.get(Restaurant, restaurant.id)
    assert restaurant.stripe_subscription_id == "sub_x"


def test_webhook_endpoint_rejects_a_bad_signature(client, monkeypatch):
    def _boom(**kw):
        raise stripe_gateway.StripeGatewayError("signature invalide")

    monkeypatch.setattr(tenants_router.stripe_gateway, "construct_webhook_event", _boom)

    res = client.post(
        "/api/v1/restaurants/stripe-subscription-webhook", content=b"{}", headers={"stripe-signature": "bad"}
    )

    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_SIGNATURE"


# --- Restaurant : propriétés Stripe (aucun appel réseau, objet en mémoire) --


def test_stripe_subscription_active_checks_the_subscription_id_not_the_customer_id():
    """Bug corrigé le 2026-09-02 : `stripe_customer_id` SURVIT à une
    annulation (le client Stripe reste valable pour se réabonner), donc le
    lire ici aurait continué à afficher "prélèvement automatique" après une
    résiliation. `stripe_subscription_id`, lui, est effacé par
    `customer.subscription.deleted`."""
    restaurant = Restaurant(name="x", slug="y", stripe_customer_id="cus_1", stripe_subscription_id=None)
    assert restaurant.stripe_subscription_active is False

    restaurant.stripe_subscription_id = "sub_1"
    assert restaurant.stripe_subscription_active is True


def test_stripe_configured_reflects_the_connect_account_id_only():
    assert Restaurant(name="x", slug="y", stripe_account_id=None).stripe_configured is False
    assert Restaurant(name="x", slug="y", stripe_account_id="acct_1").stripe_configured is True


def test_payment_credentials_resolves_the_stripe_account_id_on_the_france_market(monkeypatch):
    monkeypatch.setattr(markets_module, "current_market", FRANCE)
    restaurant = Restaurant(name="x", slug="y", stripe_account_id="acct_1")

    assert restaurant.payment_credentials() == "acct_1"


def test_payment_credentials_ignores_the_stripe_account_id_on_the_tunisia_market(monkeypatch):
    """Symétrique de test_payment_credentials.py côté Konnect : un
    `stripe_account_id` posé n'a pas de sens tant que `current_market` reste
    la Tunisie — jamais un mélange entre fournisseurs."""
    monkeypatch.setattr(markets_module, "current_market", TUNISIA)
    restaurant = Restaurant(name="x", slug="y", stripe_account_id="acct_1")

    assert restaurant.payment_credentials() is None
