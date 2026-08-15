"""
Tenue en service réel (Phase 15).

Un service de midi dans un restaurant de 20 tables, joué en une fois : le but
n'est pas de mesurer des microsecondes mais de vérifier qu'aucune commande ne se
perd et qu'aucune requête ne dégénère quand le volume d'une vraie soirée est en
base. Un écran serveur qui met dix secondes à charger en plein rush est aussi
inutilisable qu'un écran cassé.
"""
import time

from tests.conftest import auth_headers, create_restaurant, create_staff

from app.core.config import settings
from app.modules.menu.models import MenuItem
from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table

TABLES = 20
ORDERS = 200
# Seuils volontairement larges : on cherche la dégénérescence (requête en N²,
# chargement complet de la base), pas la performance fine. SQLite en mémoire sur
# une machine de CI partagée n'est pas un banc de mesure.
MAX_SECONDS_PER_ORDER = 0.25
MAX_SECONDS_PER_SCREEN_LOAD = 3.0


def test_a_full_service_does_not_lose_orders_or_degenerate(client, db_session, monkeypatch):
    # Un service réel, ce sont 200 téléphones différents, pas un seul client
    # qui commande 200 fois : chaque commande porte donc son IP, comme derrière
    # le proxy de l'hébergeur en production (Phase 19.3). Sans ça, le test
    # mesurerait le limiteur de débit au lieu de la tenue en charge.
    monkeypatch.setattr(settings, "forwarded_allow_ips", "testclient")

    restaurant = create_restaurant(name="Chez Slah", slug="charge-service")
    tables = [Table(restaurant_id=restaurant.id, label=f"Table {i}") for i in range(1, TABLES + 1)]
    items = [
        MenuItem(restaurant_id=restaurant.id, name=f"Plat {i}", price=10.0 + i, category="Plats")
        for i in range(1, 11)
    ]
    db_session.add_all(tables + items)
    db_session.commit()
    for obj in tables + items:
        db_session.refresh(obj)

    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    kitchen = create_staff(restaurant.id, StaffRole.KITCHEN)

    # --- 200 commandes réparties sur les 20 tables ---
    started = time.monotonic()
    tokens: list[tuple[int, str]] = []
    for index in range(ORDERS):
        table = tables[index % TABLES]
        item = items[index % len(items)]
        response = client.post(
            "/api/v1/orders",
            json={
                "qr_token": table.qr_token,
                "items": [{"menu_item_id": item.id, "quantity": 1 + index % 3}],
            },
            headers={"X-Forwarded-For": f"41.226.{index // 256}.{index % 256}"},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        tokens.append((body["id"], body["public_token"]))
    creation_seconds = time.monotonic() - started

    assert len(tokens) == ORDERS
    assert len({t for _id, t in tokens}) == ORDERS, "deux commandes partagent un token"
    assert creation_seconds / ORDERS < MAX_SECONDS_PER_ORDER, (
        f"{creation_seconds / ORDERS:.3f} s par commande — la création dégénère avec le volume"
    )

    # --- L'écran serveur charge tout le service en attente ---
    started = time.monotonic()
    active = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/active", headers=auth_headers(waiter)
    )
    screen_seconds = time.monotonic() - started
    assert active.status_code == 200
    assert len(active.json()) == ORDERS, "des commandes manquent à l'écran serveur"
    assert screen_seconds < MAX_SECONDS_PER_SCREEN_LOAD, (
        f"{screen_seconds:.2f} s pour charger l'écran serveur — inutilisable en plein rush"
    )

    # --- Le cycle complet sur un échantillon, cuisine comprise ---
    for order_id, _token in tokens[:20]:
        assert client.post(f"/api/v1/orders/{order_id}/confirm", headers=auth_headers(waiter)).status_code == 200
        assert client.post(
            f"/api/v1/orders/{order_id}/send-to-kitchen", headers=auth_headers(waiter)
        ).status_code == 200
        assert client.post(
            f"/api/v1/orders/{order_id}/start-preparation", headers=auth_headers(kitchen)
        ).status_code == 200
        assert client.post(
            f"/api/v1/orders/{order_id}/mark-ready", headers=auth_headers(kitchen)
        ).status_code == 200

    # --- Les pages de direction restent utilisables sur ce volume ---
    for path in (
        f"/api/v1/stats/dashboard/{restaurant.id}",
        f"/api/v1/stats/preuve/{restaurant.id}",
        f"/api/v1/stats/equipe/{restaurant.id}",
    ):
        manager = create_staff(restaurant.id, StaffRole.MANAGER)
        started = time.monotonic()
        response = client.get(path, headers=auth_headers(manager))
        elapsed = time.monotonic() - started
        assert response.status_code == 200, path
        assert elapsed < MAX_SECONDS_PER_SCREEN_LOAD, f"{path} met {elapsed:.2f} s sur 200 commandes"

    # --- Chaque client retrouve SA commande, et seulement la sienne ---
    first_id, first_token = tokens[0]
    _second_id, second_token = tokens[1]
    assert client.get(f"/api/v1/orders/{first_id}", headers={"X-Order-Token": first_token}).status_code == 200
    assert client.get(f"/api/v1/orders/{first_id}", headers={"X-Order-Token": second_token}).status_code == 404
