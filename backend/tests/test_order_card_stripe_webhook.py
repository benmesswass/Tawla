"""
Webhook Stripe Connect — confirmation du paiement carte du CLIENT sur un
Direct Charge (compte connecté du restaurant). Jusqu'ici volontairement
absent (voir stripe_gateway.py, payment_provider.py) : seul le filet de
sécurité `POST /pay/card/check` (retour navigateur) réglait la commande, ce
qui laissait une commande `pending` pour toujours si le client fermait
l'onglet juste après avoir payé.

Même convention que test_stripe_subscription.py : `construct_connect_webhook_event`
monkeypatché plutôt qu'une vraie signature Stripe recalculée à la main —
c'est la logique de routage de l'évènement qui est sous test ici, pas le SDK
Stripe lui-même (déjà couvert côté `construct_webhook_event`/abonnement).
"""
from app.core import stripe_gateway
from app.core.rate_limit import _hits
from app.modules.orders import router as orders_router
from app.modules.orders.models import Order, PaymentMethod, PaymentStatus
from app.modules.staff.models import StaffRole
from app.modules.tenants.models import Restaurant
from tests.conftest import _TestingSessionLocal, auth_headers, create_restaurant, create_staff


def _manager_headers(restaurant_id: int) -> dict[str, str]:
    return auth_headers(create_staff(restaurant_id, StaffRole.MANAGER))


def _fake_stripe_object(data: dict) -> dict:
    class _Obj(dict):
        def to_dict(self):
            return dict(self)

    return _Obj(data)


def _event(event_type: str, obj: dict) -> dict:
    return {"type": event_type, "data": {"object": _fake_stripe_object(obj)}}


def _setup_pending_stripe_order(client, restaurant: Restaurant, *, price: float = 20, quantity: int = 1) -> dict:
    manager_headers = _manager_headers(restaurant.id)
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=manager_headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": price},
        headers=manager_headers,
    ).json()
    order = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": quantity}]},
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=manager_headers)

    db = _TestingSessionLocal()
    db_order = db.get(Order, order["id"])
    db_order.payment_method = PaymentMethod.CARD
    db_order.payment_status = PaymentStatus.PENDING
    db_order.payment_ref = "cs_test_123"
    db.commit()
    db.close()
    return order


def _make_async_settle_stub(result: str):
    async def _stub(db, order_id):
        return result

    return _stub


def test_webhook_rejects_a_bad_signature(client, monkeypatch):
    def _boom(**kw):
        raise stripe_gateway.StripeGatewayError("signature invalide")

    monkeypatch.setattr(orders_router.stripe_gateway, "construct_connect_webhook_event", _boom)

    res = client.post(
        "/api/v1/orders/stripe-card-webhook", content=b"{}", headers={"stripe-signature": "bad"}
    )

    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_SIGNATURE"


def test_webhook_settles_a_pending_order_from_the_session_metadata(client, db_session, monkeypatch):
    restaurant = create_restaurant(slug="stripe-card-webhook-settle")
    order = _setup_pending_stripe_order(client, restaurant)
    event = _event(
        "checkout.session.completed",
        {"mode": "payment", "id": "cs_test_123", "metadata": {"order_id": str(order["id"])}},
    )
    monkeypatch.setattr(orders_router.stripe_gateway, "construct_connect_webhook_event", lambda **kw: event)
    monkeypatch.setattr(
        orders_router.service, "settle_card_payment",
        _make_async_settle_stub("paid"),
    )

    res = client.post(
        "/api/v1/orders/stripe-card-webhook", content=b"{}", headers={"stripe-signature": "whatever"}
    )

    assert res.status_code == 200
    assert res.json()["result"] == "paid"


def test_webhook_ignores_a_subscription_mode_event(client, monkeypatch):
    """Ce endpoint est le pendant CONNECT (paiement carte du client) — un
    évènement d'abonnement (mode="subscription") est celui de
    stripe-subscription-webhook (tenants/router.py), jamais celui-ci."""
    event = _event(
        "checkout.session.completed",
        {"mode": "subscription", "id": "cs_test_sub", "metadata": {"order_id": "1"}},
    )
    monkeypatch.setattr(orders_router.stripe_gateway, "construct_connect_webhook_event", lambda **kw: event)

    def _boom(*a, **kw):
        raise AssertionError("ne doit jamais régler une commande pour un évènement d'abonnement")

    monkeypatch.setattr(orders_router.service, "settle_card_payment", _boom)

    res = client.post(
        "/api/v1/orders/stripe-card-webhook", content=b"{}", headers={"stripe-signature": "whatever"}
    )

    assert res.status_code == 200
    assert res.json()["result"] == "ignored"


