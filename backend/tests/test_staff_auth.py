from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_staff

_PASSWORD = "secret1234"


def test_login_success(client):
    restaurant = client.post("/api/v1/restaurants", json={"name": "Café Auth", "slug": "cafe-auth"}).json()
    staff = create_staff(restaurant["id"], password=_PASSWORD)

    res = client.post("/api/v1/auth/login", json={"email": staff.email, "password": _PASSWORD})
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["staff"]["email"] == staff.email
    assert body["staff"]["role"] == "manager"


def test_login_wrong_password_is_rejected(client):
    restaurant = client.post("/api/v1/restaurants", json={"name": "Café Auth2", "slug": "cafe-auth2"}).json()
    staff = create_staff(restaurant["id"], password=_PASSWORD)

    res = client.post("/api/v1/auth/login", json={"email": staff.email, "password": "wrong-password"})
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_login_unknown_email_returns_same_error_as_wrong_password(client):
    """Anti-énumération : on ne distingue jamais "e-mail inconnu" de "mot de passe incorrect"."""
    res = client.post("/api/v1/auth/login", json={"email": "personne@test.local", "password": "whatever123"})
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_me_returns_current_staff(client):
    restaurant = client.post("/api/v1/restaurants", json={"name": "Café Auth3", "slug": "cafe-auth3"}).json()
    staff = create_staff(restaurant["id"])

    res = client.get("/api/v1/auth/me", headers=auth_headers(staff))
    assert res.status_code == 200
    assert res.json()["id"] == staff.id


def test_protected_route_requires_token(client):
    restaurant = client.post("/api/v1/restaurants", json={"name": "Café Auth4", "slug": "cafe-auth4"}).json()

    res = client.get(f"/api/v1/orders/by-restaurant/{restaurant['id']}/active")
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "NOT_AUTHENTICATED"


def test_protected_route_rejects_garbage_token(client):
    restaurant = client.post("/api/v1/restaurants", json={"name": "Café Auth5", "slug": "cafe-auth5"}).json()

    res = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant['id']}/active",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "INVALID_TOKEN"


def test_manager_only_route_rejects_waiter(client):
    restaurant = client.post("/api/v1/restaurants", json={"name": "Café Auth6", "slug": "cafe-auth6"}).json()
    waiter = create_staff(restaurant["id"], role=StaffRole.WAITER)

    res = client.post(
        "/api/v1/menu-items",
        json={"restaurant_id": restaurant["id"], "name": "Thé", "price": 2},
        headers=auth_headers(waiter),
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "FORBIDDEN"
