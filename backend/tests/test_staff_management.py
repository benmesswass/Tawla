"""
Gestion de l'équipe par le manager (Phase 12.1).

Ce module n'existait pas avant : un établissement inscrit via `/auth/register`
n'avait aucun moyen de créer un compte serveur ou cuisine, donc ni le pool
serveur ni l'écran cuisine n'étaient utilisables sans écrire en base à la main.
Les tests couvrent les vrais risques : isolation entre restaurants, escalade de
rôle, et le verrouillage définitif d'un restaurant qui perdrait son dernier
manager actif.
"""
from tests.conftest import auth_headers, create_staff

from app.modules.staff.models import StaffRole


def _restaurant(client, slug: str = "resto-equipe") -> int:
    response = client.post("/api/v1/auth/register", json={
        "restaurant_name": slug,
        "manager_name": "Manager",
        "email": f"{slug}@test.local",
        "password": "manager-pass-1234",
    })
    assert response.status_code == 201
    return response.json()["staff"]["restaurant_id"]


def test_manager_creates_waiter_with_generated_password(client):
    restaurant_id = _restaurant(client)
    manager = create_staff(restaurant_id, StaffRole.MANAGER)

    response = client.post("/api/v1/staff", json={
        "name": "Sami",
        "email": "Sami@Resto.TN",  # casse mixte volontaire
        "role": "waiter",
    }, headers=auth_headers(manager))

    assert response.status_code == 201
    body = response.json()
    assert body["staff"]["role"] == "waiter"
    assert body["staff"]["restaurant_id"] == restaurant_id
    assert body["staff"]["email"] == "sami@resto.tn"
    assert body["staff"]["is_active"] is True

    # Le mot de passe généré n'est lisible qu'ici, et il fonctionne.
    password = body["temporary_password"]
    assert password
    login = client.post("/api/v1/auth/login", json={"email": "sami@resto.tn", "password": password})
    assert login.status_code == 200
    assert login.json()["staff"]["role"] == "waiter"


def test_manager_can_set_the_password_himself(client):
    restaurant_id = _restaurant(client)
    manager = create_staff(restaurant_id, StaffRole.MANAGER)

    response = client.post("/api/v1/staff", json={
        "name": "Cuisine",
        "email": "cuisine@resto.tn",
        "role": "kitchen",
        "password": "cuisine-pass-1234",
    }, headers=auth_headers(manager))

    assert response.status_code == 201
    # Aucun mot de passe temporaire renvoyé quand le manager en fournit un.
    assert response.json()["temporary_password"] is None
    login = client.post(
        "/api/v1/auth/login", json={"email": "cuisine@resto.tn", "password": "cuisine-pass-1234"}
    )
    assert login.status_code == 200


def test_new_account_always_lands_in_the_manager_restaurant(client):
    """Le payload ne porte pas de restaurant_id : impossible de créer un
    compte chez le voisin, même en le forçant."""
    restaurant_a = _restaurant(client, "resto-a")
    restaurant_b = _restaurant(client, "resto-b")
    manager_a = create_staff(restaurant_a, StaffRole.MANAGER)

    response = client.post("/api/v1/staff", json={
        "name": "Infiltré",
        "email": "infiltre@resto.tn",
        "role": "manager",
        "restaurant_id": restaurant_b,  # ignoré par le schéma
    }, headers=auth_headers(manager_a))

    assert response.status_code == 201
    assert response.json()["staff"]["restaurant_id"] == restaurant_a


def test_waiter_and_kitchen_cannot_create_accounts(client):
    restaurant_id = _restaurant(client)

    for role in (StaffRole.WAITER, StaffRole.KITCHEN):
        staff = create_staff(restaurant_id, role)
        response = client.post("/api/v1/staff", json={
            "name": "Complice",
            "email": f"complice-{role.value}@resto.tn",
            "role": "manager",
        }, headers=auth_headers(staff))
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "FORBIDDEN"


