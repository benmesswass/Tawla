"""
Dashboard plateforme : vue cross-tenant de l'opérateur (Wassim), distincte du
dashboard manager d'un restaurant (`test_dashboard_recette.py`). Compte
`PlatformAdmin` en base (email + mot de passe), pas un compte par
établissement — voir `platform_admin/models.py`.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from tests.conftest import auth_headers, create_restaurant, create_staff

from app.core.config import settings
from app.core.dates import as_utc
from app.core.subscription import tier_price_tnd
from app.modules.menu.models import MenuItem
from app.modules.orders.models import Order, OrderItem, OrderStatus, PaymentStatus
from app.modules.platform_admin import security as admin_security
from app.modules.platform_admin.models import PlatformAdmin
from app.modules.staff.models import StaffRole
from app.modules.staff.security import hash_password
from app.modules.tables.models import Table
from app.modules.tenants.models import Restaurant, SubscriptionTier

_PASSWORD = "un-mot-de-passe-fort-1234"


def _create_admin(db_session, email: str = "wassim@tawla.tn", is_active: bool = True) -> PlatformAdmin:
    admin = PlatformAdmin(email=email, name="Wassim", password_hash=hash_password(_PASSWORD), is_active=is_active)
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


def _admin_headers(admin: PlatformAdmin) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_security.create_access_token(admin.id)}"}


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


def _resto_with_item(name: str, slug: str, db_session, **kwargs):
    restaurant = create_restaurant(name=name, slug=slug, **kwargs)
    table = Table(restaurant_id=restaurant.id, label="T1")
    item = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=20.0, category="Plats")
    db_session.add_all([table, item])
    db_session.commit()
    db_session.refresh(table)
    db_session.refresh(item)
    return restaurant, table, item


# --- Connexion -----------------------------------------------------------


def test_login_rejects_unknown_email(client, db_session):
    _create_admin(db_session)
    res = client.post("/api/v1/platform-admin/login", json={"email": "personne@tawla.tn", "password": _PASSWORD})
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_wrong_password(client, db_session):
    admin = _create_admin(db_session)
    res = client.post("/api/v1/platform-admin/login", json={"email": admin.email, "password": "mauvais"})
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_login_succeeds_with_correct_credentials(client, db_session):
    admin = _create_admin(db_session)
    res = client.post("/api/v1/platform-admin/login", json={"email": admin.email, "password": _PASSWORD})
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["admin"]["email"] == admin.email
    assert body["admin"]["name"] == "Wassim"


def test_login_rejects_disabled_account(client, db_session):
    admin = _create_admin(db_session, is_active=False)
    res = client.post("/api/v1/platform-admin/login", json={"email": admin.email, "password": _PASSWORD})
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "ACCOUNT_DISABLED"


def test_login_email_is_case_insensitive(client, db_session):
    admin = _create_admin(db_session, email="wassim@tawla.tn")
    res = client.post("/api/v1/platform-admin/login", json={"email": "Wassim@Tawla.tn", "password": _PASSWORD})
    assert res.status_code == 200


# --- Création d'un compte admin (2026-08-21ter/quater) ----------------------
# Remplace scripts/create_platform_admin.py : plus besoin d'un accès shell au
# serveur, mais toujours aucune route d'inscription publique — verrouillé par
# un JWT admin existant (formulaire dans /admin) OU ADMIN_CREATION_SECRET
# (bootstrap/dépannage en curl).


def test_create_admin_rejects_wrong_secret(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "admin_creation_secret", "le-vrai-secret")
    res = client.post(
        "/api/v1/platform-admin/admins",
        json={"secret": "un-mauvais-secret", "email": "intrus@tawla.tn", "name": "Intrus", "password": "peu-importe"},
    )
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_SECRET"
    assert db_session.query(PlatformAdmin).filter(PlatformAdmin.email == "intrus@tawla.tn").first() is None


def test_create_admin_succeeds_with_correct_secret(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "admin_creation_secret", "le-vrai-secret")
    res = client.post(
        "/api/v1/platform-admin/admins",
        json={"secret": "le-vrai-secret", "email": "wassim@tawla.tn", "name": "Wassim", "password": _PASSWORD},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "wassim@tawla.tn"
    assert "password" not in body and "password_hash" not in body

    login_res = client.post(
        "/api/v1/platform-admin/login", json={"email": "wassim@tawla.tn", "password": _PASSWORD}
    )
    assert login_res.status_code == 200


def test_create_admin_is_idempotent_by_email_never_creates_a_second_row(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "admin_creation_secret", "le-vrai-secret")
    payload = {"secret": "le-vrai-secret", "email": "wassim@tawla.tn", "name": "Wassim", "password": _PASSWORD}

    client.post("/api/v1/platform-admin/admins", json=payload)
    res2 = client.post("/api/v1/platform-admin/admins", json={**payload, "name": "Wassim Ben Messaoud"})

    assert res2.status_code == 201
    assert res2.json()["name"] == "Wassim Ben Messaoud"
    assert db_session.query(PlatformAdmin).filter(PlatformAdmin.email == "wassim@tawla.tn").count() == 1


def test_create_admin_authorized_via_existing_admin_jwt_ignores_wrong_secret(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "admin_creation_secret", "le-vrai-secret")
    existing_admin = _create_admin(db_session)

    res = client.post(
        "/api/v1/platform-admin/admins",
        json={
            "secret": "un-mauvais-secret", "email": "second@tawla.tn", "name": "Second Admin",
            "password": "un-autre-mot-de-passe-1234",
        },
        headers=_admin_headers(existing_admin),
    )

    assert res.status_code == 201
    assert res.json()["email"] == "second@tawla.tn"


def test_create_admin_with_no_authorization_at_all_is_rejected(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "admin_creation_secret", "le-vrai-secret")
    res = client.post(
        "/api/v1/platform-admin/admins",
        json={"email": "intrus@tawla.tn", "name": "Intrus", "password": "peu-importe"},
    )
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_SECRET"
    assert db_session.query(PlatformAdmin).filter(PlatformAdmin.email == "intrus@tawla.tn").first() is None


def test_create_admin_with_expired_or_garbage_bearer_token_falls_back_to_the_secret(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "admin_creation_secret", "le-vrai-secret")
    res = client.post(
        "/api/v1/platform-admin/admins",
        json={"secret": "le-vrai-secret", "email": "wassim@tawla.tn", "name": "Wassim", "password": _PASSWORD},
        headers={"Authorization": "Bearer un-token-invalide"},
    )
    assert res.status_code == 201


# --- Protection de /overview et confusion de principal ---------------------


def test_overview_requires_a_token(client):
    res = client.get("/api/v1/platform-admin/overview")
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "NOT_AUTHENTICATED"


def test_overview_rejects_garbage_token(client):
    res = client.get("/api/v1/platform-admin/overview", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_TOKEN"


def test_overview_rejects_a_staff_token(client, db_session):
    """
    Un token manager n'ouvre pas la vue plateforme. Staff et PlatformAdmin
    partagent `settings.jwt_secret` (§0 de la spec) : c'est le claim `type`,
    vérifié explicitement, qui les sépare — pas une signature différente.
    """
    restaurant = create_restaurant(name="Chez Slah")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    res = client.get("/api/v1/platform-admin/overview", headers=auth_headers(manager))
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_TOKEN"


def test_admin_token_is_rejected_by_staff_routes_without_crashing(client, db_session):
    """
    Symétrique : un token admin ne doit jamais faire planter ni usurper une
    route staff. `sub` d'un admin est aussi un entier — sans le claim `type`
    vérifié dans `get_current_staff`, ce token se déchiffrerait quand même
    (même secret) et `db.get(Staff, ...)` pourrait tomber sur un Staff dont
    l'ID coïncide, authentifiant silencieusement comme lui.
    """
    admin = _create_admin(db_session)
    res = client.get("/api/v1/auth/me", headers=_admin_headers(admin))
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_TOKEN"


def test_overview_accepts_a_valid_admin_token(client, db_session):
    admin = _create_admin(db_session)
    res = client.get("/api/v1/platform-admin/overview", headers=_admin_headers(admin))
    assert res.status_code == 200


def test_overview_rejects_a_deactivated_admin(client, db_session):
    """Contrôlé à chaque requête, pas seulement au login : un accès désactivé
    en cours de JWT (12h) doit cesser tout de suite — c'est l'écran qui
    expose le plus de données à la fois."""
    admin = _create_admin(db_session)
    headers = _admin_headers(admin)
    admin.is_active = False
    db_session.add(admin)
    db_session.commit()

    res = client.get("/api/v1/platform-admin/overview", headers=headers)
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_TOKEN"


# --- Chiffres agrégés --------------------------------------------------


def test_overview_on_empty_database_shows_zeroes_not_an_error(client, db_session):
    admin = _create_admin(db_session)
    body = client.get("/api/v1/platform-admin/overview", headers=_admin_headers(admin)).json()

    assert body["restaurants_total"] == 0
    assert body["mrr_tnd"] == 0
    assert body["paying_restaurants_count"] == 0
    assert body["orders_last_7d"] == 0
    assert body["gmv_last_7d_tnd"] == 0
    assert body["lost_orders_rate_last_7d"] is None
    assert body["restaurants"] == []
    assert len(body["weekly_signups"]) == 12


def test_mrr_counts_only_active_online_paid_tiers(client, db_session):
    """
    Le cœur de la spec (§1.3) : un MRR qui compterait un pilote gratuit ou un
    palier expiré mentirait à Wassim sur son propre chiffre d'affaires.
    """
    now = datetime.now(timezone.utc)
    admin = _create_admin(db_session)

    # Payé en ligne, encore actif : compte dans le MRR (100 DT = palier Pro).
    paying_pro = create_restaurant(
        name="Le Marsa Café", slug="le-marsa-cafe",
        subscription_tier=SubscriptionTier.PRO, subscription_period_end=now + timedelta(days=15),
    )
    # Pilote fixé à la main par setup_restaurant.py (pas d'échéance) : palier
    # Business affiché dans la répartition, mais jamais dans le MRR.
    create_restaurant(
        name="Chez Slah", slug="chez-slah",
        subscription_tier=SubscriptionTier.BUSINESS, subscription_period_end=None,
    )
    # Payé en ligne mais échéance dépassée : retombe à Essentiel, pas de MRR.
    create_restaurant(
        name="Dar Hammamet", slug="dar-hammamet",
        subscription_tier=SubscriptionTier.PRO, subscription_period_end=now - timedelta(days=5),
    )

    body = client.get("/api/v1/platform-admin/overview", headers=_admin_headers(admin)).json()

    assert body["mrr_tnd"] == pytest.approx(100.0)
    assert body["paying_restaurants_count"] == 1
    assert body["restaurants_by_tier"]["pro"] == 1
    assert body["restaurants_by_tier"]["business"] == 1
    assert body["restaurants_by_tier"]["essentiel"] == 1

    by_slug = {r["slug"]: r for r in body["restaurants"]}
    assert by_slug["le-marsa-cafe"]["effective_tier"] == "pro"
    assert by_slug["dar-hammamet"]["effective_tier"] == "essentiel"
    assert by_slug["chez-slah"]["effective_tier"] == "business"


def test_mrr_excludes_a_free_launch_promo_restaurant_even_while_active(client, db_session):
    """
    Corrigé le 2026-08-21 en même temps que l'offre de lancement devenait
    configurable : un restaurant actif via le mois gratuit
    (is_active=True, has_paid_for_subscription=False) ne paie rien — le
    compter dans le MRR ou paying_restaurants_count mentirait à Wassim,
    exactement comme un pilote gratuit (test ci-dessus).
    """
    now = datetime.now(timezone.utc)
    admin = _create_admin(db_session)
    create_restaurant(
        name="Resto Lancement Gratuit", slug="resto-lancement-gratuit",
        subscription_tier=SubscriptionTier.ESSENTIEL, subscription_period_end=now + timedelta(days=20),
        is_active=True, launch_promo_discount_percent=100, has_paid_for_subscription=False,
    )

    body = client.get("/api/v1/platform-admin/overview", headers=_admin_headers(admin)).json()

    assert body["mrr_tnd"] == 0
    assert body["paying_restaurants_count"] == 0
    by_slug = {r["slug"]: r for r in body["restaurants"]}
    assert by_slug["resto-lancement-gratuit"]["has_paid_for_subscription"] is False
    assert by_slug["resto-lancement-gratuit"]["launch_promo_discount_percent"] == 100


def test_overview_aggregates_orders_across_every_restaurant(client, db_session):
    admin = _create_admin(db_session)
    resto_a, table_a, item_a = _resto_with_item("Chez Slah", "chez-slah-orders", db_session)
    resto_b, table_b, item_b = _resto_with_item("Le Marsa Café", "le-marsa-orders", db_session)

    _order(db_session, resto_a, table_a, item_a, 20.0, OrderStatus.SERVED, PaymentStatus.PAID)
    _order(db_session, resto_a, table_a, item_a, 30.0, OrderStatus.SERVED, PaymentStatus.PAID)
    # Annulée : compte dans le volume de commandes, jamais dans le GMV.
    _order(db_session, resto_a, table_a, item_a, 999.0, OrderStatus.CANCELLED, PaymentStatus.UNPAID)
    _order(db_session, resto_b, table_b, item_b, 15.0, OrderStatus.SERVED, PaymentStatus.PAID)
    # Hors fenêtre de 7 jours : ne doit compter nulle part dans l'agrégat.
    _order(db_session, resto_b, table_b, item_b, 500.0, OrderStatus.SERVED, PaymentStatus.PAID, days_ago=30)

    body = client.get("/api/v1/platform-admin/overview", headers=_admin_headers(admin)).json()

    assert body["orders_last_7d"] == 4
    assert body["gmv_last_7d_tnd"] == pytest.approx(65.0)

    by_slug = {r["slug"]: r for r in body["restaurants"]}
    assert by_slug["chez-slah-orders"]["orders_count"] == 3
    assert by_slug["chez-slah-orders"]["revenue_tnd"] == pytest.approx(50.0)
    # Restaurant le plus actif en tête (3 commandes contre 2).
    assert body["restaurants"][0]["slug"] == "chez-slah-orders"


def test_lost_orders_rate_reuses_the_shared_definition(client, db_session):
    """Même définition que `stats/service.py::lost_orders` — jamais une
    redéfinition (spec §1.6)."""
    admin = _create_admin(db_session)
    resto, table, item = _resto_with_item("Chez Slah", "chez-slah-lost", db_session)

    _order(db_session, resto, table, item, 20.0, OrderStatus.SERVED, PaymentStatus.PAID)
    _order(db_session, resto, table, item, 30.0, OrderStatus.CANCELLED, PaymentStatus.UNPAID)

    body = client.get("/api/v1/platform-admin/overview", headers=_admin_headers(admin)).json()

    assert body["orders_last_7d"] == 2
    assert body["lost_orders_rate_last_7d"] == pytest.approx(0.5)


def test_overview_never_leaks_a_konnect_api_key(client, db_session):
    """La fiche par restaurant n'expose que ce qu'un opérateur a besoin de
    voir pour juger l'usage — jamais un secret d'un restaurant tiers."""
    admin = _create_admin(db_session)
    _resto_with_item("Chez Slah", "chez-slah-secret", db_session)

    body = client.get("/api/v1/platform-admin/overview", headers=_admin_headers(admin)).json()

    assert "konnect_api_key_encrypted" not in body["restaurants"][0]
    assert "konnect_api_key" not in body["restaurants"][0]


# --- Rétention (ouvertures du dashboard manager) ---------------------------


def test_dashboard_views_are_recorded_and_aggregated_per_restaurant(client, db_session):
    """
    Instrumentation minimale de la Phase 24 : chaque ouverture du dashboard
    manager (`GET /stats/dashboard/{id}`) doit apparaître dans l'agrégat
    plateforme — le signal qui précède une résiliation.
    """
    admin = _create_admin(db_session)
    resto_a = create_restaurant(name="Chez Slah", slug="chez-slah-views")
    resto_b = create_restaurant(name="Le Marsa Café", slug="le-marsa-views")
    resto_c = create_restaurant(name="Dar Hammamet", slug="dar-hammamet-views")
    manager_a = create_staff(resto_a.id, StaffRole.MANAGER)
    manager_b = create_staff(resto_b.id, StaffRole.MANAGER)

    # Deux ouvertures pour A, une pour B, aucune pour C.
    client.get(f"/api/v1/stats/dashboard/{resto_a.id}", headers=auth_headers(manager_a))
    client.get(f"/api/v1/stats/dashboard/{resto_a.id}", headers=auth_headers(manager_a))
    client.get(f"/api/v1/stats/dashboard/{resto_b.id}", headers=auth_headers(manager_b))

    body = client.get("/api/v1/platform-admin/overview", headers=_admin_headers(admin)).json()

    assert body["dashboard_views_last_7d"] == 3
    assert body["restaurants_active_last_7d"] == 2

    by_slug = {r["slug"]: r for r in body["restaurants"]}
    assert by_slug["chez-slah-views"]["dashboard_views_last_7d"] == 2
    assert by_slug["le-marsa-views"]["dashboard_views_last_7d"] == 1
    assert by_slug["dar-hammamet-views"]["dashboard_views_last_7d"] == 0
    assert resto_c.slug == "dar-hammamet-views"  # sanity : le bon resto est bien celui à zéro


def test_dashboard_view_survives_even_with_no_orders(client, db_session):
    """L'instrumentation ne doit jamais dépendre du reste du calcul de
    stats : un restaurant sans aucune commande doit quand même être compté
    comme "actif" s'il ouvre son dashboard."""
    admin = _create_admin(db_session)
    resto = create_restaurant(name="Sousse Grill", slug="sousse-grill-views")
    manager = create_staff(resto.id, StaffRole.MANAGER)

    res = client.get(f"/api/v1/stats/dashboard/{resto.id}", headers=auth_headers(manager))
    assert res.status_code == 200

    body = client.get("/api/v1/platform-admin/overview", headers=_admin_headers(admin)).json()
    assert body["dashboard_views_last_7d"] == 1


