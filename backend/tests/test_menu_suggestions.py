"""
Vente incitative « avec ce plat » (Phase 14.1).

C'est la seule fonctionnalité du produit qui produit un chiffre défendable en
rendez-vous commercial. Les tests portent donc autant sur la mesure de l'effet
que sur la mécanique : un effet mal attribué ne vaut rien.
"""
from datetime import datetime, timedelta, timezone

from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.menu.models import MenuItem
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table


def _setup(db_session, slug: str):
    restaurant = create_restaurant(name="Chez Slah", slug=slug)
    table = Table(restaurant_id=restaurant.id, label="Table 1")
    plat = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=24.0, category="Plats")
    boisson = MenuItem(restaurant_id=restaurant.id, name="Thé", price=3.0, category="Boissons")
    dessert = MenuItem(restaurant_id=restaurant.id, name="Baklawa", price=5.0, category="Desserts")
    db_session.add_all([table, plat, boisson, dessert])
    db_session.commit()
    for obj in (table, plat, boisson, dessert):
        db_session.refresh(obj)
    return restaurant, table, plat, boisson, dessert


def _set(client, manager, item_id: int, suggested_ids: list[int]):
    return client.put(
        f"/api/v1/menu-items/{item_id}/suggestions",
        json={"suggested_item_ids": suggested_ids},
        headers=auth_headers(manager),
    )


# --- Gestion par le manager ------------------------------------------------


def test_manager_sets_and_replaces_suggestions(client, db_session):
    restaurant, _table, plat, boisson, dessert = _setup(db_session, "sugg-set")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = _set(client, manager, plat.id, [boisson.id, dessert.id])
    assert response.status_code == 200
    assert [i["name"] for i in response.json()["suggested_items"]] == ["Thé", "Baklawa"]

    # Remplacement en bloc : l'appel est rejouable sans effet de bord.
    response = _set(client, manager, plat.id, [dessert.id])
    assert [i["name"] for i in response.json()["suggested_items"]] == ["Baklawa"]

    listed = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}/suggestions").json()
    assert listed == {str(plat.id): [dessert.id]}


def test_empty_list_removes_all_suggestions(client, db_session):
    restaurant, _table, plat, boisson, _dessert = _setup(db_session, "sugg-vide")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _set(client, manager, plat.id, [boisson.id])

    assert _set(client, manager, plat.id, []).status_code == 200
    assert client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}/suggestions").json() == {}


def test_a_dish_cannot_suggest_itself(client, db_session):
    restaurant, _table, plat, _boisson, _dessert = _setup(db_session, "sugg-soi")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = _set(client, manager, plat.id, [plat.id])
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "SELF_SUGGESTION"


def test_more_than_three_suggestions_is_refused(client, db_session):
    """Au-delà de trois, la proposition devient une deuxième carte et le client
    la referme."""
    restaurant, _table, plat, boisson, dessert = _setup(db_session, "sugg-trop")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    extra = MenuItem(restaurant_id=restaurant.id, name="Café", price=2.0, category="Boissons")
    other = MenuItem(restaurant_id=restaurant.id, name="Eau", price=1.5, category="Boissons")
    db_session.add_all([extra, other])
    db_session.commit()
    db_session.refresh(extra)
    db_session.refresh(other)

    response = _set(client, manager, plat.id, [boisson.id, dessert.id, extra.id, other.id])
    assert response.status_code == 422


def test_duplicates_are_collapsed_not_rejected(client, db_session):
    restaurant, _table, plat, boisson, _dessert = _setup(db_session, "sugg-doublon")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = _set(client, manager, plat.id, [boisson.id, boisson.id])
    assert response.status_code == 200
    assert len(response.json()["suggested_items"]) == 1


def test_cannot_suggest_an_item_of_another_restaurant(client, db_session):
    restaurant, _table, plat, _boisson, _dessert = _setup(db_session, "sugg-iso-a")
    other, _t, other_plat, _b, _d = _setup(db_session, "sugg-iso-b")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = _set(client, manager, plat.id, [other_plat.id])
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ITEM_NOT_FOUND"

    # Ni toucher au plat du voisin.
    assert _set(client, manager, other_plat.id, []).status_code == 404


def test_setting_suggestions_is_manager_only(client, db_session):
    restaurant, _table, plat, boisson, _dessert = _setup(db_session, "sugg-role")
    waiter = create_staff(restaurant.id, StaffRole.WAITER)

    assert _set(client, waiter, plat.id, [boisson.id]).status_code == 403
    assert client.put(
        f"/api/v1/menu-items/{plat.id}/suggestions", json={"suggested_item_ids": [boisson.id]}
    ).status_code == 401


# --- Lecture par le client -------------------------------------------------


