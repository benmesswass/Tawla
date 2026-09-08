"""
Repères du plan de salle (Phase 18, suite) — le bar, la porte d'entrée.

Un repère n'est pas une table : rien à commander, rien à servir. Il n'existe
que pour que le serveur se repère dans la zone (« la 4 est près de
l'entrée ») — même plan, même écran, même palier (Pro+) que les tables.
"""
import pytest

from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.staff.models import StaffRole
from app.modules.tables.models import PlanLandmark, PlanLandmarkPart
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
    assert (body["parts"][0]["pos_x"], body["parts"][0]["pos_y"]) == (50.0, 12.0)


def test_a_new_landmark_is_a_single_straight_run(client, salle):
    """On pose un comptoir droit, on le coude ensuite si la salle le demande —
    c'est le geste réel, donc un seul tronçon à la pose."""
    manager = create_staff(salle.id, StaffRole.MANAGER)

    body = _poser(client, salle.id, manager).json()

    assert len(body["parts"]) == 1
    assert (body["parts"][0]["width"], body["parts"][0]["height"]) == (12.0, 7.0)


def test_a_landmark_can_be_created_with_chosen_dimensions(client, salle):
    """Un bar peut être un coin comptoir ou occuper tout un mur — le manager
    choisit sa forme dès la pose, pas seulement après coup."""
    manager = create_staff(salle.id, StaffRole.MANAGER)

    response = client.post(
        f"/api/v1/tables/plan/{salle.id}/landmarks",
        json={"kind": "bar", "pos_x": 50.0, "pos_y": 12.0, "width": 40.0, "height": 5.0},
        headers=auth_headers(manager),
    )

    assert response.status_code == 201, response.text
    part = response.json()["parts"][0]
    assert (part["width"], part["height"]) == (40.0, 5.0)


def test_a_landmark_is_placed_immediately_no_reserve(client, db_session, salle):
    """Contrairement à une table, un repère naît déjà posé : rien d'autre à
    régler qu'une position, donc pas de réserve où attendre."""
    manager = create_staff(salle.id, StaffRole.MANAGER)

    body = _poser(client, salle.id, manager, kind="entrance", pos_x=4.0, pos_y=50.0).json()

    stored = db_session.get(PlanLandmark, body["id"])
    assert (stored.parts[0].pos_x, stored.parts[0].pos_y) == (4.0, 50.0)


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


def test_reshaping_a_landmark_replaces_its_runs(client, db_session, salle):
    """Déplacer, étirer, couder : un seul geste vu du manager, donc une seule
    écriture — la liste des tronçons remplace l'ancienne en bloc."""
    manager = create_staff(salle.id, StaffRole.MANAGER)
    landmark = _poser(client, salle.id, manager).json()

    response = client.put(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}",
        json={"parts": [{"pos_x": 80.0, "pos_y": 20.0, "width": 25.0, "height": 15.0}]},
        headers=auth_headers(manager),
    )

    assert response.status_code == 200
    part = response.json()["parts"][0]
    assert (part["pos_x"], part["pos_y"], part["width"], part["height"]) == (80.0, 20.0, 25.0, 15.0)
    db_session.expire_all()
    stored = db_session.get(PlanLandmark, landmark["id"])
    assert len(stored.parts) == 1
    assert (stored.parts[0].pos_x, stored.parts[0].width) == (80.0, 25.0)


def test_a_bar_can_be_shaped_as_an_l(client, salle):
    """Retour de Wassim (2026-09-08) : un rectangle ne dit pas un bar en L.
    Deux tronçons en équerre, et le plan dessine leur union."""
    manager = create_staff(salle.id, StaffRole.MANAGER)
    landmark = _poser(client, salle.id, manager).json()

    response = client.put(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}",
        json={
            "parts": [
                {"pos_x": 8.0, "pos_y": 8.0, "width": 36.0, "height": 6.0},
                {"pos_x": 38.0, "pos_y": 8.0, "width": 6.0, "height": 28.0},
            ]
        },
        headers=auth_headers(manager),
    )

    assert response.status_code == 200, response.text
    assert len(response.json()["parts"]) == 2


