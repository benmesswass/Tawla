from app.core.rate_limit import _hits


def test_login_blocked_after_threshold(client):
    _hits.clear()
    try:
        payload = {"email": "ratelimit@test.local", "password": "whatever123"}
        for _ in range(20):
            res = client.post("/api/v1/auth/login", json=payload)
            assert res.status_code == 401  # unknown email, but not yet rate-limited

        res = client.post("/api/v1/auth/login", json=payload)
        assert res.status_code == 429
        assert res.json()["detail"]["code"] == "RATE_LIMITED"
    finally:
        _hits.clear()


def test_login_and_register_are_limited_independently(client):
    _hits.clear()
    try:
        for _ in range(20):
            client.post("/api/v1/auth/login", json={"email": "x@test.local", "password": "x"})

        res = client.post(
            "/api/v1/auth/register",
            json={
                "restaurant_name": "Rate Limit Café",
                "manager_name": "Manager",
                "email": "owner@ratelimit.test",
                "password": "secret1234",
            },
        )
        assert res.status_code == 201
    finally:
        _hits.clear()