def test_duplicate_email_is_rejected(client):
    restaurant_id = _restaurant(client)
    manager = create_staff(restaurant_id, StaffRole.MANAGER)
    payload = {"name": "Sami", "email": "doublon@resto.tn", "role": "waiter"}

    assert client.post("/api/v1/staff", json=payload, headers=auth_headers(manager)).status_code == 201
    second = client.post("/api/v1/staff", json=payload, headers=auth_headers(manager))
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "EMAIL_EXISTS"


def test_listing_is_scoped_to_the_manager_restaurant(client):
    restaurant_a = _restaurant(client, "resto-a")
    restaurant_b = _restaurant(client, "resto-b")
    manager_a = create_staff(restaurant_a, StaffRole.MANAGER)
    create_staff(restaurant_b, StaffRole.WAITER)

    listed = client.get(f"/api/v1/staff/by-restaurant/{restaurant_a}", headers=auth_headers(manager_a))
    assert listed.status_code == 200
    assert {row["restaurant_id"] for row in listed.json()} == {restaurant_a}

    forbidden = client.get(f"/api/v1/staff/by-restaurant/{restaurant_b}", headers=auth_headers(manager_a))
    assert forbidden.status_code == 403


def test_manager_cannot_touch_staff_of_another_restaurant(client):
    restaurant_a = _restaurant(client, "resto-a")
    restaurant_b = _restaurant(client, "resto-b")
    manager_a = create_staff(restaurant_a, StaffRole.MANAGER)
    waiter_b = create_staff(restaurant_b, StaffRole.WAITER)

    patched = client.patch(
        f"/api/v1/staff/{waiter_b.id}", json={"is_active": False}, headers=auth_headers(manager_a)
    )
    assert patched.status_code == 404
    assert patched.json()["detail"]["code"] == "STAFF_NOT_FOUND"

    reset = client.post(f"/api/v1/staff/{waiter_b.id}/reset-password", headers=auth_headers(manager_a))
    assert reset.status_code == 404


def test_disabled_account_loses_login_and_existing_token(client):
    """Le point qui compte : un JWT vit 12h, donc la désactivation doit
    invalider un token déjà émis, pas seulement le prochain login."""
    restaurant_id = _restaurant(client)
    manager = create_staff(restaurant_id, StaffRole.MANAGER)
    waiter = create_staff(restaurant_id, StaffRole.WAITER, password="waiter-pass-1234")
    waiter_headers = auth_headers(waiter)

    # Le token fonctionne tant que le compte est actif.
    assert client.get("/api/v1/auth/me", headers=waiter_headers).status_code == 200

    disabled = client.patch(
        f"/api/v1/staff/{waiter.id}", json={"is_active": False}, headers=auth_headers(manager)
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False

    # Token déjà émis : refusé.
    stale = client.get("/api/v1/auth/me", headers=waiter_headers)
    assert stale.status_code == 401
    assert stale.json()["detail"]["code"] == "ACCOUNT_DISABLED"

    # Nouveau login : refusé aussi.
    login = client.post(
        "/api/v1/auth/login", json={"email": waiter.email, "password": "waiter-pass-1234"}
    )
    assert login.status_code == 401
    assert login.json()["detail"]["code"] == "ACCOUNT_DISABLED"


def test_disabled_account_cannot_work_on_orders(client):
    """Vérifie que la désactivation coupe une route métier réelle, pas
    seulement /auth/me."""
    restaurant_id = _restaurant(client)
    manager = create_staff(restaurant_id, StaffRole.MANAGER)
    waiter = create_staff(restaurant_id, StaffRole.WAITER)
    waiter_headers = auth_headers(waiter)

    client.patch(f"/api/v1/staff/{waiter.id}", json={"is_active": False}, headers=auth_headers(manager))

    response = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant_id}/active", headers=waiter_headers
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "ACCOUNT_DISABLED"