# --- Offre de lancement : réglages (2026-08-21) -----------------------------


def test_get_launch_campaign_requires_admin_token(client):
    res = client.get("/api/v1/platform-admin/launch-campaign")
    assert res.status_code == 401


def test_get_launch_campaign_returns_defaults_in_a_fresh_database(client, db_session):
    admin = _create_admin(db_session)
    res = client.get("/api/v1/platform-admin/launch-campaign", headers=_admin_headers(admin))
    assert res.status_code == 200
    assert res.json() == {"discount_percent": 100, "max_grants": 20, "grants_used": 0}


def test_get_launch_campaign_counts_grants_already_used(client, db_session):
    admin = _create_admin(db_session)
    create_restaurant(slug="lancement-deja-pris-1", launch_promo_discount_percent=100)
    create_restaurant(slug="lancement-deja-pris-2", launch_promo_discount_percent=50)
    create_restaurant(slug="lancement-jamais-offert", launch_promo_discount_percent=None)

    res = client.get("/api/v1/platform-admin/launch-campaign", headers=_admin_headers(admin))

    assert res.status_code == 200
    assert res.json()["grants_used"] == 2


def test_set_launch_campaign_requires_admin_token(client):
    res = client.put("/api/v1/platform-admin/launch-campaign", json={"discount_percent": 50, "max_grants": 5})
    assert res.status_code == 401


