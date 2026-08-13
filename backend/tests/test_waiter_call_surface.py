"""
Surface publique de l'appel serveur (suite de la Phase 12.2).

`POST /api/v1/waiter-calls` prenait `restaurant_id` et `table_id` en entiers
bruts, sans authentification et sans `qr_token`. Deux boucles suffisaient donc,
depuis n'importe où, pour faire sonner en continu les écrans serveur de tous
les établissements — sans jamais entrer dans un restaurant.

C'est exactement le scénario que la revue d'investissement redoute (« un
incident en pleine soirée fait résilier »), et le motif que la Phase 12.2 avait
retiré de la création de commande sans le retirer ici.
"""
from tests.conftest import create_restaurant

from app.modules.tables.models import Table


def _table(db_session, restaurant_id: int, label: str = "Table 1") -> Table:
    table = Table(restaurant_id=restaurant_id, label=label)
    db_session.add(table)
    db_session.commit()
    db_session.refresh(table)
    return table


def test_a_waiter_cannot_be_called_by_guessing_ids(client, db_session):
    """Le test du constat : sans le QR de la table, aucune sonnerie."""
    restaurant = create_restaurant(name="Chez Slah")
    table = _table(db_session, restaurant.id)

    response = client.post(
        "/api/v1/waiter-calls",
        json={"restaurant_id": restaurant.id, "table_id": table.id},
    )

    assert response.status_code == 422, (
        "l'appel serveur accepte encore des identifiants devinables — "
        "n'importe qui peut faire sonner la salle à distance"
    )


def test_the_qr_token_of_the_table_calls_its_waiter(client, db_session):
    restaurant = create_restaurant(name="Chez Slah")
    table = _table(db_session, restaurant.id)

    response = client.post("/api/v1/waiter-calls", json={"qr_token": table.qr_token})

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["table_id"] == table.id
    assert body["restaurant_id"] == restaurant.id


def test_an_unknown_token_answers_404(client):
    response = client.post("/api/v1/waiter-calls", json={"qr_token": "token-inexistant"})
    assert response.status_code == 404


def test_the_token_of_one_table_never_rings_for_another(client, db_session):
    """Le restaurant est déduit de la table, jamais reçu du client : un client
    ne peut pas rattacher son appel à un autre établissement."""
    restaurant = create_restaurant(name="Chez Slah")
    autre = create_restaurant(name="Le Concurrent")
    table = _table(db_session, restaurant.id)
    _table(db_session, autre.id, label="Table adverse")

    body = client.post("/api/v1/waiter-calls", json={"qr_token": table.qr_token}).json()

    assert body["restaurant_id"] == restaurant.id
    assert body["restaurant_id"] != autre.id


def test_a_single_table_cannot_ring_the_room_without_end(client, db_session):
    """Le QR est physiquement sur la table, donc un client attablé peut quand
    même insister. Le limiteur borne la nuisance sans gêner un usage normal —
    on appelle le serveur quelques fois par repas, pas vingt."""
    restaurant = create_restaurant(name="Chez Slah")
    table = _table(db_session, restaurant.id)

    codes = [
        client.post("/api/v1/waiter-calls", json={"qr_token": table.qr_token}).status_code
        for _ in range(25)
    ]

    assert 429 in codes, "aucune limite : une table peut faire sonner la salle en continu"
    assert codes[0] == 201, "le premier appel doit passer"
