"""
Rétention des données personnelles (Phase 16).

Le produit collecte deux choses qui identifient une personne : un numéro de
téléphone (fidélité) et un abonnement Web Push (point de contact vers un
navigateur). La loi organique 2004-63 n'autorise à les conserver que tant
qu'ils ont une finalité. Ces tests vérifient qu'ils disparaissent réellement
quand cette finalité s'éteint — un drapeau « supprimé » posé sur une ligne qui
contient toujours le numéro ne serait pas une purge.
"""
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from tests.conftest import auth_headers, create_restaurant, create_staff, order_headers

from app.core.database import Base
from app.modules.loyalty import service as loyalty_service
from app.modules.loyalty.models import LoyaltyMember
from app.modules.menu.models import MenuItem
from app.modules.orders import service as orders_service
from app.modules.orders.models import Order, OrderStatus
from app.modules.staff.models import StaffRole
from app.modules.tables.models import Table

SUBSCRIPTION = {
    "endpoint": "https://push.example.test/abonnement-1",
    "keys": {"p256dh": "cle-publique", "auth": "secret"},
}


@pytest.fixture()
def resto(db_session):
    restaurant = create_restaurant(name="Chez Slah", slug=None)
    table = Table(restaurant_id=restaurant.id, label="Table 1")
    item = MenuItem(restaurant_id=restaurant.id, name="Couscous", price=18.0, category="Plats")
    db_session.add_all([table, item])
    db_session.commit()
    db_session.refresh(table)
    db_session.refresh(item)
    return restaurant, table, item


def _place_order(client, table, item, loyalty_phone: str | None = None) -> dict:
    payload = {
        "qr_token": table.qr_token,
        "items": [{"menu_item_id": item.id, "quantity": 1}],
    }
    if loyalty_phone:
        payload["loyalty_phone"] = loyalty_phone
    response = client.post("/api/v1/orders", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _to_served(client, order_id: int, waiter, kitchen) -> None:
    for path, staff in (
        ("confirm", waiter),
        ("send-to-kitchen", waiter),
        ("start-preparation", kitchen),
        ("mark-ready", kitchen),
        ("mark-served", waiter),
    ):
        response = client.post(f"/api/v1/orders/{order_id}/{path}", headers=auth_headers(staff))
        assert response.status_code == 200, f"{path} : {response.text}"


# --- Abonnement push : effacé dès que la commande est terminée ---------------


def test_push_subscription_is_erased_once_the_order_is_served(client, db_session, resto):
    restaurant, table, item = resto
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    kitchen = create_staff(restaurant.id, StaffRole.KITCHEN)
    order = _place_order(client, table, item)

    saved = client.post(
        f"/api/v1/orders/{order['id']}/push-subscription",
        json=SUBSCRIPTION,
        headers=order_headers(order),
    )
    assert saved.status_code in (200, 204), saved.text
    db_session.expire_all()
    assert db_session.get(Order, order["id"]).push_subscription is not None

    _to_served(client, order["id"], waiter, kitchen)

    db_session.expire_all()
    assert db_session.get(Order, order["id"]).push_subscription is None


def test_push_subscription_is_erased_when_the_order_is_cancelled(client, db_session, resto):
    restaurant, table, item = resto
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    order = _place_order(client, table, item)
    client.post(
        f"/api/v1/orders/{order['id']}/push-subscription",
        json=SUBSCRIPTION,
        headers=order_headers(order),
    )

    cancelled = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=auth_headers(waiter))
    assert cancelled.status_code == 200, cancelled.text

    db_session.expire_all()
    assert db_session.get(Order, order["id"]).push_subscription is None


def test_push_subscription_survives_until_the_order_is_ready(client, db_session, resto):
    """La finalité de l'abonnement est justement de prévenir que c'est prêt :
    le purger trop tôt casserait la notification qu'il sert à envoyer."""
    restaurant, table, item = resto
    waiter = create_staff(restaurant.id, StaffRole.WAITER)
    kitchen = create_staff(restaurant.id, StaffRole.KITCHEN)
    order = _place_order(client, table, item)
    client.post(
        f"/api/v1/orders/{order['id']}/push-subscription",
        json=SUBSCRIPTION,
        headers=order_headers(order),
    )

    for path, staff in (
        ("confirm", waiter),
        ("send-to-kitchen", waiter),
        ("start-preparation", kitchen),
    ):
        client.post(f"/api/v1/orders/{order['id']}/{path}", headers=auth_headers(staff))

    db_session.expire_all()
    assert db_session.get(Order, order["id"]).push_subscription is not None


def test_purge_catches_subscriptions_left_on_already_terminal_orders(db_session, resto):
    """Rattrapage des commandes servies avant l'existence de cette règle."""
    restaurant, table, item = resto
    served = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        status=OrderStatus.SERVED,
        push_subscription='{"endpoint": "https://push.example.test/vieux"}',
    )
    active = Order(
        restaurant_id=restaurant.id,
        table_id=table.id,
        status=OrderStatus.IN_PREPARATION,
        push_subscription='{"endpoint": "https://push.example.test/en-cours"}',
    )
    db_session.add_all([served, active])
    db_session.commit()

    assert orders_service.purge_terminal_push_subscriptions(db_session, dry_run=True) == 1
    db_session.expire_all()
    assert db_session.get(Order, served.id).push_subscription is not None, "le dry-run a supprimé"

    assert orders_service.purge_terminal_push_subscriptions(db_session) == 1
    db_session.expire_all()
    assert db_session.get(Order, served.id).push_subscription is None
    assert db_session.get(Order, active.id).push_subscription is not None, "commande en cours touchée"