def test_set_launch_campaign_updates_discount_and_cap(client, db_session):
    """« Une seule manip simple » demandée par Wassim (2026-08-21) : régler
    pourcentage + nombre de places d'un coup, persisté, reflété immédiatement
    sur `grants_used`."""
    admin = _create_admin(db_session)
    create_restaurant(slug="lancement-avant-reglage", launch_promo_discount_percent=100)

    res = client.put(
        "/api/v1/platform-admin/launch-campaign",
        json={"discount_percent": 50, "max_grants": 5},
        headers=_admin_headers(admin),
    )

    assert res.status_code == 200
    assert res.json() == {"discount_percent": 50, "max_grants": 5, "grants_used": 1}

    res2 = client.get("/api/v1/platform-admin/launch-campaign", headers=_admin_headers(admin))
    assert res2.json()["discount_percent"] == 50
    assert res2.json()["max_grants"] == 5


def test_set_launch_campaign_rejects_a_percent_above_100(client, db_session):
    admin = _create_admin(db_session)
    res = client.put(
        "/api/v1/platform-admin/launch-campaign",
        json={"discount_percent": 150, "max_grants": 5},
        headers=_admin_headers(admin),
    )
    assert res.status_code == 422


def test_set_launch_campaign_rejects_a_negative_max_grants(client, db_session):
    admin = _create_admin(db_session)
    res = client.put(
        "/api/v1/platform-admin/launch-campaign",
        json={"discount_percent": 50, "max_grants": -1},
        headers=_admin_headers(admin),
    )
    assert res.status_code == 422


