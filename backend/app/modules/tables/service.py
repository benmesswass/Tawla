from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_event
from app.modules.notifications.manager import manager, table_channel
from app.modules.orders import table_cart
from app.modules.orders.models import Order
from app.modules.staff.models import Staff
from app.modules.tables import party as table_party
from app.modules.tables.models import Table
from app.modules.tenants.models import Restaurant
from app.modules.waiter_calls.models import WaiterCall

logger = get_logger("tables")


def get_table_by_qr_token(db: Session, qr_token: str) -> Table:
    """
    Point d'entrée unique de tout le parcours client : c'est le scan du QR qui
    rattache un appel anonyme à une table, donc à un restaurant. Quatre routes
    le faisaient chacune de leur côté (menu, commande, appel serveur, fiche
    restaurant), et la fidélité en fait une cinquième.

    Le 404 est identique partout, et volontairement : un token inconnu ne doit
    jamais se distinguer d'un token valide sur une autre table, ni d'une table
    dont le restaurant n'a pas (ou plus) payé son activation (2026-08-20) —
    sinon la réponse elle-même dirait aux clients qu'un établissement existe
    mais n'a pas payé.
    """
    table = db.query(Table).filter(Table.qr_token == qr_token).first()
    if not table:
        raise HTTPException(
            status_code=404,
            detail={"code": "INVALID_TABLE_CODE", "message": "invalid table code"},
        )
    restaurant = db.get(Restaurant, table.restaurant_id)
    if not restaurant or not restaurant.is_usable:
        raise HTTPException(
            status_code=404,
            detail={"code": "INVALID_TABLE_CODE", "message": "invalid table code"},
        )

    # Scan = occupation (2026-09-09) : posé une seule fois, jamais réécrit
    # tant que la table n'a pas été explicitement libérée (`release_table`).
    # Un deuxième scan (rafraîchissement, deuxième convive) ne fait rien de
    # plus qu'une lecture.
    if table.occupied_at is None:
        table.occupied_at = datetime.now(timezone.utc)
        db.commit()

    return table


async def release_table(db: Session, table: Table, staff: Staff) -> Table:
    """
    Le serveur ou le manager confirment que les clients sont partis — seul
    geste qui remet la table à zéro (2026-09-09). Plus aucun timer ni aucune
    déconnexion ne le fait à sa place : les clients doivent pouvoir prendre
    leur temps pour commander sans risquer de perdre leur panier en route.
    """
    table.occupied_at = None
    db.commit()
    db.refresh(table)

    table_cart.table_cart_store.pop_all(table.id)
    table_party.table_party_store.clear(table.id)

    log_event(
        logger, "table.released",
        restaurant_id=table.restaurant_id, table_id=table.id, staff_id=staff.id,
    )

    await manager.broadcast(
        table.restaurant_id, channel="staff",
        message={"event": "table.released", "table_id": table.id},
    )
    # Un appareil client resté connecté (onglet ouvert) doit voir son panier
    # et ses convives repartir à zéro tout de suite — mêmes événements que
    # ceux diffusés à chaque changement (voir notifications/router.py).
    client_channel = table_channel(table.id)
    await manager.broadcast(table.restaurant_id, client_channel, table_cart.snapshot_message(table.id))
    await manager.broadcast(table.restaurant_id, client_channel, table_party.party_message(table.id))

    return table


def delete_table(db: Session, table: Table) -> None:
    """
    Une table qui a déjà des commandes ou des appels serveur garde son
    historique (stats, factures) : la supprimer casserait la FK, ou pire la
    perdrait en silence (SQLite ne vérifie pas les FK dans les tests). Le
    manager renomme la table plutôt que d'effacer un passage réel.
    """
    if db.query(Order.id).filter(Order.table_id == table.id).first() is not None:
        raise HTTPException(
            status_code=409,
            detail={"code": "TABLE_HAS_ORDERS", "message": "table has existing orders"},
        )
    if db.query(WaiterCall.id).filter(WaiterCall.table_id == table.id).first() is not None:
        raise HTTPException(
            status_code=409,
            detail={"code": "TABLE_HAS_WAITER_CALLS", "message": "table has existing waiter calls"},
        )
    db.delete(table)
    db.commit()