# --- Fidélité : la fiche disparaît après 24 mois sans commande ---------------


def _member(db_session, restaurant_id: int, phone: str, created_days_ago: int, last_order_days_ago=None):
    now = datetime.now(timezone.utc)
    member = LoyaltyMember(
        restaurant_id=restaurant_id,
        phone_number=phone,
        created_at=now - timedelta(days=created_days_ago),
        last_order_at=None if last_order_days_ago is None else now - timedelta(days=last_order_days_ago),
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)
    return member


def test_a_paid_order_refreshes_the_retention_clock(client, db_session, resto):
    restaurant, table, item = resto
    order = _place_order(client, table, item, loyalty_phone="20123456")

    paid = client.post(
        f"/api/v1/orders/{order['id']}/pay/card",
        json={"tip_amount": 0},
        headers=order_headers(order),
    )
    assert paid.status_code == 200, paid.text

    member = (
        db_session.query(LoyaltyMember)
        .filter(LoyaltyMember.phone_number == "20123456")
        .one()
    )
    assert member.last_order_at is not None
    assert member.order_count == 1


def test_members_inactive_beyond_24_months_are_deleted(db_session, resto):
    restaurant, _table, _item = resto
    vieux = _member(db_session, restaurant.id, "20000001", created_days_ago=900, last_order_days_ago=800)
    recent = _member(db_session, restaurant.id, "20000002", created_days_ago=900, last_order_days_ago=100)
    limite = _member(db_session, restaurant.id, "20000003", created_days_ago=900, last_order_days_ago=729)

    assert loyalty_service.purge_inactive_members(db_session) == 1
    restants = {m.phone_number for m in db_session.query(LoyaltyMember).all()}
    assert restants == {recent.phone_number, limite.phone_number}
    assert vieux.phone_number not in restants


def test_a_member_who_never_ordered_is_judged_on_its_creation_date(db_session, resto):
    """Sans cette règle, une fiche créée par une simple saisie de numéro jamais
    suivie d'une commande resterait en base pour toujours."""
    restaurant, _table, _item = resto
    _member(db_session, restaurant.id, "20000004", created_days_ago=900)
    _member(db_session, restaurant.id, "20000005", created_days_ago=10)

    assert loyalty_service.purge_inactive_members(db_session) == 1
    assert [m.phone_number for m in db_session.query(LoyaltyMember).all()] == ["20000005"]


def test_the_dry_run_counts_without_deleting_anything(db_session, resto):
    restaurant, _table, _item = resto
    _member(db_session, restaurant.id, "20000006", created_days_ago=900, last_order_days_ago=800)

    assert loyalty_service.purge_inactive_members(db_session, dry_run=True) == 1
    assert db_session.query(LoyaltyMember).count() == 1


def test_the_purge_crosses_restaurants_and_leaves_nothing_behind(db_session, resto):
    """La purge est une obligation légale, pas une action de gestion d'un
    restaurant : elle s'applique à toutes les fiches, quel que soit le tenant.
    Et la ligne est supprimée, pas juste vidée — le numéro ne doit plus être
    lisible en base."""
    restaurant, _table, _item = resto
    autre = create_restaurant(name="Autre resto", slug=None)
    _member(db_session, restaurant.id, "20000007", created_days_ago=900, last_order_days_ago=800)
    _member(db_session, autre.id, "20000008", created_days_ago=900, last_order_days_ago=800)

    assert loyalty_service.purge_inactive_members(db_session) == 2
    assert db_session.query(LoyaltyMember).count() == 0
    from sqlalchemy import text

    restant = db_session.execute(text("SELECT phone_number FROM loyalty_members")).fetchall()
    assert restant == []


def test_the_purge_is_idempotent(db_session, resto):
    restaurant, _table, _item = resto
    _member(db_session, restaurant.id, "20000009", created_days_ago=900, last_order_days_ago=800)

    assert loyalty_service.purge_inactive_members(db_session) == 1
    assert loyalty_service.purge_inactive_members(db_session) == 0


# --- Le script d'exploitation lui-même -------------------------------------


def test_the_purge_script_runs_end_to_end(tmp_path):
    """
    Lancé en vrai sous-processus, sur sa propre base : c'est le seul test qui
    voit ce que voit Wassim quand il tape la commande. La suite pytest importe
    `model_registry` dans son conftest, donc un script qui oublie cet import
    passe tous les autres tests et casse au premier commit — c'est exactement
    ce qui est arrivé à la première version de ce script.
    """
    db_path = tmp_path / "purge.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)

    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO loyalty_members (restaurant_id, phone_number, order_count,"
                 " reward_available, created_at, last_order_at)"
                 " VALUES (1, '20999999', 3, 0, :old, :old)"),
            {"old": now - timedelta(days=900)},
        )

    script = Path(__file__).resolve().parent.parent / "scripts" / "purge_donnees_personnelles.py"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}"}

    simulation = subprocess.run(
        [sys.executable, str(script)], env=env, capture_output=True, text=True, timeout=60
    )
    assert simulation.returncode == 0, simulation.stderr
    assert "1" in simulation.stdout
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM loyalty_members")).scalar() == 1

    applique = subprocess.run(
        [sys.executable, str(script), "--appliquer"], env=env, capture_output=True, text=True, timeout=60
    )
    assert applique.returncode == 0, applique.stderr
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM loyalty_members")).scalar() == 0