def test_set_launch_campaign_does_not_change_a_restaurant_already_registered(client, db_session):
    """La réduction est FIGÉE à l'inscription (voir
    Restaurant.launch_promo_discount_percent) — changer la campagne
    ensuite ne doit jamais recalculer rétroactivement un restaurant déjà
    inscrit sous l'ancien réglage."""
    admin = _create_admin(db_session)
    restaurant = create_restaurant(slug="lancement-immuable", launch_promo_discount_percent=100)

    res = client.put(
        "/api/v1/platform-admin/launch-campaign",
        json={"discount_percent": 20, "max_grants": 20},
        headers=_admin_headers(admin),
    )
    assert res.status_code == 200

    restaurant = db_session.get(Restaurant, restaurant.id)
    assert restaurant.launch_promo_discount_percent == 100


# --- Promo personnalisée au cas par cas (2026-08-21bis) ----------------------


def test_set_restaurant_promo_requires_admin_token(client, db_session):
    restaurant = create_restaurant(slug="promo-toggle-noauth")
    res = client.put(
        f"/api/v1/platform-admin/restaurants/{restaurant.id}/promo",
        json={"discount_percent": 100, "duration_days": 30},
    )
    assert res.status_code == 401


def test_set_restaurant_promo_404s_on_unknown_restaurant(client, db_session):
    admin = _create_admin(db_session)
    res = client.put(
        "/api/v1/platform-admin/restaurants/999999/promo",
        json={"discount_percent": 100, "duration_days": 30},
        headers=_admin_headers(admin),
    )
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "RESTAURANT_NOT_FOUND"


