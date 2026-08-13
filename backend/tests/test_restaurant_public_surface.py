"""
Surface publique de `restaurants` (suite de la Phase 12.2).

`GET /api/v1/restaurants/{restaurant_id}` était public et prenait un
identifiant incrémental : en parcourant 1, 2, 3… n'importe qui obtenait la
liste des établissements clients de Tawla, avec leur formule d'abonnement.
C'est la liste des clients de Wassim, servie à un concurrent.

La règle du projet (CLAUDE.md) est pourtant explicite : une route client est
publique par design, mais **jamais non liée** — elle exige le `qr_token` de la
table ou le `public_token` de la commande. Cette route-ci y avait échappé parce
que la page client en a réellement besoin.
"""
from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table

COMMERCIAL_FIELDS = ("subscription_tier", "slug", "created_at")


def _table(db_session, restaurant_id: int) -> Table:
    table = Table(restaurant_id=restaurant_id, label="Table 1")
    db_session.add(table)
    db_session.commit()
    db_session.refresh(table)
    return table


def test_a_restaurant_cannot_be_read_by_walking_ids(client, db_session):
    """Le test du constat : énumérer les identifiants ne doit rien donner."""
    restaurant = create_restaurant(name="Chez Slah")

    response = client.get(f"/api/v1/restaurants/{restaurant.id}")

    assert response.status_code in (401, 403), (
        "la fiche d'un établissement est lisible sans authentification — "
        "toute la clientèle de Tawla s'énumère en incrémentant l'identifiant"
    )


def test_the_qr_token_opens_the_restaurant_of_that_table(client, db_session):
    restaurant = create_restaurant(name="Chez Slah")
    table = _table(db_session, restaurant.id)

    response = client.get(f"/api/v1/restaurants/by-token/{table.qr_token}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Chez Slah"
    assert body["id"] == restaurant.id


def test_the_public_view_carries_no_commercial_data(client, db_session):
    """Le client attablé a besoin du nom et des réglages de service. Pas de la
    formule d'abonnement de l'établissement, qui ne le regarde pas."""
    restaurant = create_restaurant(name="Chez Slah")
    table = _table(db_session, restaurant.id)

    body = client.get(f"/api/v1/restaurants/by-token/{table.qr_token}").json()

    for field in COMMERCIAL_FIELDS:
        assert field not in body, f"`{field}` exposé sur la route publique"
    # Ce dont la page client se sert réellement.
    for field in ("id", "name", "ramadan_mode_enabled", "iftar_time", "cafe_mode_enabled"):
        assert field in body, f"`{field}` manquant — la page client en a besoin"


def test_an_unknown_token_answers_404_and_not_403(client):
    """Un 403 confirmerait qu'un établissement existe derrière ce token."""
    response = client.get("/api/v1/restaurants/by-token/token-qui-nexiste-pas")
    assert response.status_code == 404


def test_staff_reads_its_own_restaurant(client, db_session):
    """L'écran cuisine et le dashboard sont authentifiés : ils gardent l'accès
    à la fiche complète de leur propre établissement."""
    restaurant = create_restaurant(name="Chez Slah")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = client.get(f"/api/v1/restaurants/{restaurant.id}", headers=auth_headers(manager))

    assert response.status_code == 200, response.text
    assert response.json()["subscription_tier"] is not None


def test_staff_cannot_read_another_restaurant(client, db_session):
    restaurant = create_restaurant(name="Chez Slah")
    autre = create_restaurant(name="Le Concurrent")
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    response = client.get(f"/api/v1/restaurants/{autre.id}", headers=auth_headers(manager))

    assert response.status_code == 404
