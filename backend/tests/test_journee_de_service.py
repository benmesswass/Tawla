"""
Borne de journée de service (Phase 19.5).

Défaut rendu visible par le plan de salle : des tables restaient rouges le
lendemain, avec « +1 h ». Les écrans de service ne doivent montrer que le
service en cours — sans jamais toucher au statut des commandes, qui restent
« perdues » pour la page de preuve.
"""
from datetime import date as date_type
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.dates import service_day_bounds, service_day_start
from app.modules.menu.models import MenuItem
from app.modules.orders.models import Order
from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table
from app.modules.waiter_calls.models import WaiterCall
from tests.conftest import auth_headers, create_restaurant, create_staff

# Marché par défaut des tests (MARKET non posé dans l'environnement de test) —
# voir app/core/markets.py. Utilisé tel quel plutôt qu'importé depuis
# current_market() : ces tests vérifient le comportement TUNISIEN par défaut,
# pas "le marché courant, quel qu'il soit".
TUNIS = ZoneInfo("Africa/Tunis")


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


def test_tunisie_reste_a_lheure_ete_comme_hiver():
    """
    Non-régression F3 (MARCHE_FRANCE.md) : le passage de `TUNIS`, décalage
    fixe UTC+1, à `ZoneInfo("Africa/Tunis")` ne doit RIEN changer pour la
    Tunisie — elle n'applique plus l'heure d'été depuis 2009. Vérifié aux deux
    saisons plutôt que supposé.
    """
    hiver = datetime(2026, 1, 15, 4, 30, tzinfo=TUNIS)  # 4h30 locale, avant la borne
    ete = datetime(2026, 7, 15, 4, 30, tzinfo=TUNIS)

    assert service_day_start(hiver, tz=TUNIS).astimezone(TUNIS).hour == 5
    assert service_day_start(hiver, tz=TUNIS).astimezone(TUNIS).day == 14
    assert service_day_start(ete, tz=TUNIS).astimezone(TUNIS).hour == 5
    assert service_day_start(ete, tz=TUNIS).astimezone(TUNIS).day == 14
    # Le décalage à UTC reste +1h en toute saison — c'était tout l'argument de
    # l'ancien commentaire ("la Tunisie n'applique plus l'heure d'été").
    assert hiver.utcoffset() == timedelta(hours=1)
    assert ete.utcoffset() == timedelta(hours=1)


def test_france_applique_lheure_dete_contrairement_a_la_tunisie():
    """
    F3 : un décalage fixe comme l'ancien `TUNIS` serait FAUX pour la France 7
    mois par an (MARCHE_FRANCE.md §3.3) — c'est le bug que ce test attrape.
    `service_day_start(tz=...)` doit suivre l'heure d'été, pas un offset figé.
    """
    paris = ZoneInfo("Europe/Paris")
    hiver = datetime(2026, 1, 15, 4, 30, tzinfo=paris)  # CET, UTC+1
    ete = datetime(2026, 7, 15, 4, 30, tzinfo=paris)  # CEST, UTC+2

    assert hiver.utcoffset() == timedelta(hours=1)
    assert ete.utcoffset() == timedelta(hours=2)

    debut_hiver = service_day_start(hiver, tz=paris).astimezone(paris)
    debut_ete = service_day_start(ete, tz=paris).astimezone(paris)

    # Dans les deux saisons, la borne locale reste 5h — c'est la conversion
    # UTC sous-jacente qui doit bouger d'une heure entre les deux, pas la
    # lecture locale que voit l'écran de service.
    assert (debut_hiver.day, debut_hiver.hour) == (14, 5)
    assert (debut_ete.day, debut_ete.hour) == (14, 5)
    debut_hiver_utc = service_day_start(hiver, tz=paris)
    debut_ete_utc = service_day_start(ete, tz=paris)
    assert debut_hiver_utc.hour == 4  # 5h CET = 4h UTC
    assert debut_ete_utc.hour == 3  # 5h CEST = 3h UTC


def test_service_day_bounds_suit_le_marche_passe_en_parametre():
    """`service_day_bounds` doit relayer `tz` à `service_day_start` sans le
    perdre — sinon la borne redevient tunisienne par défaut même pour la
    France, exactement le bug que ce module corrige."""
    paris = ZoneInfo("Europe/Paris")

    debut, fin = service_day_bounds(date_type(2026, 7, 15), tz=paris)

    assert (fin - debut) == timedelta(days=1)
    assert debut.astimezone(paris).hour == 5