def test_set_restaurant_promo_at_100_percent_activates_for_the_chosen_duration(client, db_session):
    admin = _create_admin(db_session)
    restaurant = create_restaurant(slug="promo-100", is_active=False)

    res = client.put(
        f"/api/v1/platform-admin/restaurants/{restaurant.id}/promo",
        json={"discount_percent": 100, "duration_days": 10},
        headers=_admin_headers(admin),
    )

    assert res.status_code == 200
    body = res.json()
    assert body["custom_promo_discount_percent"] == 100
    restaurant = db_session.get(Restaurant, restaurant.id)
    assert restaurant.is_active is True
    assert restaurant.is_usable is True
    assert as_utc(restaurant.subscription_period_end) < datetime.now(timezone.utc) + timedelta(days=11)

    # Retrait : `duration_days=0` efface la promo mais ne reprend jamais un
    # accès déjà accordé (voir le docstring de l'endpoint).
    res2 = client.put(
        f"/api/v1/platform-admin/restaurants/{restaurant.id}/promo",
        json={"discount_percent": 0, "duration_days": 0},
        headers=_admin_headers(admin),
    )
    assert res2.status_code == 200
    assert res2.json() == {"custom_promo_discount_percent": None, "custom_promo_ends_at": None}
    db_session.expire_all()
    restaurant = db_session.get(Restaurant, restaurant.id)
    assert restaurant.custom_promo_discount_percent is None
    assert restaurant.is_active is True
    assert restaurant.is_usable is True


