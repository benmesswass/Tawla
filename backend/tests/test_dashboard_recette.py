"""
Le premier écran du patron (Phase 17.1).

Le tableau de bord affichait les temps par étape, la performance par serveur,
les plats les plus vendus — jamais « voilà ce que tu as fait aujourd'hui ».
C'est pourtant le seul chiffre qu'un restaurateur cherche tous les soirs. Sans
lui le tableau de bord est une curiosité qu'on ouvre quand on y pense ; avec
lui c'est une habitude quotidienne, et c'est cette habitude qui empêche une
résiliation au troisième mois.

Le temps d'attente moyen est posé juste à côté (2026-08-28, ex-« commandes
perdues » — voir CONTEXT.md) : c'est ainsi que le patron voit **en passant**,
pendant qu'il regarde sa recette, si le service tourne rond aujourd'hui. Les
commandes annulées, elles, restent mesurées et partagées avec la page de
preuve, mais ne sont plus le chiffre de tête.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from tests.conftest import auth_headers, create_restaurant, create_staff

from app.modules.menu.models import MenuItem
from app.modules.orders.models import Order, OrderItem, OrderStatus, PaymentStatus
from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table


@pytest.fixture()
def resto(db_session):
    restaurant = create_restaurant(name="Chez Slah")
    table = Table(restaurant_id=restaurant.id, label="Terrasse 2")
    item = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=20.0, category="Plats")
    db_session.add_all([table, item])
    db_session.commit()
    db_session.refresh(table)
    db_session.refresh(item)
    return restaurant, table, item


def _order(
    db_session,
    restaurant,
    table,
    item,
    amount: float,
    status: OrderStatus,
    minutes_ago: int = 1,
    payment_status: PaymentStatus = PaymentStatus.PAID,
):
    """Commande posée directement en base : ces tests portent sur le calcul,
    pas sur le parcours (couvert ailleurs).

    `payment_status` vaut PAID par défaut : depuis le retour du premier
    service, seule une commande réglée entre dans la recette, donc c'est l'état
    à donner à toute commande censée compter."""
    order = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        status=status,
        payment_status=payment_status,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )
    order.items.append(
        OrderItem(menu_item_id=item.id, menu_item_name="Couscous", unit_price=amount, quantity=1)
    )
    db_session.add(order)
    db_session.commit()
    return order


def _dashboard(client, restaurant, staff) -> dict:
    response = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=auth_headers(staff))
    assert response.status_code == 200, response.text
    return response.json()


def test_the_dashboard_shows_todays_takings(client, db_session, resto):
    restaurant, table, item = resto
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _order(db_session, restaurant, table, item, 20.0, OrderStatus.SERVED)
    _order(db_session, restaurant, table, item, 32.5, OrderStatus.READY)

    body = _dashboard(client, restaurant, manager)

    assert body["revenue_today"] == pytest.approx(52.5), (
        "le patron ne voit nulle part ce qu'il a fait aujourd'hui"
    )


def test_a_cancelled_order_is_not_counted_as_takings(client, db_session, resto):
    restaurant, table, item = resto
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _order(db_session, restaurant, table, item, 20.0, OrderStatus.SERVED)
    _order(db_session, restaurant, table, item, 99.0, OrderStatus.CANCELLED)

    assert _dashboard(client, restaurant, manager)["revenue_today"] == pytest.approx(20.0)


def test_une_commande_servie_mais_pas_encore_reglee_ne_compte_pas(client, db_session, resto):
    """
    Retour du premier service : la recette additionnait tout ce qui n'était pas
    annulé, donc des commandes que personne n'avait payées. Le patron lisait
    chaque soir un chiffre plus haut que sa caisse — et c'est ce chiffre-là qui
    porte l'argument de vente.
    """
    restaurant, table, item = resto
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _order(db_session, restaurant, table, item, 20.0, OrderStatus.SERVED)
    _order(db_session, restaurant, table, item, 75.0, OrderStatus.SERVED, payment_status=PaymentStatus.UNPAID)
    # Cash demandé par le client mais pas encore encaissé par le serveur :
    # l'argent n'est pas dans la caisse, il n'a rien à faire dans la recette.
    _order(db_session, restaurant, table, item, 40.0, OrderStatus.SERVED, payment_status=PaymentStatus.PENDING)

    assert _dashboard(client, restaurant, manager)["revenue_today"] == pytest.approx(20.0)


def test_le_cash_confirme_par_le_serveur_entre_dans_la_recette(client, db_session, resto):
    """L'autre moitié : une fois le serveur ayant confirmé l'encaissement, la
    commande compte — sinon le correctif ci-dessus rendrait la recette muette
    dans un restaurant qui encaisse surtout en espèces."""
    restaurant, table, item = resto
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _order(db_session, restaurant, table, item, 33.0, OrderStatus.SERVED, payment_status=PaymentStatus.PAID)

    assert _dashboard(client, restaurant, manager)["revenue_today"] == pytest.approx(33.0)


def test_the_dashboard_shows_todays_cancelled_orders(client, db_session, resto):
    """Seule une annulation compte — une commande encore en attente, même
    ancienne, peut toujours être prise en charge (décision du 2026-08-28)."""
    restaurant, table, item = resto
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _order(db_session, restaurant, table, item, 30.0, OrderStatus.CANCELLED)
    # Ancienne ou récente, une commande en attente n'est pas perdue : elle
    # attend encore son serveur.
    _order(db_session, restaurant, table, item, 25.0, OrderStatus.PENDING_CONFIRMATION, minutes_ago=45)
    _order(db_session, restaurant, table, item, 18.0, OrderStatus.PENDING_CONFIRMATION, minutes_ago=1)

    assert _dashboard(client, restaurant, manager)["cancelled_orders_today"] == 1


def test_takings_and_cancelled_orders_match_the_proof_page(client, db_session, resto):
    """
    Les deux écrans doivent dire la même chose du même jour. S'ils divergent,
    le patron ne croit plus ni l'un ni l'autre — et c'est sur ces chiffres que
    repose toute la vente.
    """
    restaurant, table, item = resto
    manager = create_staff(restaurant.id, StaffRole.MANAGER)
    _order(db_session, restaurant, table, item, 20.0, OrderStatus.SERVED)
    _order(db_session, restaurant, table, item, 30.0, OrderStatus.READY)
    # Une commande annulée ou jamais prise en charge n'est pas réglée : c'est
    # l'état réel de ces deux-là en service.
    _order(
        db_session, restaurant, table, item, 40.0, OrderStatus.CANCELLED,
        payment_status=PaymentStatus.UNPAID,
    )
    _order(
        db_session, restaurant, table, item, 25.0, OrderStatus.PENDING_CONFIRMATION,
        minutes_ago=45, payment_status=PaymentStatus.UNPAID,
    )

    dashboard = _dashboard(client, restaurant, manager)
    today = date.today().isoformat()
    proof = client.get(
        f"/api/v1/stats/preuve/{restaurant.id}?start={today}&end={today}",
        headers=auth_headers(manager),
    ).json()["current"]

    assert dashboard["cancelled_orders_today"] == proof["cancelled_orders_count"]
    # La recette est la somme des paniers réglés, dont la page de preuve tire
    # sa moyenne : les deux écrans partagent la même définition.
    regles = (
        db_session.query(Order)
        .filter(Order.restaurant_id == restaurant.id, Order.payment_status == PaymentStatus.PAID)
        .count()
    )
    assert dashboard["revenue_today"] == pytest.approx(proof["avg_basket_amount"] * regles)


def test_a_quiet_day_shows_zero_and_not_an_empty_screen(client, db_session, resto):
    """Zéro est une information ; une case vide est un bug aux yeux du patron."""
    restaurant, _table, _item = resto
    manager = create_staff(restaurant.id, StaffRole.MANAGER)

    body = _dashboard(client, restaurant, manager)

    assert body["revenue_today"] == 0
    assert body["cancelled_orders_today"] == 0


def test_the_takings_of_another_restaurant_are_never_visible(client, db_session, resto):
    restaurant, table, item = resto
    autre = create_restaurant(name="Le Concurrent")
    manager_autre = create_staff(autre.id, StaffRole.MANAGER)
    _order(db_session, restaurant, table, item, 500.0, OrderStatus.SERVED)

    response = client.get(
        f"/api/v1/stats/dashboard/{restaurant.id}", headers=auth_headers(manager_autre)
    )

    assert response.status_code in (403, 404)


def test_a_waiter_cannot_read_the_takings(client, db_session, resto):
    """La recette est un chiffre de direction, pas un chiffre de salle."""
    restaurant, table, item = resto
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    _order(db_session, restaurant, table, item, 20.0, OrderStatus.SERVED)

    response = client.get(f"/api/v1/stats/dashboard/{restaurant.id}", headers=auth_headers(waiter))

    assert response.status_code == 403
