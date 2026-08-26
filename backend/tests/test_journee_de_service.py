"""
Borne de journée de service (Phase 19.5).

Défaut rendu visible par le plan de salle : des tables restaient rouges le
lendemain, avec « +1 h ». Les écrans de service ne doivent montrer que le
service en cours — sans jamais toucher au statut des commandes, qui restent
« perdues » pour la page de preuve.
"""
from datetime import datetime, timedelta, timezone

from app.core.dates import service_day_start
from app.core.markets import FRANCE, TUNISIA
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
    jour_de_service = service_day_start().astimezone(TUNISIA.timezone).date() - timedelta(days=1)
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
    if nuit > datetime.now(TUNISIA.timezone):
        nuit = datetime.now(TUNISIA.timezone) - timedelta(minutes=5)
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
    minuit_et_demi = datetime(2026, 8, 15, 0, 30, tzinfo=TUNISIA.timezone)

    debut = service_day_start(minuit_et_demi).astimezone(TUNISIA.timezone)

    assert (debut.day, debut.hour) == (14, 5)


def test_a_july_order_lands_in_the_correct_service_day_in_france():
    """
    Exigence explicite de MARCHE_FRANCE.md Phase F3 : « Test qui prouve
    qu'une commande du 15 juillet tombe dans la bonne journée de service ».
    23 h à Paris un 15 juillet (heure d'été, UTC+2) — après la borne de 5 h,
    doit tomber dans la journée de service du 15, pas du 14 ni décalée d'une
    heure comme l'aurait fait un décalage UTC fixe façon `TUNIS` d'avant F3.
    """
    late_evening_utc = datetime(2026, 7, 15, 21, 0, tzinfo=timezone.utc)  # 23h Paris (UTC+2)

    debut = service_day_start(late_evening_utc, market=FRANCE).astimezone(FRANCE.timezone)

    assert (debut.month, debut.day, debut.hour) == (7, 15, 5)


def test_the_service_day_boundary_shifts_with_daylight_saving_time():
    """
    Preuve que `zoneinfo` est réellement branché, pas juste un décalage fixe
    différent (ex. UTC+2 en dur, qui serait alors faux en hiver) : le même
    instant local (2 h du matin, avant la borne de 5 h) doit produire une
    borne UTC DIFFÉRENTE en été et en hiver, puisque Paris change de
    décalage entre les deux (UTC+2 l'été, UTC+1 l'hiver) — la Tunisie, elle,
    n'observe plus l'heure d'été depuis 2009 (`TUNISIA.timezone` reste à
    UTC+1 toute l'année, vérifié à part dans test_markets.py).
    """
    ete = service_day_start(datetime(2026, 7, 15, 2, 0, tzinfo=FRANCE.timezone), market=FRANCE)
    hiver = service_day_start(datetime(2026, 1, 15, 2, 0, tzinfo=FRANCE.timezone), market=FRANCE)

    assert ete.hour != hiver.hour
    assert ete.astimezone(FRANCE.timezone).hour == 5
    assert hiver.astimezone(FRANCE.timezone).hour == 5


def test_tunisia_behaviour_is_unchanged_by_the_market_parameter():
    """Critère de sortie F3 : `MARKET=tn` ne change pas de comportement.
    Les tests tournent avec `MARKET` non posé (défaut "tn") — `market=None`
    doit donc rester exactement équivalent à `market=TUNISIA` ici."""
    now = datetime(2026, 7, 15, 21, 0, tzinfo=timezone.utc)

    assert service_day_start(now) == service_day_start(now, market=TUNISIA)