def test_set_restaurant_promo_at_100_percent_never_shortens_an_existing_paid_period(client, db_session):
    admin = _create_admin(db_session)
    already_paid_until = datetime.now(timezone.utc) + timedelta(days=25)
    restaurant = create_restaurant(
        slug="promo-100-extends", is_active=True, has_paid_for_subscription=True,
        subscription_period_end=already_paid_until,
    )

    res = client.put(
        f"/api/v1/platform-admin/restaurants/{restaurant.id}/promo",
        json={"discount_percent": 100, "duration_days": 5},
        headers=_admin_headers(admin),
    )

    assert res.status_code == 200
    restaurant = db_session.get(Restaurant, restaurant.id)
    # 5 jours de cadeau n'effacent jamais les 25 jours déjà payés.
    assert as_utc(restaurant.subscription_period_end) >= already_paid_until


def test_set_restaurant_promo_under_100_percent_only_discounts_the_next_checkout(client, db_session):
    admin = _create_admin(db_session)
    restaurant = create_restaurant(
        slug="promo-partial", is_active=False, subscription_tier=SubscriptionTier.ESSENTIEL,
    )

    res = client.put(
        f"/api/v1/platform-admin/restaurants/{restaurant.id}/promo",
        json={"discount_percent": 50, "duration_days": 15},
        headers=_admin_headers(admin),
    )

    assert res.status_code == 200
    restaurant = db_session.get(Restaurant, restaurant.id)
    # Ne jamais activer sous 100 % — même logique que l'offre de lancement.
    assert restaurant.is_active is False
    assert tier_price_tnd(restaurant, SubscriptionTier.ESSENTIEL) == 25
