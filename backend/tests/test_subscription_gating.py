"""
Gating par palier d'abonnement (offre à trois paliers, 2026-08-18).

`Restaurant.subscription_tier` existait depuis la Phase 11 sans aucune
fonctionnalité bloquée derrière (voir le commentaire historique dans
`tenants/models.py`). Chaque test ici vérifie qu'Essentiel refuse — ou rend
inerte, selon le cas — une fonctionnalité que Pro ou Business autorise.
"""
from app.modules.staff.models import StaffRole
from app.modules.tenants.models import SubscriptionTier
from tests.conftest import auth_headers, create_restaurant, create_staff, order_headers


def _setup(client, tier: SubscriptionTier, slug: str):
    restaurant = create_restaurant(name="Chez Slah", slug=slug, subscription_tier=tier)
    manager_headers = auth_headers(create_staff(restaurant.id, StaffRole.MANAGER))
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=manager_headers
    ).json()
    item = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Couscous", "price": 20},
        headers=manager_headers,
    ).json()
    return restaurant, manager_headers, table, item


def test_card_payment_forbidden_for_essentiel(client):
    restaurant, manager_headers, table, item = _setup(client, SubscriptionTier.ESSENTIEL, "gating-carte-essentiel")
    order = client.post(
        "/api/v1/orders", json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": 1}]}
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=manager_headers)

    res = client.post(
        f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order)
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "UPGRADE_REQUIRED"
    assert res.json()["detail"]["required_tier"] == "pro"


def test_card_payment_allowed_for_pro(client):
    restaurant, manager_headers, table, item = _setup(client, SubscriptionTier.PRO, "gating-carte-pro")
    order = client.post(
        "/api/v1/orders", json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": 1}]}
    ).json()
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=manager_headers)

    res = client.post(
        f"/api/v1/orders/{order['id']}/pay/card", json={"tip_amount": 0}, headers=order_headers(order)
    )
    assert res.status_code == 200
    assert res.json()["payment_status"] == "paid"


def test_loyalty_phone_is_ignored_for_essentiel(client):
    """
    Pas d'erreur : le client ne doit jamais voir sa commande bloquée pour un
    champ facultatif. La fiche fidélité, elle, ne doit simplement jamais se
    créer.
    """
    restaurant, _headers, table, item = _setup(client, SubscriptionTier.ESSENTIEL, "gating-fidelite-essentiel")

    res = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
            "loyalty_phone": "20111222",
        },
    )
    assert res.status_code == 201

    # `loyalty_phone` n'apparaît jamais dans la réponse client (Phase 12.2) —
    # on vérifie via /lookup que la fiche n'a simplement jamais été créée.
    lookup = client.post(
        "/api/v1/loyalty/lookup", json={"qr_token": table["qr_token"], "phone_number": "20111222"}
    )
    assert lookup.status_code == 404


def test_loyalty_phone_is_recorded_for_pro(client):
    restaurant, _headers, table, item = _setup(client, SubscriptionTier.PRO, "gating-fidelite-pro")

    res = client.post(
        "/api/v1/orders",
        json={
            "qr_token": table["qr_token"],
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
            "loyalty_phone": "20111333",
        },
    )
    assert res.status_code == 201

    lookup = client.post(
        "/api/v1/loyalty/lookup", json={"qr_token": table["qr_token"], "phone_number": "20111333"}
    )
    assert lookup.status_code == 200
    assert lookup.json()["order_count"] == 0


def test_suggestions_forbidden_for_essentiel(client):
    restaurant, manager_headers, _table, item = _setup(
        client, SubscriptionTier.ESSENTIEL, "gating-suggestions-essentiel"
    )
    other = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Thé", "price": 3},
        headers=manager_headers,
    ).json()

    res = client.put(
        f"/api/v1/menu-items/{item['id']}/suggestions",
        json={"suggested_item_ids": [other["id"]]},
        headers=manager_headers,
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "UPGRADE_REQUIRED"


def test_suggestions_allowed_for_pro(client):
    restaurant, manager_headers, _table, item = _setup(client, SubscriptionTier.PRO, "gating-suggestions-pro")
    other = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant.id, "name": "Thé", "price": 3},
        headers=manager_headers,
    ).json()

    res = client.put(
        f"/api/v1/menu-items/{item['id']}/suggestions",
        json={"suggested_item_ids": [other["id"]]},
        headers=manager_headers,
    )
    assert res.status_code == 200


