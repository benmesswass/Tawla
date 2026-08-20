"""
Dashboard plateforme : vue cross-tenant de l'opérateur (Wassim), distincte du
dashboard manager d'un restaurant (`test_dashboard_recette.py`). Un seul
opérateur, un seul mot de passe en variable d'environnement — pas de compte
en base, pas de rôle staff.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.menu.models import MenuItem
from app.modules.orders.models import Order, OrderItem, OrderStatus, PaymentStatus
from app.modules.platform_admin.security import create_admin_token
from app.modules.staff.models import StaffRole
from app.modules.staff.security import hash_password
from app.modules.tables.models import Table
from app.modules.tenants.models import SubscriptionTier

_ADMIN_PASSWORD = "un-mot-de-passe-fort-1234"


def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_admin_token()}"}


def _order(db_session, restaurant, table, item, amount: float, status: OrderStatus, payment_status: PaymentStatus, days_ago: int = 0):
    order = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        status=status,
        payment_status=payment_status,
        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    order.items.append(OrderItem(menu_item_id=item.id, menu_item_name=item.name, unit_price=amount, quantity=1))
    db_session.add(order)
    db_session.commit()
    return order


def _resto_with_item(name: str, slug: str, db_session, tier: SubscriptionTier = SubscriptionTier.BUSINESS):
    restaurant = create_restaurant(name=name, slug=slug, subscription_tier=tier)
    table = Table(restaurant_id=restaurant.id, label="T1")
    item = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=20.0, category="Plats")
    db_session.add_all([table, item])
    db_session.commit()
    db_session.refresh(table)
    db_session.refresh(item)
    return restaurant, table, item


# --- Connexion -----------------------------------------------------------


def test_login_rejected_when_no_password_configured(client):
    """Défaut de dev, ou prod pas encore configurée : refuser, jamais ouvrir."""
    res = client.post("/api/v1/platform-admin/login", json={"password": "n'importe quoi"})
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_login_rejected_with_wrong_password(client):
    with patch("app.modules.platform_admin.router.settings") as mock_settings:
        mock_settings.platform_admin_password_hash = hash_password(_ADMIN_PASSWORD)
        res = client.post("/api/v1/platform-admin/login", json={"password": "mauvais-mot-de-passe"})
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_login_succeeds_with_correct_password(client):
    with patch("app.modules.platform_admin.router.settings") as mock_settings:
        mock_settings.platform_admin_password_hash = hash_password(_ADMIN_PASSWORD)
        res = client.post("/api/v1/platform-admin/login", json={"password": _ADMIN_PASSWORD})
    assert res.status_code == 200
    assert res.json()["access_token"]
    assert res.json()["token_type"] == "bearer"


# --- Protection de /overview ----------------------------------------------


def test_overview_requires_a_token(client):
    res = client.get("/api/v1/platform-admin/overview")
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "NOT_AUTHENTICATED"


def test_overview_rejects_garbage_token(client):
    res = client.get("/api/v1/platform-admin/overview", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_TOKEN"


def test_overview_rejects_a_staff_token(client, db_session):
    """Un token manager n'ouvre pas la vue plateforme : deux domaines, deux
    secrets de signature distincts (voir platform_admin/security.py)."""
    restaurant = create_restaurant(name="Chez Slah")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    res = client.get("/api/v1/platform-admin/overview", headers=auth_headers(manager))
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_TOKEN"


def test_admin_token_is_rejected_by_staff_routes_without_crashing(client):
    """
    Symétrique du test précédent : un token admin ne doit jamais faire planter
    une route staff. `get_current_staff` fait `int(payload["sub"])` hors du
    try/except qui entoure le décodage — sans secret distinct, un token admin
    valide s'y déchiffrerait puis ferait lever un ValueError non rattrapé
    (500) au lieu d'un 401 propre.
    """
    res = client.get("/api/v1/auth/me", headers=_admin_headers())
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_TOKEN"


def test_overview_accepts_a_valid_admin_token(client):
    res = client.get("/api/v1/platform-admin/overview", headers=_admin_headers())
    assert res.status_code == 200


# --- Chiffres agrégés ------------------------------------------------------


def test_overview_on_empty_database_shows_zeroes_not_an_error(client):
    body = client.get("/api/v1/platform-admin/overview", headers=_admin_headers()).json()
    assert body["restaurants_total"] == 0
    assert body["orders_total"] == 0
    assert body["revenue_total_tnd"] == 0
    assert body["restaurants"] == []
    assert len(body["weekly"]) == 12


def test_overview_aggregates_across_every_restaurant(client, db_session):
    resto_a, table_a, item_a = _resto_with_item("Chez Slah", "chez-slah", db_session, SubscriptionTier.PRO)
    resto_b, table_b, item_b = _resto_with_item("Le Marsa Café", "le-marsa-cafe", db_session, SubscriptionTier.ESSENTIEL)

    _order(db_session, resto_a, table_a, item_a, 20.0, OrderStatus.SERVED, PaymentStatus.PAID)
    _order(db_session, resto_a, table_a, item_a, 30.0, OrderStatus.SERVED, PaymentStatus.PAID)
    # Annulée : ne doit compter ni dans les commandes payées ni dans la recette.
    _order(db_session, resto_a, table_a, item_a, 999.0, OrderStatus.CANCELLED, PaymentStatus.UNPAID)

    _order(db_session, resto_b, table_b, item_b, 15.0, OrderStatus.SERVED, PaymentStatus.PAID)

    body = client.get("/api/v1/platform-admin/overview", headers=_admin_headers()).json()

    assert body["restaurants_total"] == 2
    assert body["restaurants_by_tier"]["pro"] == 1
    assert body["restaurants_by_tier"]["essentiel"] == 1
    assert body["restaurants_by_tier"]["business"] == 0

    # Trois commandes réglées comptent dans le total, la quatrième (annulée) non.
    assert body["orders_total"] == 4
    assert body["revenue_total_tnd"] == pytest.approx(65.0)

    by_slug = {r["slug"]: r for r in body["restaurants"]}
    assert by_slug["chez-slah"]["orders_count"] == 3
    assert by_slug["chez-slah"]["revenue_tnd"] == pytest.approx(50.0)
    assert by_slug["le-marsa-cafe"]["orders_count"] == 1
    assert by_slug["le-marsa-cafe"]["revenue_tnd"] == pytest.approx(15.0)

    # Le plus actif (Chez Slah, 3 commandes) doit apparaître en tête.
    assert body["restaurants"][0]["slug"] == "chez-slah"


def test_overview_never_leaks_a_konnect_api_key(client, db_session):
    """La fiche par restaurant n'expose que ce qu'un opérateur a besoin de
    voir pour juger l'usage — jamais un secret d'un restaurant tiers."""
    _resto_with_item("Chez Slah", "chez-slah-2", db_session)

    body = client.get("/api/v1/platform-admin/overview", headers=_admin_headers()).json()

    assert "konnect_api_key_encrypted" not in body["restaurants"][0]
    assert "konnect_api_key" not in body["restaurants"][0]


def test_orders_older_than_thirty_days_are_excluded_from_the_recent_counters(client, db_session):
    resto, table, item = _resto_with_item("Chez Slah", "chez-slah-3", db_session)
    _order(db_session, resto, table, item, 20.0, OrderStatus.SERVED, PaymentStatus.PAID, days_ago=1)
    _order(db_session, resto, table, item, 999.0, OrderStatus.SERVED, PaymentStatus.PAID, days_ago=45)

    body = client.get("/api/v1/platform-admin/overview", headers=_admin_headers()).json()

    assert body["orders_total"] == 2
    assert body["orders_last_30d"] == 1
    assert body["revenue_total_tnd"] == pytest.approx(1019.0)
    assert body["revenue_last_30d_tnd"] == pytest.approx(20.0)
