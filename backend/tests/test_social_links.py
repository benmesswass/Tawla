from app.modules.staff.models import StaffRole
from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup_restaurant(client):
    restaurant = create_restaurant(name="Dar Chaabane", slug="dar-chaabane-social")
    headers = auth_headers(create_staff(restaurant.id))
    return restaurant, headers


def _payload(**overrides):
    base = {
        "facebook_url": None,
        "instagram_url": None,
        "tiktok_url": None,
        "whatsapp_url": None,
        "google_review_url": None,
    }
    base.update(overrides)
    return base


def test_manager_can_set_social_links(client):
    restaurant, headers = _setup_restaurant(client)
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/social-links",
        json=_payload(
            facebook_url="https://facebook.com/darachaabane",
            instagram_url="https://instagram.com/darachaabane",
            whatsapp_url="https://wa.me/21612345678",
            google_review_url="https://g.page/r/abc/review",
        ),
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["facebook_url"] == "https://facebook.com/darachaabane"
    assert body["tiktok_url"] is None
    assert body["google_review_url"] == "https://g.page/r/abc/review"


def test_social_link_rejects_non_http_scheme(client):
    """Ces liens finissent en href brut sur le menu public
    (ReseauxSociaux.tsx) : un schéma non http(s) serait un XSS stocké
    déclenché au clic par n'importe quel client."""
    restaurant, headers = _setup_restaurant(client)
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/social-links",
        json=_payload(facebook_url="javascript:alert(1)"),
        headers=headers,
    )
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["code"] == "INVALID_SOCIAL_URL"
    assert detail["field"] == "facebook_url"


def test_social_link_rejects_url_over_300_chars(client):
    restaurant, headers = _setup_restaurant(client)
    too_long = "https://example.com/" + "a" * 290
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/social-links",
        json=_payload(google_review_url=too_long),
        headers=headers,
    )
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["code"] == "SOCIAL_URL_TOO_LONG"
    assert detail["field"] == "google_review_url"


def test_social_link_blank_string_clears_field(client):
    restaurant, headers = _setup_restaurant(client)
    client.patch(
        f"/api/v1/restaurants/{restaurant.id}/social-links",
        json=_payload(facebook_url="https://facebook.com/darachaabane"),
        headers=headers,
    )

    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/social-links",
        json=_payload(facebook_url="  "),
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["facebook_url"] is None


def test_social_links_require_manager_role(client):
    restaurant, _headers = _setup_restaurant(client)
    waiter_headers = auth_headers(create_staff(restaurant.id, role=StaffRole.WAITER))
    res = client.patch(
        f"/api/v1/restaurants/{restaurant.id}/social-links",
        json=_payload(),
        headers=waiter_headers,
    )
    assert res.status_code == 403


def test_social_links_isolated_per_restaurant(client):
    restaurant_a, headers_a = _setup_restaurant(client)
    restaurant_b = create_restaurant(name="Autre resto", slug="autre-resto-social")

    res = client.patch(
        f"/api/v1/restaurants/{restaurant_b.id}/social-links",
        json=_payload(facebook_url="https://facebook.com/autre"),
        headers=headers_a,
    )
    assert res.status_code == 403