def test_webhook_ignores_a_session_without_an_order_id_in_metadata(client, monkeypatch):
    event = _event("checkout.session.completed", {"mode": "payment", "id": "cs_test_no_meta", "metadata": {}})
    monkeypatch.setattr(orders_router.stripe_gateway, "construct_connect_webhook_event", lambda **kw: event)

    def _boom(*a, **kw):
        raise AssertionError("aucun order_id dans metadata — rien à régler")

    monkeypatch.setattr(orders_router.service, "settle_card_payment", _boom)

    res = client.post(
        "/api/v1/orders/stripe-card-webhook", content=b"{}", headers={"stripe-signature": "whatever"}
    )

    assert res.status_code == 200
    assert res.json()["result"] == "ignored"


def test_webhook_ignores_an_unrelated_event_type(client, monkeypatch):
    event = _event("payment_intent.created", {})
    monkeypatch.setattr(orders_router.stripe_gateway, "construct_connect_webhook_event", lambda **kw: event)

    res = client.post(
        "/api/v1/orders/stripe-card-webhook", content=b"{}", headers={"stripe-signature": "whatever"}
    )

    assert res.status_code == 200
    assert res.json()["result"] == "ignored"


# --- Corrections (revue adversariale post-merge) ----------------------------


def test_webhook_settles_on_async_payment_succeeded_too(client, db_session, monkeypatch):
    """Régression : un moyen de paiement ASYNCHRONE (virement, certains
    prélèvements — proposables sur Checkout selon la config du compte
    connecté) ne confirme jamais via `checkout.session.completed` seul,
    Stripe déclenche `checkout.session.async_payment_succeeded` une fois
    l'argent réellement reçu. L'ignorer aurait laissé ces commandes-là
    bloquées en `pending` pour toujours — exactement le défaut que ce
    webhook existe pour fermer."""
    restaurant = create_restaurant(slug="stripe-card-webhook-async")
    order = _setup_pending_stripe_order(client, restaurant)
    event = _event(
        "checkout.session.async_payment_succeeded",
        {"mode": "payment", "id": "cs_test_123", "metadata": {"order_id": str(order["id"])}},
    )
    monkeypatch.setattr(orders_router.stripe_gateway, "construct_connect_webhook_event", lambda **kw: event)
    monkeypatch.setattr(orders_router.service, "settle_card_payment", _make_async_settle_stub("paid"))

    res = client.post(
        "/api/v1/orders/stripe-card-webhook", content=b"{}", headers={"stripe-signature": "whatever"}
    )

    assert res.status_code == 200
    assert res.json()["result"] == "paid"


def test_webhook_ignores_a_non_numeric_order_id_instead_of_crashing(client, monkeypatch):
    """Régression : `int(order_id_raw)` non protégé levait une ValueError
    non rattrapée sur toute valeur illisible — un 500 aurait fait rejouer
    l'évènement par Stripe indéfiniment (poison webhook) plutôt que de
    l'ignorer proprement."""
    event = _event(
        "checkout.session.completed",
        {"mode": "payment", "id": "cs_test_bad_id", "metadata": {"order_id": "not-a-number"}},
    )
    monkeypatch.setattr(orders_router.stripe_gateway, "construct_connect_webhook_event", lambda **kw: event)

    def _boom(*a, **kw):
        raise AssertionError("un order_id illisible ne doit jamais atteindre settle_card_payment")

    monkeypatch.setattr(orders_router.service, "settle_card_payment", _boom)

    res = client.post(
        "/api/v1/orders/stripe-card-webhook", content=b"{}", headers={"stripe-signature": "whatever"}
    )

    assert res.status_code == 200
    assert res.json()["result"] == "ignored"


def test_webhook_is_rate_limited_like_its_konnect_sibling(client, monkeypatch):
    """Régression : contrairement à `order_card_payment_webhook` (Konnect,
    même fichier), ce endpoint n'avait aucun plafond — une signature
    invalide reste bon marché à vérifier, mais rien n'empêchait de la
    spammer sans limite."""
    _hits.clear()
    try:
        def _boom(**kw):
            raise stripe_gateway.StripeGatewayError("signature invalide")

        monkeypatch.setattr(orders_router.stripe_gateway, "construct_connect_webhook_event", _boom)

        for _ in range(20):
            res = client.post(
                "/api/v1/orders/stripe-card-webhook", content=b"{}", headers={"stripe-signature": "bad"}
            )
            assert res.status_code == 401  # signature invalide, pas encore limité

        res = client.post(
            "/api/v1/orders/stripe-card-webhook", content=b"{}", headers={"stripe-signature": "bad"}
        )
        assert res.status_code == 429
        assert res.json()["detail"]["code"] == "RATE_LIMITED"
    finally:
        _hits.clear()
