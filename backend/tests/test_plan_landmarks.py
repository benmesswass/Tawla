"""
Repères du plan de salle (Phase 18, suite) — le bar, la porte d'entrée.

Un repère n'est pas une table : rien à commander, rien à servir. Il n'existe
que pour que le serveur se repère dans la zone (« la 4 est près de
l'entrée ») — même plan, même écran, même palier (Pro+) que les tables.
"""
import pytest

from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.staff.models import StaffRole
from app.modules.tables.models import PlanLandmark
from app.modules.tenants.models import SubscriptionTier


@pytest.fixture()
def salle():
    return create_restaurant(name="Dar El Jeld")


def _poser(client, restaurant_id, staff, kind="bar", pos_x=50.0, pos_y=12.0):
    return client.post(
        f"/api/v1/tables/plan/{restaurant_id}/landmarks",
        json={"kind": kind, "pos_x": pos_x, "pos_y": pos_y},
        headers=auth_headers(staff),
    )


def test_a_manager_adds_a_landmark(client, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)

    response = _poser(client, salle.id, manager, kind="bar", pos_x=50.0, pos_y=12.0)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["kind"] == "bar"
    assert (body["pos_x"], body["pos_y"]) == (50.0, 12.0)


def test_a_landmark_defaults_to_medium_size(client, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)

    body = _poser(client, salle.id, manager).json()

    assert body["size"] == "medium"


def test_a_landmark_can_be_created_with_a_chosen_size(client, salle):
    """Un bar peut être un coin comptoir ou occuper tout un mur — le manager
    choisit la taille dès la pose, pas seulement après coup."""
    manager = create_staff(salle.id, StaffRole.MANAGER)

    response = client.post(
        f"/api/v1/tables/plan/{salle.id}/landmarks",
        json={"kind": "bar", "pos_x": 50.0, "pos_y": 12.0, "size": "large"},
        headers=auth_headers(manager),
    )

    assert response.status_code == 201, response.text
    assert response.json()["size"] == "large"


def test_a_landmark_is_placed_immediately_no_reserve(client, db_session, salle):
    """Contrairement à une table, un repère naît déjà posé : rien d'autre à
    régler qu'une position, donc pas de réserve où attendre."""
    manager = create_staff(salle.id, StaffRole.MANAGER)

    body = _poser(client, salle.id, manager, kind="entrance", pos_x=4.0, pos_y=50.0).json()

    stored = db_session.get(PlanLandmark, body["id"])
    assert (stored.pos_x, stored.pos_y) == (4.0, 50.0)


def test_a_waiter_reads_the_landmarks(client, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)
    waiter = create_staff(salle.id, StaffRole.WAITER)
    _poser(client, salle.id, manager)

    response = client.get(f"/api/v1/tables/plan/{salle.id}/landmarks", headers=auth_headers(waiter))

    assert response.status_code == 200
    assert [l["kind"] for l in response.json()] == ["bar"]


def test_a_waiter_cannot_add_a_landmark(client, salle):
    """Poser un repère est un acte de gestion, comme dessiner la salle — le
    serveur la lit, il ne la modifie pas."""
    waiter = create_staff(salle.id, StaffRole.WAITER)

    response = _poser(client, salle.id, waiter)

    assert response.status_code == 403


def test_a_manager_cannot_add_a_landmark_to_another_restaurant(client, salle):
    autre = create_restaurant(name="Le Concurrent")
    manager_autre = create_staff(autre.id, StaffRole.MANAGER)

    response = _poser(client, salle.id, manager_autre)

    assert response.status_code == 403


def test_adding_a_landmark_requires_pro_tier(client):
    """Le plan visuel est Pro+ (2026-08-18) — un repère n'a pas plus de sens
    qu'une table positionnée sans lui."""
    restaurant = create_restaurant(name="Essentiel", subscription_tier=SubscriptionTier.ESSENTIEL)
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = _poser(client, restaurant.id, manager)

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "UPGRADE_REQUIRED"


def test_a_position_outside_the_plan_is_refused(client, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)

    response = _poser(client, salle.id, manager, pos_x=140.0)

    assert response.status_code == 422


def test_moving_a_landmark_replaces_its_position(client, db_session, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)
    landmark = _poser(client, salle.id, manager).json()

    response = client.put(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}",
        json={"pos_x": 80.0, "pos_y": 20.0},
        headers=auth_headers(manager),
    )

    assert response.status_code == 200
    db_session.expire_all()
    stored = db_session.get(PlanLandmark, landmark["id"])
    assert (stored.pos_x, stored.pos_y) == (80.0, 20.0)


def test_resizing_a_landmark_replaces_its_size(client, db_session, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)
    landmark = _poser(client, salle.id, manager).json()
    assert landmark["size"] == "medium"

    response = client.put(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}",
        json={"pos_x": 80.0, "pos_y": 20.0, "size": "small"},
        headers=auth_headers(manager),
    )

    assert response.status_code == 200
    assert response.json()["size"] == "small"
    db_session.expire_all()
    assert db_session.get(PlanLandmark, landmark["id"]).size.value == "small"


def test_an_unknown_size_is_refused(client, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)

    response = client.post(
        f"/api/v1/tables/plan/{salle.id}/landmarks",
        json={"kind": "bar", "pos_x": 50.0, "pos_y": 12.0, "size": "enorme"},
        headers=auth_headers(manager),
    )

    assert response.status_code == 422


def test_a_waiter_cannot_move_a_landmark(client, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)
    waiter = create_staff(salle.id, StaffRole.WAITER)
    landmark = _poser(client, salle.id, manager).json()

    response = client.put(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}",
        json={"pos_x": 10.0, "pos_y": 10.0},
        headers=auth_headers(waiter),
    )

    assert response.status_code == 403


def test_a_manager_cannot_move_another_restaurants_landmark(client, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)
    landmark = _poser(client, salle.id, manager).json()

    autre = create_restaurant(name="Le Concurrent")
    manager_autre = create_staff(autre.id, StaffRole.MANAGER)

    response = client.put(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}",
        json={"pos_x": 10.0, "pos_y": 10.0},
        headers=auth_headers(manager_autre),
    )

    assert response.status_code == 403


def test_deleting_a_landmark_removes_it_from_the_plan(client, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)
    landmark = _poser(client, salle.id, manager, kind="entrance", pos_x=4.0, pos_y=50.0).json()

    response = client.delete(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}", headers=auth_headers(manager)
    )

    assert response.status_code == 204
    listing = client.get(f"/api/v1/tables/plan/{salle.id}/landmarks", headers=auth_headers(manager)).json()
    assert listing == []


def test_a_waiter_cannot_delete_a_landmark(client, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)
    waiter = create_staff(salle.id, StaffRole.WAITER)
    landmark = _poser(client, salle.id, manager).json()

    response = client.delete(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}", headers=auth_headers(waiter)
    )

    assert response.status_code == 403


def test_the_landmarks_of_another_restaurant_are_isolated(client, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)
    _poser(client, salle.id, manager)

    autre = create_restaurant(name="Le Concurrent")
    intrus = create_staff(autre.id, StaffRole.WAITER)

    response = client.get(f"/api/v1/tables/plan/{salle.id}/landmarks", headers=auth_headers(intrus))

    assert response.status_code == 403
