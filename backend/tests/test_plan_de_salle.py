"""
Plan de salle (Phase 18).

Le manager pose ses tables comme elles sont dans sa salle, et le serveur lit
l'état de la salle d'un coup d'œil au lieu de dérouler une liste. Une liste
grandit indéfiniment ; un plan a exactement le nombre de tables de la salle,
toujours.

Les coordonnées sont en pourcentage et jamais en pixels : le même plan se
regarde sur un téléphone de 360 px et sur l'écran du bureau.
"""
import pytest

from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table, TableShape


@pytest.fixture()
def salle(db_session):
    restaurant = create_restaurant(name="Dar El Jeld")
    tables = [
        Table(restaurant_id=restaurant.id, label="Terrasse 2", zone="Terrasse"),
        Table(restaurant_id=restaurant.id, label="T7", zone="Salle"),
    ]
    db_session.add_all(tables)
    db_session.commit()
    for t in tables:
        db_session.refresh(t)
    return restaurant, tables


def _plan(client, restaurant, staff, placements):
    return client.put(
        f"/api/v1/tables/plan/{restaurant.id}",
        json={"placements": placements},
        headers=auth_headers(staff),
    )


def test_a_manager_places_his_tables(client, db_session, salle):
    restaurant, tables = salle
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = _plan(client, restaurant, manager, [
        {"table_id": tables[0].id, "pos_x": 18.5, "pos_y": 62.0, "shape": "round"},
        {"table_id": tables[1].id, "pos_x": 74.0, "pos_y": 30.5, "shape": "rect"},
    ])

    assert response.status_code == 200, response.text
    db_session.expire_all()
    posee = db_session.get(Table, tables[0].id)
    assert (posee.pos_x, posee.pos_y) == (18.5, 62.0)
    assert db_session.get(Table, tables[1].id).shape == TableShape.RECT


def test_a_new_table_is_not_placed_yet(client, db_session, salle):
    """Elle existe, elle a son QR, mais elle n'apparaît pas sur le plan tant
    que le manager ne l'y a pas posée — plutôt qu'atterrir en (0,0)."""
    _restaurant, tables = salle
    assert tables[0].pos_x is None and tables[0].pos_y is None


def test_a_position_outside_the_plan_is_refused(client, salle):
    restaurant, tables = salle
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = _plan(client, restaurant, manager, [
        {"table_id": tables[0].id, "pos_x": 140.0, "pos_y": 12.0},
    ])

    assert response.status_code == 422


def test_the_whole_plan_is_saved_or_nothing_is(client, db_session, salle):
    """Une table étrangère glissée dans la requête ne doit pas laisser le plan
    à moitié enregistré."""
    restaurant, tables = salle
    autre = create_restaurant(name="Le Concurrent")
    table_adverse = Table(restaurant_id=autre.id, label="Chez eux")
    db_session.add(table_adverse)
    db_session.commit()
    db_session.refresh(table_adverse)
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = _plan(client, restaurant, manager, [
        {"table_id": tables[0].id, "pos_x": 10.0, "pos_y": 10.0},
        {"table_id": table_adverse.id, "pos_x": 50.0, "pos_y": 50.0},
    ])

    assert response.status_code == 404
    db_session.expire_all()
    assert db_session.get(Table, tables[0].id).pos_x is None, "le plan a été enregistré à moitié"
    assert db_session.get(Table, table_adverse.id).pos_x is None


def test_a_waiter_cannot_redraw_the_room(client, salle):
    """Dessiner la salle est un acte de gestion. Le serveur la lit, il ne la
    modifie pas — sinon un plan se réorganise tout seul en plein service."""
    restaurant, tables = salle
    waiter = create_staff(restaurant.id, StaffRole.WAITER)

    response = _plan(client, restaurant, waiter, [
        {"table_id": tables[0].id, "pos_x": 10.0, "pos_y": 10.0},
    ])

    assert response.status_code == 403


