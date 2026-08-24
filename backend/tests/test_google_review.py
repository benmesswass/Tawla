"""
Demande d'avis Google après le service (F5-A7, MARCHE_FRANCE.md) — argument
de vente central des concurrents français. Le manager colle le lien de sa
fiche Google Business Profile ; vide/absent retire le bouton côté client.
"""
from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant(client):
    restaurant = create_restaurant(name="Café Avis", slug="cafe-avis")
    headers = auth_headers(create_staff(restaurant.id))
    return restaurant, headers


def test_restaurant_starts_without_a_google_review_url(client):
    restaurant = create_restaurant(name="Resto Test", slug="resto-avis-default")
    assert restaurant.google_review_url is None


def test_manager_sets_the_google_review_url(client):
    restaurant, headers = _setup_restaurant(client)
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/google-review-url",
        json={"url": "https://g.page/r/abc123/review"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["google_review_url"] == "https://g.page/r/abc123/review"


def test_manager_can_clear_the_google_review_url(client):
    restaurant, headers = _setup_restaurant(client)
    client.patch(
        f"/api/v1/restaurants/{restaurant.id}/google-review-url",
        json={"url": "https://g.page/r/abc123/review"},
        headers=headers,
    )
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/google-review-url", json={"url": None}, headers=headers
    )
    assert res.status_code == 200
    assert res.json()["google_review_url"] is None


def test_google_review_url_rejects_a_non_http_scheme(client):
    """Même garde-fou que `MenuItem.image_url` : jamais un `javascript:`/`data:`
    stocké, même saisi par le manager lui-même."""
    restaurant, headers = _setup_restaurant(client)
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/google-review-url",
        json={"url": "javascript:alert(1)"},
        headers=headers,
    )
    assert res.status_code == 422


def test_google_review_url_requires_manager_role(client):
    restaurant, _headers = _setup_restaurant(client)
    waiter_headers = auth_headers(create_staff(restaurant.id, role=StaffRole.WAITER))
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/google-review-url",
        json={"url": "https://g.page/r/abc123/review"},
        headers=waiter_headers,
    )
    assert res.status_code == 403


def test_google_review_url_is_isolated_per_restaurant(client):
    restaurant_a, headers_a = _setup_restaurant(client)
    restaurant_b = create_restaurant(name="Autre café avis", slug="autre-cafe-avis")

    res = client.patch(
        f"/api/v1/restaurants/{restaurant_b.id}/google-review-url",
        json={"url": "https://g.page/r/abc123/review"},
        headers=headers_a,
    )
    assert res.status_code == 403


def test_google_review_url_is_visible_on_the_public_restaurant_view(client):
    """Contrairement à `konnect_wallet_id` ou `subscription_tier`, le lien
    d'avis doit être lisible du client — c'est lui qui affiche le bouton."""
    restaurant, headers = _setup_restaurant(client)
    client.patch(
        f"/api/v1/restaurants/{restaurant.id}/google-review-url",
        json={"url": "https://g.page/r/abc123/review"},
        headers=headers,
    )
    table = client.post(
        "/api/v1/tables", json={"restaurant_id": restaurant.id, "label": "Table 1"}, headers=headers
    ).json()

    res = client.get(f"/api/v1/restaurants/by-token/{table['qr_token']}")
    assert res.status_code == 200
    assert res.json()["google_review_url"] == "https://g.page/r/abc123/review"