def test_reactivated_account_works_again(client):
    restaurant_id = _restaurant(client)
    manager = create_staff(restaurant_id, StaffRole.MANAGER)
    waiter = create_staff(restaurant_id, StaffRole.WAITER, password="waiter-pass-1234")

    client.patch(f"/api/v1/staff/{waiter.id}", json={"is_active": False}, headers=auth_headers(manager))
    client.patch(f"/api/v1/staff/{waiter.id}", json={"is_active": True}, headers=auth_headers(manager))

    login = client.post(
        "/api/v1/auth/login", json={"email": waiter.email, "password": "waiter-pass-1234"}
    )
    assert login.status_code == 200


def test_last_active_manager_cannot_be_disabled(client):
    """Un restaurant sans manager actif est verrouillé définitivement :
    plus personne ne peut créer de compte ni rouvrir l'accès."""
    restaurant_id = _restaurant(client)
    manager = create_staff(restaurant_id, StaffRole.MANAGER)
    # Le manager créé par /auth/register compte aussi : on le désactive
    # d'abord pour que `manager` soit réellement le dernier actif.
    registered = client.get(f"/api/v1/staff/by-restaurant/{restaurant_id}", headers=auth_headers(manager))
    for row in registered.json():
        if row["id"] != manager.id and row["role"] == "manager":
            client.patch(f"/api/v1/staff/{row['id']}", json={"is_active": False}, headers=auth_headers(manager))

    response = client.patch(
        f"/api/v1/staff/{manager.id}", json={"is_active": False}, headers=auth_headers(manager)
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "LAST_ACTIVE_MANAGER"


def test_last_active_manager_cannot_be_demoted(client):
    """Même invariant par l'autre porte : le changement de rôle."""
    restaurant_id = _restaurant(client)
    manager = create_staff(restaurant_id, StaffRole.MANAGER)
    listed = client.get(f"/api/v1/staff/by-restaurant/{restaurant_id}", headers=auth_headers(manager))
    for row in listed.json():
        if row["id"] != manager.id and row["role"] == "manager":
            client.patch(f"/api/v1/staff/{row['id']}", json={"is_active": False}, headers=auth_headers(manager))

    response = client.patch(
        f"/api/v1/staff/{manager.id}", json={"role": "waiter"}, headers=auth_headers(manager)
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "LAST_ACTIVE_MANAGER"


def test_manager_can_be_disabled_when_another_one_remains(client):
    restaurant_id = _restaurant(client)
    first = create_staff(restaurant_id, StaffRole.MANAGER)
    second = create_staff(restaurant_id, StaffRole.MANAGER)

    response = client.patch(
        f"/api/v1/staff/{second.id}", json={"is_active": False}, headers=auth_headers(first)
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_reset_password_invalidates_the_previous_one(client):
    restaurant_id = _restaurant(client)
    manager = create_staff(restaurant_id, StaffRole.MANAGER)
    waiter = create_staff(restaurant_id, StaffRole.WAITER, password="waiter-pass-1234")

    response = client.post(f"/api/v1/staff/{waiter.id}/reset-password", headers=auth_headers(manager))
    assert response.status_code == 200
    new_password = response.json()["temporary_password"]
    assert new_password

    old = client.post("/api/v1/auth/login", json={"email": waiter.email, "password": "waiter-pass-1234"})
    assert old.status_code == 401

    new = client.post("/api/v1/auth/login", json={"email": waiter.email, "password": new_password})
    assert new.status_code == 200


def test_renaming_and_role_change_are_applied(client):
    restaurant_id = _restaurant(client)
    manager = create_staff(restaurant_id, StaffRole.MANAGER)
    waiter = create_staff(restaurant_id, StaffRole.WAITER)

    response = client.patch(
        f"/api/v1/staff/{waiter.id}",
        json={"name": "Sami B.", "role": "kitchen"},
        headers=auth_headers(manager),
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Sami B."
    assert response.json()["role"] == "kitchen"


def test_staff_management_requires_authentication(client):
    restaurant_id = _restaurant(client)

    assert client.post("/api/v1/staff", json={
        "name": "Anonyme", "email": "anon@resto.tn", "role": "manager",
    }).status_code == 401
    assert client.get(f"/api/v1/staff/by-restaurant/{restaurant_id}").status_code == 401
