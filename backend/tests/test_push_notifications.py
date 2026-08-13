from unittest.mock import patch

from tests.conftest import auth_headers, create_restaurant, create_staff, order_headers, order_headers

_FAKE_SUBSCRIPTION = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/fake-endpoint",
    "keys": {"p256dh": "fake-p256dh-key", "auth": "fake-auth-key"},
}


def _setup_restaurant_with_item(client):
    restaurant = create_restaurant(name="Café Push", slug="cafe-push")
    headers = auth_headers(create_staff(restaurant.id))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Café", "price": 3.5},
        headers=headers,
    ).json()
    return restaurant, table, item, headers


def _order_to_ready(client, restaurant, table, item, headers):
    order = client.post(
        "/api/v1/orders",
        json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"]}]},
    ).json()
    order_id = order["id"]
    client.post(f"/api/v1/orders/{order_id}/confirm", headers=headers)
    client.post(f"/api/v1/orders/{order_id}/send-to-kitchen", headers=headers)
    client.post(f"/api/v1/orders/{order_id}/start-preparation", headers=headers)
    # La commande entière, pas seulement son id : les routes client (abonnement
    # push) exigent désormais son public_token.
    return order


def test_vapid_public_key_endpoint_returns_configured_value(client):
    res = client.get("/api/v1/notifications/vapid-public-key")
    assert res.status_code == 200
    assert "public_key" in res.json()


def test_client_can_save_push_subscription(client):
    restaurant, table, item, headers = _setup_restaurant_with_item(client)
    order = _order_to_ready(client, restaurant, table, item, headers)

    res = client.post(f"/api/v1/orders/{order['id']}/push-subscription", json=_FAKE_SUBSCRIPTION, headers=order_headers(order))
    assert res.status_code == 204


def test_push_subscription_on_unknown_order_returns_404(client):
    res = client.post("/api/v1/orders/999999/push-subscription", json=_FAKE_SUBSCRIPTION)
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "ORDER_NOT_FOUND"


def test_marking_ready_sends_push_when_subscribed_and_configured(client):
    restaurant, table, item, headers = _setup_restaurant_with_item(client)
    order = _order_to_ready(client, restaurant, table, item, headers)
    client.post(f"/api/v1/orders/{order['id']}/push-subscription", json=_FAKE_SUBSCRIPTION, headers=order_headers(order))

    with patch("app.core.push.settings") as mock_settings, patch("app.core.push.webpush") as mock_webpush:
        mock_settings.vapid_public_key = "fake-public-key"
        mock_settings.vapid_private_key = "fake-private-key"
        mock_settings.vapid_contact_email = "contact@tawla.tn"

        res = client.post(f"/api/v1/orders/{order['id']}/mark-ready", headers=headers)
        assert res.status_code == 200

        mock_webpush.assert_called_once()
        call_kwargs = mock_webpush.call_args.kwargs
        assert call_kwargs["subscription_info"] == _FAKE_SUBSCRIPTION
        assert "prête" in call_kwargs["data"] or "pr\\u00eate" in call_kwargs["data"]


def test_marking_ready_without_subscription_never_calls_webpush(client):
    restaurant, table, item, headers = _setup_restaurant_with_item(client)
    order = _order_to_ready(client, restaurant, table, item, headers)

    with patch("app.core.push.webpush") as mock_webpush:
        res = client.post(f"/api/v1/orders/{order['id']}/mark-ready", headers=headers)
        assert res.status_code == 200
        mock_webpush.assert_not_called()


def test_marking_ready_never_fails_when_vapid_not_configured_even_with_subscription(client):
    """
    Comportement par défaut de l'environnement de test/dev (pas de clés
    VAPID) : la transition de statut doit réussir normalement, la
    notification étant un simple no-op silencieux.
    """
    restaurant, table, item, headers = _setup_restaurant_with_item(client)
    order = _order_to_ready(client, restaurant, table, item, headers)
    client.post(f"/api/v1/orders/{order['id']}/push-subscription", json=_FAKE_SUBSCRIPTION, headers=order_headers(order))

    res = client.post(f"/api/v1/orders/{order['id']}/mark-ready", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "ready"


def test_marking_ready_never_fails_even_if_push_send_raises(client):
    """
    Un abonnement expiré ou une erreur réseau vers le service de push ne
    doit jamais casser le passage en "prête" côté cuisine — best-effort.
    """
    restaurant, table, item, headers = _setup_restaurant_with_item(client)
    order = _order_to_ready(client, restaurant, table, item, headers)
    client.post(f"/api/v1/orders/{order['id']}/push-subscription", json=_FAKE_SUBSCRIPTION, headers=order_headers(order))

    with patch("app.core.push.settings") as mock_settings, patch("app.core.push.webpush") as mock_webpush:
        mock_settings.vapid_public_key = "fake-public-key"
        mock_settings.vapid_private_key = "fake-private-key"
        mock_settings.vapid_contact_email = "contact@tawla.tn"
        mock_webpush.side_effect = RuntimeError("subscription expired")

        res = client.post(f"/api/v1/orders/{order['id']}/mark-ready", headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "ready"
