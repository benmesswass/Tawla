"""
Borne de journée de service (Phase 19.5).

Défaut rendu visible par le plan de salle : des tables restaient rouges le
lendemain, avec « +1 h ». Les écrans de service ne doivent montrer que le
service en cours — sans jamais toucher au statut des commandes, qui restent
« perdues » pour la page de preuve.
"""
from datetime import datetime, timedelta

from app.core.dates import TUNIS, service_day_start
from app.modules.menu.models import MenuItem
from app.modules.orders.models import Order
from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table
from app.modules.waiter_calls.models import WaiterCall
from tests.conftest import auth_headers, create_restaurant, create_staff


def _setup(db_session):
    restaurant = create_restaurant(name="Chez Slah", slug="journee-de-service")
    table = Table(restaurant_id=restaurant.id, label="Table 1")
    item = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=25.0, category="Plats")
    db_session.add_all([table, item])
    db_session.commit()
    db_session.refresh(table)
    db_session.refresh(item)
    return restaurant, table, item


def _order_created_at(db_session, restaurant, table, moment) -> Order:
    order = Order(restaurant_id=restaurant.id, table_id=table.id, created_at=moment)
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


def test_une_commande_de_la_veille_disparait_de_lecran_serveur(client, db_session):
    restaurant, table, _item = _setup(db_session)
    veille = service_day_start() - timedelta(hours=2)
    _order_created_at(db_session, restaurant, table, veille)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)

    active = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/active", headers=auth_headers(waiter)
    )

    assert active.status_code == 200
    assert active.json() == []


def test_une_commande_de_la_veille_reste_une_commande_perdue(client, db_session):
    """
    On cesse de l'afficher, on ne l'efface pas : son statut ne bouge pas, donc
    elle continue de compter dans les commandes perdues — le chiffre qui porte
    l'argument de vente.
    """
    restaurant, table, _item = _setup(db_session)
    veille = service_day_start() - timedelta(hours=2)
    oubliee = _order_created_at(db_session, restaurant, table, veille)
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    # `veille` tombe avant 5h Tunis : sa journée de service est celle d'hier
    # (F-3), même si son horodatage calendaire brut est encore aujourd'hui.
    jour_de_service = service_day_start().astimezone(TUNIS).date() - timedelta(days=1)
    jour = jour_de_service.isoformat()
    preuve = client.get(
        f"/api/v1/stats/preuve/{restaurant.id}",
        params={"start": jour, "end": jour},
        headers=auth_headers(manager),
    )

    assert preuve.status_code == 200
    assert preuve.json()["current"]["lost_orders_count"] == 1
    db_session.refresh(oubliee)
    assert oubliee.status.value == "pending_confirmation"


def test_un_service_de_nuit_reste_affiche(client, db_session):
    """
    La borne est à 5 h du matin, heure de Tunis, précisément pour qu'une
    commande passée à 2 h reste celle du service en cours.
    """
    restaurant, table, _item = _setup(db_session)
    nuit = service_day_start() + timedelta(minutes=5)
    if nuit > datetime.now(TUNIS):
        nuit = datetime.now(TUNIS) - timedelta(minutes=5)
    _order_created_at(db_session, restaurant, table, nuit)
    waiter = create_staff(restaurant.id, StaffRole.WAITER)

    active = client.get(
        f"/api/v1/orders/by-restaurant/{restaurant.id}/active", headers=auth_headers(waiter)
    )

    assert len(active.json()) == 1


def test_un_appel_serveur_de_la_veille_disparait_de_lecran(client, db_session):
    """Même borne pour les appels serveur : deux écrans qui filtrent
    différemment finiraient par se contredire."""
    restaurant, table, _item = _setup(db_session)
    veille = service_day_start() - timedelta(hours=2)
    db_session.add(
        WaiterCall(restaurant_id=restaurant.id, table_id=table.id, created_at=veille)
    )
    db_session.commit()
    waiter = create_staff(restaurant.id, StaffRole.WAITER)

    pending = client.get(
        f"/api/v1/waiter-calls/by-restaurant/{restaurant.id}/pending", headers=auth_headers(waiter)
    )

    assert pending.status_code == 200
    assert pending.json() == []


def test_la_borne_ne_coupe_jamais_un_service_en_cours():
    """5 h du matin, heure de Tunis — jamais au milieu d'un service."""
    minuit_et_demi = datetime(2026, 8, 15, 0, 30, tzinfo=TUNIS)

    debut = service_day_start(minuit_et_demi).astimezone(TUNIS)

    assert (debut.day, debut.hour) == (14, 5)
