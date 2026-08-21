"""
Écran admin (2026-08-20) : secret unique partagé (Settings.admin_secret),
pas de compte ni de rôle — Wassim est seul utilisateur. Ces tests couvrent le
fail-closed (secret absent/faux) et que la dérogation promo débloque
réellement une route gated, pas seulement le champ en base.
"""
from app.modules.tenants.models import SubscriptionTier
from tests.conftest import create_restaurant


def test_list_restaurants_rejected_without_admin_secret_configured(client):
    """Fail-closed : ADMIN_SECRET absent de l'environnement doit fermer la
    route à tout le monde, même avec un en-tête plausible — jamais comparer
    "" à "" avec succès."""
    res = client.get("/api/v1/admin/restaurants", headers={"X-Admin-Secret": "whatever"})
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_ADMIN_SECRET"


def test_list_restaurants_rejected_with_wrong_secret(client, monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "the-real-secret")
    from app.core.config import settings
    monkeypatch.setattr(settings, "admin_secret", "the-real-secret")

    res = client.get("/api/v1/admin/restaurants", headers={"X-Admin-Secret": "not-it"})

    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_ADMIN_SECRET"


def test_list_restaurants_rejected_with_no_header_at_all(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "admin_secret", "the-real-secret")

    res = client.get("/api/v1/admin/restaurants")

    assert res.status_code == 401


def test_list_restaurants_succeeds_with_the_correct_secret(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "admin_secret", "the-real-secret")
    create_restaurant(slug="admin-list-a", is_active=False)
    create_restaurant(slug="admin-list-b", is_active=True)

    res = client.get("/api/v1/admin/restaurants", headers={"X-Admin-Secret": "the-real-secret"})

    assert res.status_code == 200
    slugs = {r["slug"] for r in res.json()}
    assert {"admin-list-a", "admin-list-b"} <= slugs


def test_set_promo_unblocks_an_inactive_restaurant(client, monkeypatch):
    """Le vrai test : pas juste que promo_gratuit passe à True en base, mais
    qu'une route staff gated s'ouvre réellement à la suite — is_usable."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "admin_secret", "the-real-secret")
    restaurant = create_restaurant(
        slug="admin-promo-unblocks", subscription_tier=SubscriptionTier.ESSENTIEL, is_active=False
    )
    from tests.conftest import auth_headers, create_staff
    from app.modules.staff.models import StaffRole
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    blocked = client.get(f"/api/v1/tables/by-restaurant/{restaurant.id}", headers=auth_headers(manager))
    assert blocked.status_code == 402

    promo_res = client.patch(
        f"/api/v1/admin/restaurants/{restaurant.id}/promo",
        json={"promo_gratuit": True},
        headers={"X-Admin-Secret": "the-real-secret"},
    )
    assert promo_res.status_code == 200
    assert promo_res.json()["promo_gratuit"] is True

    unblocked = client.get(f"/api/v1/tables/by-restaurant/{restaurant.id}", headers=auth_headers(manager))
    assert unblocked.status_code == 200


def test_set_promo_can_be_revoked(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "admin_secret", "the-real-secret")
    restaurant = create_restaurant(slug="admin-promo-revoke", is_active=False, promo_gratuit=True)
    from tests.conftest import auth_headers, create_staff
    from app.modules.staff.models import StaffRole
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    res = client.patch(
        f"/api/v1/admin/restaurants/{restaurant.id}/promo",
        json={"promo_gratuit": False},
        headers={"X-Admin-Secret": "the-real-secret"},
    )
    assert res.status_code == 200

    blocked = client.get(f"/api/v1/tables/by-restaurant/{restaurant.id}", headers=auth_headers(manager))
    assert blocked.status_code == 402


def test_set_promo_rejects_an_unknown_restaurant(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "admin_secret", "the-real-secret")

    res = client.patch(
        "/api/v1/admin/restaurants/999999/promo",
        json={"promo_gratuit": True},
        headers={"X-Admin-Secret": "the-real-secret"},
    )

    assert res.status_code == 404
