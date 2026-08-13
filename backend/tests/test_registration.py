import uuid

_PASSWORD = "onboard1234"


def test_register_creates_restaurant_and_manager(client):
    email = f"owner-{uuid.uuid4().hex[:8]}@test.local"
    res = client.post(
        "/api/v1/auth/register",
        json={
            "restaurant_name": "Café des Nattes",
            "manager_name": "Amina",
            "email": email,
            "password": _PASSWORD,
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["access_token"]
    assert body["staff"]["email"] == email
    assert body["staff"]["role"] == "manager"
    assert body["staff"]["restaurant_id"]


def test_register_derives_slug_from_restaurant_name(client):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "restaurant_name": "Le Petit Café",
            "manager_name": "Sami",
            "email": f"owner-{uuid.uuid4().hex[:8]}@test.local",
            "password": _PASSWORD,
        },
    )
    restaurant_id = res.json()["staff"]["restaurant_id"]
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}

    restaurant = client.get(f"/api/v1/restaurants/{restaurant_id}", headers=headers).json()
    assert restaurant["slug"] == "le-petit-cafe"


def test_register_dedupes_slug_on_name_collision(client):
    common_name = f"Resto Doublon {uuid.uuid4().hex[:6]}"
    res1 = client.post(
        "/api/v1/auth/register",
        json={
            "restaurant_name": common_name,
            "manager_name": "Manager 1",
            "email": f"owner-{uuid.uuid4().hex[:8]}@test.local",
            "password": _PASSWORD,
        },
    )
    res2 = client.post(
        "/api/v1/auth/register",
        json={
            "restaurant_name": common_name,
            "manager_name": "Manager 2",
            "email": f"owner-{uuid.uuid4().hex[:8]}@test.local",
            "password": _PASSWORD,
        },
    )

    def _slug(registration: dict) -> str:
        return client.get(
            f"/api/v1/restaurants/{registration['staff']['restaurant_id']}",
            headers={"Authorization": f"Bearer {registration['access_token']}"},
        ).json()["slug"]

    slug1 = _slug(res1.json())
    slug2 = _slug(res2.json())
    assert slug1 != slug2
    assert slug2 == f"{slug1}-2"


def test_register_rejects_duplicate_email(client):
    email = f"owner-{uuid.uuid4().hex[:8]}@test.local"
    payload = {
        "restaurant_name": "Premier Resto",
        "manager_name": "Amina",
        "email": email,
        "password": _PASSWORD,
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post(
        "/api/v1/auth/register",
        json={**payload, "restaurant_name": "Deuxième Resto"},
    )
    assert res2.status_code == 409
    assert res2.json()["detail"]["code"] == "EMAIL_EXISTS"


def test_register_rejects_short_password(client):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "restaurant_name": "Resto Faible",
            "manager_name": "Amina",
            "email": f"owner-{uuid.uuid4().hex[:8]}@test.local",
            "password": "short",
        },
    )
    assert res.status_code == 422


def test_newly_registered_manager_can_log_in(client):
    email = f"owner-{uuid.uuid4().hex[:8]}@test.local"
    client.post(
        "/api/v1/auth/register",
        json={
            "restaurant_name": "Resto Login",
            "manager_name": "Amina",
            "email": email,
            "password": _PASSWORD,
        },
    )

    res = client.post("/api/v1/auth/login", json={"email": email, "password": _PASSWORD})
    assert res.status_code == 200
    assert res.json()["staff"]["role"] == "manager"


def test_registered_manager_is_isolated_to_their_own_restaurant(client):
    res_a = client.post(
        "/api/v1/auth/register",
        json={
            "restaurant_name": "Resto Isolation A",
            "manager_name": "Manager A",
            "email": f"owner-a-{uuid.uuid4().hex[:8]}@test.local",
            "password": _PASSWORD,
        },
    )
    res_b = client.post(
        "/api/v1/auth/register",
        json={
            "restaurant_name": "Resto Isolation B",
            "manager_name": "Manager B",
            "email": f"owner-b-{uuid.uuid4().hex[:8]}@test.local",
            "password": _PASSWORD,
        },
    )
    token_a = res_a.json()["access_token"]
    restaurant_b_id = res_b.json()["staff"]["restaurant_id"]

    res = client.patch(
        f"/api/v1/restaurants/{restaurant_b_id}/cafe-mode",
        json={"enabled": True},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "FORBIDDEN"