def test_a_bar_can_be_shaped_as_a_u_and_keeps_the_order_of_the_run(client, db_session, salle):
    """Trois tronçons pour un U — et ils reviennent dans l'ordre du parcours
    du comptoir, celui dans lequel le manager les a prolongés."""
    manager = create_staff(salle.id, StaffRole.MANAGER)
    landmark = _poser(client, salle.id, manager).json()

    response = client.put(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}",
        json={
            "parts": [
                {"pos_x": 8.0, "pos_y": 8.0, "width": 36.0, "height": 6.0},
                {"pos_x": 38.0, "pos_y": 8.0, "width": 6.0, "height": 28.0},
                {"pos_x": 8.0, "pos_y": 30.0, "width": 36.0, "height": 6.0},
            ]
        },
        headers=auth_headers(manager),
    )

    assert response.status_code == 200, response.text
    assert [p["pos_y"] for p in response.json()["parts"]] == [8.0, 8.0, 30.0]
    db_session.expire_all()
    stored = db_session.get(PlanLandmark, landmark["id"])
    assert [p.ordre for p in stored.parts] == [0, 1, 2]


def test_a_shape_without_any_run_is_refused(client, salle):
    """Un repère sans tronçon n'est pas un repère invisible : c'est un état
    impossible, et le retirer est une autre route."""
    manager = create_staff(salle.id, StaffRole.MANAGER)
    landmark = _poser(client, salle.id, manager).json()

    response = client.put(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}",
        json={"parts": []},
        headers=auth_headers(manager),
    )

    assert response.status_code == 422


def test_too_many_runs_are_refused(client, salle):
    """Au-delà de quatre tronçons on dessine un logiciel d'architecture, pas
    un outil de service."""
    manager = create_staff(salle.id, StaffRole.MANAGER)
    landmark = _poser(client, salle.id, manager).json()

    response = client.put(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}",
        json={
            "parts": [
                {"pos_x": 8.0 + i * 8, "pos_y": 8.0, "width": 6.0, "height": 6.0} for i in range(5)
            ]
        },
        headers=auth_headers(manager),
    )

    assert response.status_code == 422


def test_dimensions_outside_bounds_are_refused(client, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)

    for width in (0.5, 95.0):
        response = client.post(
            f"/api/v1/tables/plan/{salle.id}/landmarks",
            json={"kind": "bar", "pos_x": 50.0, "pos_y": 12.0, "width": width, "height": 7.0},
            headers=auth_headers(manager),
        )
        assert response.status_code == 422, width


def test_a_run_outside_bounds_is_refused(client, salle):
    """Les bornes valent tronçon par tronçon, pas seulement à la pose : sans
    ça un coude pouvait rattraper un bras hors du plan."""
    manager = create_staff(salle.id, StaffRole.MANAGER)
    landmark = _poser(client, salle.id, manager).json()

    response = client.put(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}",
        json={
            "parts": [
                {"pos_x": 8.0, "pos_y": 8.0, "width": 36.0, "height": 6.0},
                {"pos_x": 140.0, "pos_y": 8.0, "width": 6.0, "height": 28.0},
            ]
        },
        headers=auth_headers(manager),
    )

    assert response.status_code == 422


def test_a_waiter_cannot_reshape_a_landmark(client, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)
    waiter = create_staff(salle.id, StaffRole.WAITER)
    landmark = _poser(client, salle.id, manager).json()

    response = client.put(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}",
        json={"parts": [{"pos_x": 10.0, "pos_y": 10.0, "width": 12.0, "height": 7.0}]},
        headers=auth_headers(waiter),
    )

    assert response.status_code == 403


def test_a_manager_cannot_reshape_another_restaurants_landmark(client, salle):
    manager = create_staff(salle.id, StaffRole.MANAGER)
    landmark = _poser(client, salle.id, manager).json()

    autre = create_restaurant(name="Le Concurrent")
    manager_autre = create_staff(autre.id, StaffRole.MANAGER)

    response = client.put(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}",
        json={"parts": [{"pos_x": 10.0, "pos_y": 10.0, "width": 12.0, "height": 7.0}]},
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


def test_deleting_a_landmark_takes_its_runs_with_it(client, db_session, salle):
    """Retirer le bar retire tout le comptoir, pas seulement l'étiquette : des
    tronçons orphelins reviendraient au prochain repère créé sur cet id."""
    manager = create_staff(salle.id, StaffRole.MANAGER)
    landmark = _poser(client, salle.id, manager).json()
    client.put(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}",
        json={
            "parts": [
                {"pos_x": 8.0, "pos_y": 8.0, "width": 36.0, "height": 6.0},
                {"pos_x": 38.0, "pos_y": 8.0, "width": 6.0, "height": 28.0},
            ]
        },
        headers=auth_headers(manager),
    )

    client.delete(
        f"/api/v1/tables/plan/{salle.id}/landmarks/{landmark['id']}", headers=auth_headers(manager)
    )

    db_session.expire_all()
    restants = db_session.query(PlanLandmarkPart).filter_by(landmark_id=landmark["id"]).count()
    assert restants == 0


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
