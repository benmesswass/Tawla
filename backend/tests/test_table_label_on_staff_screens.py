"""
Le serveur doit lire le nom de la table, pas son identifiant en base.

Les écrans serveur et cuisine affichaient `Table {table_id}` : l'identifiant
technique de la ligne, pas le libellé choisi par le restaurant. Les deux
coïncident tant que les tables s'appellent « Table 1, 2, 3… » et sont créées
dans cet ordre — c'est-à-dire jamais, dès qu'un établissement a une terrasse,
un étage, ou qu'il a corrigé une table après coup.

Conséquence en salle : le client voit « Table 3 » sur son téléphone, le serveur
lit « Table 1 » sur le sien, et part au mauvais endroit avec le bon plat.
"""
from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.menu.models import MenuItem
from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table


def _restaurant_with_labelled_tables(db_session):
    """Deux tables dont le libellé ne coïncide PAS avec l'identifiant — le cas
    normal d'un vrai restaurant, et celui qui révèle le bug."""
    restaurant = create_restaurant(name="Chez Slah")
    terrasse = Table(restaurant_id=restaurant.id, label="Terrasse 2", zone="Terrasse")
    salle = Table(restaurant_id=restaurant.id, label="T7", zone="Salle")
    item = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=18.0, category="Plats")
    db_session.add_all([terrasse, salle, item])
    db_session.commit()
    for obj in (terrasse, salle, item):
        db_session.refresh(obj)
    return restaurant, terrasse, salle, item


def test_an_order_carries_the_label_of_its_table(client, db_session):
    restaurant, terrasse, _salle, item = _restaurant_with_labelled_tables(db_session)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    client.post("/api/v1/orders", json={
        "qr_token": terrasse.qr_token,
        "items": [{"menu_item_id": item.id, "quantity": 1}],
    })

    active = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/active", headers=auth_headers(waiter)
    ).json()

    assert active[0]["table_label"] == "Terrasse 2", (
        "l'écran serveur n'a que l'identifiant de la table : il affichera un "
        "numéro qui ne correspond à aucune table de la salle"
    )


def test_a_waiter_call_carries_the_label_of_its_table(client, db_session):
    restaurant, _terrasse, salle, _item = _restaurant_with_labelled_tables(db_session)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    client.post("/api/v1/waiter-calls", json={"qr_token": salle.qr_token})

    pending = client.get(
        f"/api/v1/waiter-calls/by-restaurant/{restaurant.id}/pending", headers=auth_headers(waiter)
    ).json()

    assert pending[0]["table_label"] == "T7"


def test_the_label_travels_on_the_realtime_message_too(client, db_session):
    """L'écran serveur se remplit par WebSocket en plein service, pas par
    rechargement : si le libellé ne voyage pas là, le bug survit."""
    restaurant, terrasse, _salle, item = _restaurant_with_labelled_tables(db_session)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    kitchen = create_staff(restaurant.id, StaffRole.KITCHEN)
    order = client.post("/api/v1/orders", json={
        "qr_token": terrasse.qr_token,
        "items": [{"menu_item_id": item.id, "quantity": 1}],
    }).json()

    with client.websocket_connect(
        f"/ws/kitchen/{restaurant.id}?token={auth_headers(kitchen)['Authorization'].split()[1]}"
    ) as ws:
        client.post(f"/api/v1/orders/{order['id']}/confirm", headers=auth_headers(waiter))
        client.post(f"/api/v1/orders/{order['id']}/send-to-kitchen", headers=auth_headers(waiter))
        message = ws.receive_json()

    assert message["event"] == "order.sent_to_kitchen"
    assert message["table_label"] == "Terrasse 2", (
        "la cuisine reçoit un identifiant : le ticket annoncera la mauvaise table"
    )


def test_the_client_and_the_waiter_read_the_same_table(client, db_session):
    """La seule formulation qui compte : les deux écrans doivent dire la même
    chose, sinon le plat part au mauvais endroit."""
    restaurant, terrasse, _salle, item = _restaurant_with_labelled_tables(db_session)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    client.post("/api/v1/orders", json={
        "qr_token": terrasse.qr_token,
        "items": [{"menu_item_id": item.id, "quantity": 1}],
    })

    vu_par_le_client = client.get(f"/api/v1/tables/by-token/{terrasse.qr_token}").json()["label"]
    vu_par_le_serveur = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/active", headers=auth_headers(waiter)
    ).json()[0]["table_label"]

    assert vu_par_le_client == vu_par_le_serveur