def test_unavailable_suggestions_are_hidden_from_the_client(client, db_session):
    """Proposer un plat en rupture est pire que ne rien proposer."""
    restaurant, _table, plat, boisson, dessert = _setup(db_session, "sugg-rupture")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _set(client, manager, plat.id, [boisson.id, dessert.id])

    client.patch(
        f"/api/v1/menu-items/{boisson.id}/availability",
        json={"is_available": False},
        headers=auth_headers(manager),
    )

    listed = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}/suggestions").json()
    assert listed == {str(plat.id): [dessert.id]}


def test_suggestions_are_scoped_to_the_restaurant(client, db_session):
    restaurant, _t, plat, boisson, _d = _setup(db_session, "sugg-scope-a")
    other, _t2, other_plat, other_boisson, _d2 = _setup(db_session, "sugg-scope-b")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    other_manager = create_staff(other.id, StaffRole.MANAGER)
    _set(client, manager, plat.id, [boisson.id])
    _set(client, other_manager, other_plat.id, [other_boisson.id])

    listed = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}/suggestions").json()
    assert listed == {str(plat.id): [boisson.id]}


# --- Mesure de l'effet -----------------------------------------------------


def _order(db_session, restaurant, table, lines, *, days_ago: float = 1):
    order = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        status=OrderStatus.SERVED,
        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    for item, quantity, from_suggestion in lines:
        order.items.append(
            OrderItem(
                menu_item_id=item.id,
                menu_item_name=item.name,
                unit_price=item.price,
                quantity=quantity,
                from_suggestion=from_suggestion,
            )
        )
    db_session.add(order)
    db_session.commit()
    return order


def test_order_records_which_lines_came_from_a_suggestion(client, db_session):
    restaurant, table, plat, boisson, _dessert = _setup(db_session, "sugg-flag")

    created = client.post("/api/v1/orders", json={
        "qr_token": table.qr_token,
        "items": [
            {"menu_item_id": plat.id, "quantity": 1},
            {"menu_item_id": boisson.id, "quantity": 1, "from_suggestion": True},
        ],
    })
    assert created.status_code == 201
    lines = {i["menu_item_name"]: i["from_suggestion"] for i in created.json()["items"]}
    assert lines == {"Couscous": False, "Thé": True}


def test_proof_page_separates_baskets_with_and_without_suggestion(client, db_session):
    """Le chiffre qui devient l'argument commercial : sans cette séparation, on
    ne saurait pas si un panier plus élevé vient des suggestions ou d'une table
    plus nombreuse."""
    restaurant, table, plat, boisson, _dessert = _setup(db_session, "sugg-mesure")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    # Deux commandes sans suggestion : 24 DT chacune.
    _order(db_session, restaurant, table, [(plat, 1, False)])
    _order(db_session, restaurant, table, [(plat, 1, False)])
    # Deux commandes avec une boisson acceptée depuis la suggestion : 27 DT.
    _order(db_session, restaurant, table, [(plat, 1, False), (boisson, 1, True)])
    _order(db_session, restaurant, table, [(plat, 1, False), (boisson, 1, True)])

    current = client.get(
        f"/api/v1/stats/preuve/{restaurant.id}", headers=auth_headers(manager)
    ).json()["current"]

    assert current["orders_with_suggestion_count"] == 2
    assert current["avg_basket_without_suggestion"] == 24.0
    assert current["avg_basket_with_suggestion"] == 27.0
    assert current["avg_basket_amount"] == 25.5


def test_cancelled_orders_are_excluded_from_the_uplift_measure(client, db_session):
    restaurant, table, plat, boisson, _dessert = _setup(db_session, "sugg-annulee")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    _order(db_session, restaurant, table, [(plat, 1, False)])
    cancelled = _order(db_session, restaurant, table, [(plat, 10, False), (boisson, 5, True)])
    cancelled.status = OrderStatus.CANCELLED
    db_session.commit()

    current = client.get(
        f"/api/v1/stats/preuve/{restaurant.id}", headers=auth_headers(manager)
    ).json()["current"]
    assert current["orders_with_suggestion_count"] == 0
    assert current["avg_basket_with_suggestion"] is None
    assert current["avg_basket_without_suggestion"] == 24.0


def test_no_suggestion_accepted_yields_null_not_zero(client, db_session):
    """« Aucune donnée » et « 0 dinar » ne veulent pas dire la même chose."""
    restaurant, table, plat, _boisson, _dessert = _setup(db_session, "sugg-aucune")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _order(db_session, restaurant, table, [(plat, 1, False)])

    current = client.get(
        f"/api/v1/stats/preuve/{restaurant.id}", headers=auth_headers(manager)
    ).json()["current"]
    assert current["orders_with_suggestion_count"] == 0
    assert current["avg_basket_with_suggestion"] is None