def test_a_manager_cannot_redraw_another_room(client, salle):
    restaurant, tables = salle
    autre = create_restaurant(name="Le Concurrent")
    manager_autre = create_staff(autre.id, StaffRole.MANAGER)

    response = _plan(client, restaurant, manager_autre, [
        {"table_id": tables[0].id, "pos_x": 10.0, "pos_y": 10.0},
    ])

    assert response.status_code in (403, 404)


def test_the_plan_comes_back_with_the_tables(client, salle):
    """Le serveur lit le plan par la même route que sa liste de tables : une
    seule source, donc pas de plan qui diverge de la salle réelle."""
    restaurant, tables = salle
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _plan(client, restaurant, manager, [
        {"table_id": tables[0].id, "pos_x": 25.0, "pos_y": 40.0, "shape": "square"},
    ])

    listing = client.get(
        f"/api/v1/tables/by-restaurant/{restaurant.id}", headers=auth_headers(manager)
    ).json()

    posee = next(t for t in listing if t["id"] == tables[0].id)
    assert (posee["pos_x"], posee["pos_y"]) == (25.0, 40.0)
    assert posee["shape"] == "square"
    non_posee = next(t for t in listing if t["id"] == tables[1].id)
    assert non_posee["pos_x"] is None


def test_moving_a_table_replaces_its_position(client, db_session, salle):
    restaurant, tables = salle
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _plan(client, restaurant, manager, [{"table_id": tables[0].id, "pos_x": 10.0, "pos_y": 10.0}])
    _plan(client, restaurant, manager, [{"table_id": tables[0].id, "pos_x": 80.0, "pos_y": 20.0}])

    db_session.expire_all()
    assert (db_session.get(Table, tables[0].id).pos_x, db_session.get(Table, tables[0].id).pos_y) == (80.0, 20.0)


def test_a_waiter_reads_the_plan(client, salle):
    """Il ne peut pas dessiner la salle, mais il doit pouvoir la lire — sinon
    le plan ne sert à rien à celui qui est debout dedans."""
    restaurant, tables = salle
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    _plan(client, restaurant, manager, [{"table_id": tables[0].id, "pos_x": 30.0, "pos_y": 45.0}])

    response = client.get(f"/api/v1/tables/plan/{restaurant.id}", headers=auth_headers(waiter))

    assert response.status_code == 200, response.text
    posee = next(t for t in response.json() if t["id"] == tables[0].id)
    assert (posee["pos_x"], posee["pos_y"]) == (30.0, 45.0)


def test_the_plan_never_carries_qr_tokens(client, salle):
    """Un token de QR n'a rien à faire sur un écran de service."""
    restaurant, _tables = salle
    waiter = create_staff(restaurant.id, StaffRole.WAITER)

    raw = client.get(f"/api/v1/tables/plan/{restaurant.id}", headers=auth_headers(waiter)).text

    assert "qr_token" not in raw


def test_the_plan_of_another_room_is_refused(client, salle):
    restaurant, _tables = salle
    autre = create_restaurant(name="Le Concurrent")
    intrus = create_staff(autre.id, StaffRole.WAITER)

    assert client.get(
        f"/api/v1/tables/plan/{restaurant.id}", headers=auth_headers(intrus)
    ).status_code == 403


def test_the_waiters_learn_that_a_table_went_to_the_kitchen(client, db_session, salle):
    """
    Sans cette diffusion, le plan d'un serveur montre la table libre alors
    qu'elle est occupée — et il ne le découvre qu'au prochain rechargement.
    L'événement n'était diffusé qu'au canal cuisine.
    """
    from app.modules.menu.models import MenuItem

    restaurant, tables = salle
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    item = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=20.0, category="Plats")
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    order = client.post("/api/v1/orders", json={
        "qr_token": tables[0].qr_token,
        "items": [{"menu_item_id": item.id, "quantity": 1}],
    }).json()
    client.post(f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers(waiter))

    token = auth_headers(waiter)["Authorization"].split()[1]
    with client.websocket_connect(f"/ws/staff/{restaurant.id}?token={token}") as ws:
        client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=auth_headers(waiter))
        message = ws.receive_json()

    assert message["event"] == "order.sent_to_kitchen"
    assert message["table_id"] == tables[0].id
