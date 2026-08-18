"""
Surface publique de `menu-items` (S-1, audit du 2026-08-18).

`GET /api/v1/menu-items/by-restaurant/{id}` et `/suggestions` étaient publics
et prenaient un identifiant incrémental : en parcourant 1, 2, 3… n'importe qui
lisait la carte et les prix de n'importe quel établissement. Même défaut, même
correctif que `restaurants` (voir `test_restaurant_public_surface.py`) — la
route publique passe par le `qr_token` de la table, la route par
`restaurant_id` devient réservée au staff de cet établissement.
"""
from tests.conftest import auth_headers, create_restaurant, create_staff
from app.modules.menu.models import MenuItem, MenuSuggestion
from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table


def _setup(db_session, slug: str):
    restaurant = create_restaurant(name="Chez Slah", slug=slug)
    table = Table(restaurant_id=restaurant.id, label="Table 1")
    item = MenuItem(restaurant_id=restaurant.id, name="Couscous", category="Plats", price=20.0)
    other_item = MenuItem(restaurant_id=restaurant.id, name="Thé", category="Boissons", price=3.0)
    db_session.add_all([table, item, other_item])
    db_session.commit()
    db_session.refresh(table)
    db_session.refresh(item)
    db_session.refresh(other_item)
    db_session.add(MenuSuggestion(restaurant_id=restaurant.id, menu_item_id=item.id, suggested_item_id=other_item.id))
    db_session.commit()
    return restaurant, table, item, other_item


def test_menu_cannot_be_read_by_walking_restaurant_ids(client, db_session):
    """Le constat : lire la carte sans compte, par identifiant incrémental,
    ne doit plus rien donner."""
    restaurant, _table, _item, _other = _setup(db_session, "menu-surface-walk")

    response = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}")

    assert response.status_code in (401, 403), (
        "la carte et les prix d'un établissement se lisent sans authentification — "
        "toute la carte de Tawla s'énumère en incrémentant l'identifiant"
    )


def test_suggestions_cannot_be_read_by_walking_restaurant_ids(client, db_session):
    restaurant, _table, _item, _other = _setup(db_session, "menu-surface-sugg-walk")

    response = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}/suggestions")

    assert response.status_code in (401, 403)


def test_the_qr_token_opens_the_menu_of_that_table(client, db_session):
    _restaurant, table, item, other_item = _setup(db_session, "menu-surface-token")

    response = client.get(f"/api/v1/menu-items/by-token/{table.qr_token}")

    assert response.status_code == 200, response.text
    names = {row["name"] for row in response.json()}
    assert names == {"Couscous", "Thé"}


def test_the_qr_token_opens_the_suggestions_of_that_table(client, db_session):
    _restaurant, table, item, other_item = _setup(db_session, "menu-surface-sugg-token")

    response = client.get(f"/api/v1/menu-items/by-token/{table.qr_token}/suggestions")

    assert response.status_code == 200, response.text
    assert response.json() == {str(item.id): [other_item.id]}


def test_an_unknown_token_answers_404_and_not_403_for_the_menu(client):
    """Un 403 confirmerait qu'une table existe derrière ce token."""
    response = client.get("/api/v1/menu-items/by-token/token-qui-nexiste-pas")
    assert response.status_code == 404


def test_staff_still_reads_its_own_menu_by_restaurant_id(client, db_session):
    """Contre-épreuve : le dashboard manager garde son accès, authentifié."""
    restaurant, _table, _item, _other = _setup(db_session, "menu-surface-staff")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = client.get(f"/api/v1/menu-items/by-restaurant/{restaurant.id}", headers=auth_headers(manager))

    assert response.status_code == 200, response.text
    assert {row["name"] for row in response.json()} == {"Couscous", "Thé"}


def test_staff_cannot_read_another_restaurants_menu(client, db_session):
    restaurant, _table, _item, _other = _setup(db_session, "menu-surface-staff-a")
    autre, _table_b, _item_b, _other_b = _setup(db_session, "menu-surface-staff-b")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = client.get(f"/api/v1/menu-items/by-restaurant/{autre.id}", headers=auth_headers(manager))

    assert response.status_code == 403
