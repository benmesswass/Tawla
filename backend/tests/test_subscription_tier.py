import uuid

from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.tenants.models import SubscriptionTier


def test_new_restaurant_defaults_to_essentiel_tier(client):
    email = f"owner-{uuid.uuid4().hex[:8]}@test.local"
    res = client.post(
        "/api/v1/auth/register",
        json={
            "restaurant_name": "Café Palier",
            "manager_name": "Amina",
            "email": email,
            "password": "onboard1234",
        },
    )
    restaurant_id = res.json()["staff"]["restaurant_id"]
    # La fiche complète est sous JWT depuis la fermeture de la lecture par
    # identifiant : on réutilise le token que `register` vient de renvoyer.
    token = res.json()["access_token"]

    res = client.get(
        f"/api/v1/restaurants/{restaurant_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    assert res.json()["subscription_tier"] == "essentiel"


def test_existing_restaurants_are_readable_with_a_tier(client):
    restaurant = create_restaurant(
        name="Café Palier2", slug="cafe-palier2", subscription_tier=SubscriptionTier.ESSENTIEL
    )
    manager = create_staff(restaurant.id)

    res = client.get(f"/api/v1/restaurants/{restaurant.id}", headers=auth_headers(manager))
    assert res.status_code == 200
    assert res.json()["subscription_tier"] == "essentiel"