def test_csv_import_forbidden_for_essentiel(client):
    _restaurant, manager_headers, _table, _item = _setup(client, SubscriptionTier.ESSENTIEL, "gating-csv-essentiel")

    res = client.post(
        "/api/v1/menu-items/import-csv",
        json={"content": "nom,prix\nBrik,4\n"},
        headers=manager_headers,
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "UPGRADE_REQUIRED"


def test_photo_upload_forbidden_for_essentiel(client):
    _restaurant, manager_headers, _table, item = _setup(client, SubscriptionTier.ESSENTIEL, "gating-photo-essentiel")

    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c6360000002000100ffff03000006000557bfabd400"
        "00000049454e44ae426082"
    )
    res = client.put(
        f"/api/v1/menu-items/{item['id']}/image",
        files={"file": ("plat.png", png, "image/png")},
        headers=manager_headers,
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "UPGRADE_REQUIRED"


def test_table_zone_is_ignored_for_essentiel(client):
    restaurant, manager_headers, _table, _item = _setup(client, SubscriptionTier.ESSENTIEL, "gating-zone-essentiel")

    res = client.post(
        "/api/v1/tables",
        json={"restaurant_id": restaurant.id, "label": "Terrasse 1", "zone": "Terrasse"},
        headers=manager_headers,
    )
    assert res.status_code == 201
    assert res.json()["zone"] is None


def test_table_zone_is_kept_for_pro(client):
    restaurant, manager_headers, _table, _item = _setup(client, SubscriptionTier.PRO, "gating-zone-pro")

    res = client.post(
        "/api/v1/tables",
        json={"restaurant_id": restaurant.id, "label": "Terrasse 1", "zone": "Terrasse"},
        headers=manager_headers,
    )
    assert res.status_code == 201
    assert res.json()["zone"] == "Terrasse"


def test_floor_plan_save_forbidden_for_essentiel(client):
    restaurant, manager_headers, table, _item = _setup(client, SubscriptionTier.ESSENTIEL, "gating-plan-essentiel")

    res = client.put(
        f"/api/v1/tables/plan/{restaurant.id}",
        json={"placements": [{"table_id": table["id"], "pos_x": 10, "pos_y": 10}]},
        headers=manager_headers,
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "UPGRADE_REQUIRED"


def test_ramadan_mode_forbidden_for_essentiel(client):
    restaurant, manager_headers, _table, _item = _setup(
        client, SubscriptionTier.ESSENTIEL, "gating-ramadan-essentiel"
    )

    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/ramadan-mode",
        json={"enabled": True, "iftar_time": "2027-03-10T19:00:00Z"},
        headers=manager_headers,
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "UPGRADE_REQUIRED"


def test_legal_info_forbidden_for_essentiel(client):
    restaurant, manager_headers, _table, _item = _setup(client, SubscriptionTier.ESSENTIEL, "gating-legal-essentiel")

    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/legal-info",
        json={"legal_address": "12 rue de la République, 75011 Paris"},
        headers=manager_headers,
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "UPGRADE_REQUIRED"
    assert res.json()["detail"]["required_tier"] == "pro"


def test_legal_info_allowed_for_pro(client):
    restaurant, manager_headers, _table, _item = _setup(client, SubscriptionTier.PRO, "gating-legal-pro")

    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/legal-info",
        json={"legal_address": "12 rue de la République, 75011 Paris"},
        headers=manager_headers,
    )
    assert res.status_code == 200
    assert res.json()["legal_address"] == "12 rue de la République, 75011 Paris"


def test_proof_stats_forbidden_for_essentiel(client):
    restaurant, manager_headers, _table, _item = _setup(client, SubscriptionTier.ESSENTIEL, "gating-preuve-essentiel")

    res = client.get(f"/api/v1/stats/preuve/{restaurant.id}", headers=manager_headers)
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "UPGRADE_REQUIRED"


def test_proof_stats_allowed_for_pro(client):
    restaurant, manager_headers, _table, _item = _setup(client, SubscriptionTier.PRO, "gating-preuve-pro")

    res = client.get(f"/api/v1/stats/preuve/{restaurant.id}", headers=manager_headers)
    assert res.status_code == 200


def test_team_report_forbidden_for_pro(client):
    """Business seul — Pro n'y donne pas accès, contrairement aux autres
    fonctionnalités Pro+."""
    restaurant, manager_headers, _table, _item = _setup(client, SubscriptionTier.PRO, "gating-equipe-pro")

    res = client.get(f"/api/v1/stats/equipe/{restaurant.id}", headers=manager_headers)
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "UPGRADE_REQUIRED"
    assert res.json()["detail"]["required_tier"] == "business"


def test_team_report_allowed_for_business(client):
    restaurant, manager_headers, _table, _item = _setup(client, SubscriptionTier.BUSINESS, "gating-equipe-business")

    res = client.get(f"/api/v1/stats/equipe/{restaurant.id}", headers=manager_headers)
    assert res.status_code == 200


def test_push_notification_not_sent_for_pro(client, monkeypatch):
    """Business seul déclenche l'envoi réel — vérifié en observant l'appel à
    `send_push_notification`, pas son effet (aucune clé VAPID en test)."""
    import app.modules.orders.service as orders_service

    calls = []
    monkeypatch.setattr(orders_service, "send_push_notification", lambda *a, **k: calls.append((a, k)))

    restaurant, manager_headers, table, item = _setup(client, SubscriptionTier.PRO, "gating-push-pro")
    order = client.post(
        "/api/v1/orders", json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": 1}]}
    ).json()
    client.post(
        f"/api/v1/orders/{order['id']}/push-subscription",
        json={"endpoint": "https://push.example/x", "keys": {"p256dh": "x", "auth": "y"}},
        headers=order_headers(order),
    )
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=manager_headers)
    client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=manager_headers)
    client.post(f"/api/v1/orders/{order['id']}/start-preparation", headers=manager_headers)
    client.post(f"/api/v1/orders/{order['id']}/mark-ready", headers=manager_headers)

    assert calls == []


def test_push_notification_sent_for_business(client, monkeypatch):
    import app.modules.orders.service as orders_service

    calls = []
    monkeypatch.setattr(orders_service, "send_push_notification", lambda *a, **k: calls.append((a, k)))

    restaurant, manager_headers, table, item = _setup(client, SubscriptionTier.BUSINESS, "gating-push-business")
    order = client.post(
        "/api/v1/orders", json={"qr_token": table["qr_token"], "items": [{"menu_item_id": item["id"], "quantity": 1}]}
    ).json()
    client.post(
        f"/api/v1/orders/{order['id']}/push-subscription",
        json={"endpoint": "https://push.example/x", "keys": {"p256dh": "x", "auth": "y"}},
        headers=order_headers(order),
    )
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=manager_headers)
    client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=manager_headers)
    client.post(f"/api/v1/orders/{order['id']}/start-preparation", headers=manager_headers)
    client.post(f"/api/v1/orders/{order['id']}/mark-ready", headers=manager_headers)

    assert len(calls) == 1
